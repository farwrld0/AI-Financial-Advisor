"""
test_system_prompt_v2.py
AI Personal Finance Agent — IST 495 SU26
Author: Ruohan (Kayla) Mei
Week 5 — Task 3.2: Test system_prompt_v2 with DeepSeek API

Tests 3 different user personas to verify:
1. Output follows the required 6-section format
2. Numbers are correctly cited from the profile
3. Age-based / city-based advice differs appropriately
4. Constraints are respected
5. Critical situations (negative savings) are handled correctly

HOW TO USE:
1. pip install openai
2. Set DEEPSEEK_API_KEY below (get from Ken or platform.deepseek.com)
3. Run: python test_system_prompt_v2.py
"""

from questionnaire_schema import (
    UserFinancialProfile, ExpenseItem, ExpenseTag,
    DebtItem, FutureGoal, EmploymentType, RiskTolerance
)
from system_prompt_v2 import build_messages, SYSTEM_PROMPT

# ── CONFIG ────────────────────────────────────────────────
DEEPSEEK_API_KEY = "your_deepseek_api_key_here"  # ask Ken for this


# ── TEST PERSONAS ─────────────────────────────────────────

def persona_student():
    """Persona 1: 20-year-old student, low income, high COL city, debt-heavy."""
    return UserFinancialProfile(
        age=20,
        employment_type=EmploymentType.STUDENT,
        household_size=1,
        city="Boston, MA",  # high cost-of-living
        monthly_income_after_tax=1200.0,   # part-time job
        other_income=0.0,
        monthly_subsidy=600.0,             # financial aid / scholarship
        expenses=[
            ExpenseItem("Rent (shared)",   900.0, ExpenseTag.NEED),
            ExpenseItem("Groceries",       250.0, ExpenseTag.NEED),
            ExpenseItem("Transportation",   80.0, ExpenseTag.NEED),
            ExpenseItem("Phone/Internet",   60.0, ExpenseTag.NEED),
            ExpenseItem("Dining Out",      150.0, ExpenseTag.WANT),
            ExpenseItem("Entertainment",    80.0, ExpenseTag.WANT),
            ExpenseItem("Subscriptions",    30.0, ExpenseTag.WANT),
        ],
        monthly_medical_bills=0.0,
        current_savings=500.0,
        has_emergency_fund=False,
        emergency_fund_months=0.5,
        debts=[
            DebtItem("Student Loan", 18000.0, 0.0, 0.05),  # deferred, no payment yet
        ],
        future_goals=[
            FutureGoal("Build emergency fund", 3000.0, 1.0, 1),
            FutureGoal("Laptop for coursework", 1200.0, 0.5, 2),
        ],
        risk_tolerance=RiskTolerance.AGGRESSIVE,  # young, long horizon
        constraints="Cannot work more hours due to full course load",
        expectations="Want to know if I can afford a new laptop this semester",
    )


def persona_young_professional():
    """Persona 2: 28-year-old professional, moderate COL, overspending on wants."""
    return UserFinancialProfile(
        age=28,
        employment_type=EmploymentType.FULL_TIME,
        household_size=1,
        city="Austin, TX",  # moderate cost-of-living
        monthly_income_after_tax=5200.0,
        other_income=200.0,   # side freelance
        monthly_subsidy=0.0,
        expenses=[
            ExpenseItem("Rent",           1600.0, ExpenseTag.NEED),
            ExpenseItem("Groceries",       450.0, ExpenseTag.NEED),
            ExpenseItem("Car payment",      380.0, ExpenseTag.NEED),
            ExpenseItem("Insurance",        200.0, ExpenseTag.NEED),
            ExpenseItem("Utilities",        150.0, ExpenseTag.NEED),
            ExpenseItem("Dining Out",       900.0, ExpenseTag.WANT),  # high!
            ExpenseItem("Shopping",         700.0, ExpenseTag.WANT),  # high!
            ExpenseItem("Entertainment",    400.0, ExpenseTag.WANT),
            ExpenseItem("Subscriptions",    150.0, ExpenseTag.WANT),
        ],
        monthly_medical_bills=0.0,
        current_savings=4000.0,
        has_emergency_fund=True,
        emergency_fund_months=1.0,
        debts=[
            DebtItem("Credit Card", 3500.0, 150.0, 0.22),  # high interest!
        ],
        future_goals=[
            FutureGoal("Build 6-month emergency fund", 20000.0, 1.5, 1),
            FutureGoal("Down payment for house",       40000.0, 5.0, 2),
        ],
        risk_tolerance=RiskTolerance.MODERATE,
        constraints=None,
        expectations="I feel like I'm not saving enough but don't know where my money goes",
    )


def persona_family():
    """Persona 3: 38-year-old, family of 4, high COL, medical bills, healthy savings."""
    return UserFinancialProfile(
        age=38,
        employment_type=EmploymentType.FULL_TIME,
        household_size=4,
        city="San Francisco, CA",  # very high cost-of-living
        monthly_income_after_tax=9500.0,
        other_income=500.0,   # spouse part-time
        monthly_subsidy=0.0,
        expenses=[
            ExpenseItem("Mortgage",        3200.0, ExpenseTag.NEED),
            ExpenseItem("Groceries",        900.0, ExpenseTag.NEED),
            ExpenseItem("Utilities",        300.0, ExpenseTag.NEED),
            ExpenseItem("Car payments (2)", 700.0, ExpenseTag.NEED),
            ExpenseItem("Insurance",        450.0, ExpenseTag.NEED),
            ExpenseItem("Dining Out",       300.0, ExpenseTag.WANT),
            ExpenseItem("Entertainment",    200.0, ExpenseTag.WANT),
            ExpenseItem("Shopping",         250.0, ExpenseTag.WANT),
        ],
        monthly_medical_bills=400.0,   # ongoing condition
        monthly_childcare=1200.0,
        current_savings=45000.0,
        has_emergency_fund=True,
        emergency_fund_months=4.0,
        debts=[
            DebtItem("Mortgage Principal", 580000.0, 3200.0, 0.0625),
        ],
        future_goals=[
            FutureGoal("Kids' college fund",  100000.0, 12.0, 1),
            FutureGoal("Family vacation",       6000.0, 1.0,  2),
            FutureGoal("Retirement top-up",    50000.0, 10.0, 3),
        ],
        risk_tolerance=RiskTolerance.MODERATE,
        constraints="Mortgage rate is fixed, cannot refinance until 2028",
        expectations="Want to make sure we're saving enough for two kids' college while managing medical costs",
    )


PERSONAS = {
    "Persona 1 — Student (Boston, 20yo, aggressive risk, deferred loan)": persona_student,
    "Persona 2 — Young Professional (Austin, 28yo, overspending on wants, CC debt)": persona_young_professional,
    "Persona 3 — Family (San Francisco, 38yo, medical bills, childcare, college goals)": persona_family,
}


# ── RUN TEST ──────────────────────────────────────────────

def run_persona_test(name: str, profile_fn, client):
    print("\n" + "=" * 70)
    print(f"  {name}")
    print("=" * 70)

    profile = profile_fn()

    # Print key stats for reference
    print(f"\n📋 Profile stats:")
    print(f"   Age: {profile.age} | City: {profile.city} | Risk: {profile.risk_tolerance.value}")
    print(f"   Total income: ${profile.total_monthly_income:,.2f}")
    print(f"   Total expenses: ${profile.total_monthly_expenses:,.2f}")
    print(f"   Net savings: ${profile.net_monthly_savings:,.2f} "
          f"({profile.savings_rate*100:.1f}%)")
    print(f"   Wants ratio: {profile.wants_ratio*100:.1f}%")
    print(f"   Emergency fund: {profile.emergency_fund_months} months")

    messages = build_messages(profile)

    print(f"\n⏳ Calling DeepSeek...")
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.7,
            max_tokens=1500,
        )
        result = response.choices[0].message.content
        print(f"\n📥 RESPONSE:\n")
        print(result)

        # ── Format checks ──────────────────────────────
        print(f"\n🔍 FORMAT CHECK:")
        required_sections = [
            "Profile Summary", "Financial Health Score",
            "Key Findings", "Recommendations",
            "Goal Outlook", "Output Options"
        ]
        for section in required_sections:
            present = "✅" if section in result else "❌"
            print(f"   {present} {section}")

        print(f"\n📊 Tokens: {response.usage.prompt_tokens} prompt + "
              f"{response.usage.completion_tokens} completion")

    except Exception as e:
        print(f"\n❌ API Error: {e}")


if __name__ == "__main__":
    from openai import OpenAI

    print("🚀 AI Personal Finance Agent — System Prompt v2 Test")
    print(f"   Testing {len(PERSONAS)} personas\n")

    client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com"
    )

    for name, profile_fn in PERSONAS.items():
        run_persona_test(name, profile_fn, client)

    print("\n" + "=" * 70)
    print("✅ All persona tests complete.")
    print("\nWhat to check manually:")
    print("  1. Persona 1 (student): Did it respect 'cannot work more hours'?")
    print("     Did it avoid penalizing the deferred student loan?")
    print("  2. Persona 2 (overspender): Did it flag wants_ratio > 40%?")
    print("     Did it flag the 22% interest credit card as urgent?")
    print("  3. Persona 3 (family): Did it treat medical_bills as a NEED?")
    print("     Did it acknowledge SF's high cost of living context?")
    print("     Did it address the college fund goal feasibility?")
    print("  4. All: Did the response end with the exact Output Options text?")
    print("  5. All: Was the word count roughly 300-500 words?")
    print("=" * 70)
