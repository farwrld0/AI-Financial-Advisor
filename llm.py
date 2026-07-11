"""DeepSeek API integration for the AI Personal Finance Agent."""

from __future__ import annotations

import json
import os
import tomllib
from pathlib import Path
from typing import Any

import streamlit as st
from openai import OpenAI


DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"


def get_deepseek_api_key() -> str | None:
    """Return the DeepSeek API key from Streamlit secrets or the environment."""
    try:
        secrets_key = st.secrets.get("DEEPSEEK_API_KEY")
        if secrets_key:
            return str(secrets_key)
    except Exception:
        pass
    env_key = os.getenv("DEEPSEEK_API_KEY")
    if env_key:
        return env_key

    # Compatibility for this local project layout. Streamlit Cloud should use
    # .streamlit/secrets.toml; this fallback still avoids hardcoded keys.
    local_secrets = Path(__file__).with_name("secrets.toml")
    if local_secrets.exists():
        with local_secrets.open("rb") as file:
            return tomllib.load(file).get("DEEPSEEK_API_KEY")
    return None


def _client() -> OpenAI:
    api_key = get_deepseek_api_key()
    if not api_key:
        raise ValueError("Missing DEEPSEEK_API_KEY. Add it to .streamlit/secrets.toml or your environment.")
    return OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)


def _money(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _profile_json(user_profile: dict[str, Any]) -> str:
    return json.dumps(user_profile, indent=2, ensure_ascii=False, sort_keys=True)


def build_system_prompt(user_profile: dict[str, Any]) -> str:
    """Build a detailed financial-advisor system prompt using the full profile."""
    total_income = _money(user_profile.get("total_monthly_income"))
    total_expenses = _money(user_profile.get("total_monthly_expenses"))
    monthly_surplus = _money(user_profile.get("monthly_surplus", total_income - total_expenses))
    savings_rate = (monthly_surplus / total_income * 100) if total_income else 0.0
    fixed_expenses = _money(user_profile.get("total_fixed_expenses"))
    variable_expenses = _money(user_profile.get("total_variable_expenses"))
    wants_spending = (
        _money(user_profile.get("dining_out"))
        + _money(user_profile.get("entertainment"))
        + _money(user_profile.get("shopping"))
        + _money(user_profile.get("travel"))
    )
    needs_spending = total_expenses - wants_spending

    profile_summary = f"""
Client identity and household:
- Full name: {user_profile.get("full_name")}
- Age: {user_profile.get("age")}
- City: {user_profile.get("city")}
- State / province: {user_profile.get("state")}
- Household size: {user_profile.get("household_size")}
- Employment status: {user_profile.get("employment_status")}
- Education level: {user_profile.get("education_level")}

Income:
- Monthly income after tax: ${_money(user_profile.get("monthly_income_after_tax")):,.2f}
- Secondary income: ${_money(user_profile.get("secondary_income")):,.2f}
- Total monthly income: ${total_income:,.2f}

Assets and liquidity:
- Cash savings: ${_money(user_profile.get("cash_savings")):,.2f}
- Checking account: ${_money(user_profile.get("checking_account")):,.2f}
- Investment accounts: ${_money(user_profile.get("investment_accounts")):,.2f}
- Retirement accounts: ${_money(user_profile.get("retirement_accounts")):,.2f}
- Total assets: ${_money(user_profile.get("total_assets")):,.2f}
- Net worth: ${_money(user_profile.get("net_worth")):,.2f}
- Emergency fund months: {user_profile.get("emergency_fund_months")}
- Risk preference: {user_profile.get("risk_preference")}

Fixed monthly expenses:
- Rent / mortgage: ${_money(user_profile.get("rent_mortgage")):,.2f}
- Utilities: ${_money(user_profile.get("utilities")):,.2f}
- Insurance: ${_money(user_profile.get("insurance")):,.2f}
- Transportation fixed: ${_money(user_profile.get("transportation_fixed")):,.2f}
- Loan repayments: ${_money(user_profile.get("loan_repayments")):,.2f}
- Subscriptions: ${_money(user_profile.get("subscriptions")):,.2f}
- Internet / phone: ${_money(user_profile.get("internet_phone")):,.2f}
- Other fixed expenses: ${_money(user_profile.get("other_fixed_expenses")):,.2f}
- Total fixed expenses: ${fixed_expenses:,.2f}

Variable monthly expenses:
- Groceries: ${_money(user_profile.get("groceries")):,.2f}
- Dining out: ${_money(user_profile.get("dining_out")):,.2f}
- Entertainment: ${_money(user_profile.get("entertainment")):,.2f}
- Shopping: ${_money(user_profile.get("shopping")):,.2f}
- Travel: ${_money(user_profile.get("travel")):,.2f}
- Other variable expenses: ${_money(user_profile.get("other_variable_expenses")):,.2f}
- Total variable expenses: ${variable_expenses:,.2f}

Budget totals and ratios:
- Total monthly expenses: ${total_expenses:,.2f}
- Monthly surplus: ${monthly_surplus:,.2f}
- Savings rate: {savings_rate:.1f}%
- Estimated needs spending: ${needs_spending:,.2f}
- Estimated wants spending: ${wants_spending:,.2f}

Debt and future plans:
- Total debt: ${_money(user_profile.get("total_debt")):,.2f}
- Target savings: ${_money(user_profile.get("target_savings")):,.2f}
- Primary goal: {user_profile.get("primary_goal")}
- Goal timeline: {user_profile.get("goal_timeline")}

Full raw user_profile dictionary:
{_profile_json(user_profile)}
""".strip()

    return f"""
You are a professional AI financial advisor. Give practical, specific, and responsible personal finance guidance in English.

Use every available variable in the user_profile, including full_name, age, city, state, household_size, employment_status, education_level, monthly_income_after_tax, secondary_income, cash_savings, checking_account, investment_accounts, retirement_accounts, emergency_fund_months, risk_preference, total_monthly_income, total_assets, net_worth, rent_mortgage, utilities, insurance, transportation_fixed, loan_repayments, subscriptions, internet_phone, other_fixed_expenses, groceries, dining_out, entertainment, shopping, travel, other_variable_expenses, total_fixed_expenses, total_variable_expenses, total_monthly_expenses, monthly_surplus, total_debt, target_savings, primary_goal, and goal_timeline.

Base your recommendations on the user's actual cash flow, assets, net worth, debt, household size, location, emergency fund, risk preference, spending categories, and future goal timeline. Do not invent missing facts. If a value is missing, say it is missing and make only a cautious assumption when needed. Use dollar amounts, percentages, and concrete monthly action steps where possible. Avoid legal, tax, or investment guarantees.

Return a structured report with exactly these sections:
1. Financial Health Score (0-100)
2. Income, Expense, and Savings Rate Review
3. Budget Assessment Against the 50/30/20 Rule
4. Needs vs Wants Analysis
5. Emergency Fund and Liquidity Review
6. Debt and Net Worth Assessment
7. Investment Recommendations Based on Age and Risk Preference
8. Goal Timeline and Feasibility
9. Risk Warnings
10. Top 3 Action Items

User profile:
{profile_summary}
""".strip()


def generate_financial_report(user_profile: dict[str, Any]) -> str:
    """Call DeepSeek and return the full financial analysis."""
    api_key = get_deepseek_api_key()
    if not api_key:
        raise ValueError("Missing DEEPSEEK_API_KEY. Add it to .streamlit/secrets.toml or your environment.")
    client = OpenAI(
        api_key=api_key,
        base_url=DEEPSEEK_BASE_URL,
    )
    response = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": build_system_prompt(user_profile)},
            {"role": "user", "content": "Generate my complete structured financial analysis."},
        ],
        max_tokens=2000,
        temperature=0.25,
    )
    return response.choices[0].message.content or ""


def ask_chatbot(question: str, user_profile: dict[str, Any], chat_history: list[dict[str, str]]) -> str:
    """Answer a user's question using their financial state and chat memory."""
    messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": (
                build_system_prompt(user_profile)
                + "\n\nYou are now acting as a context-aware finance chatbot. "
                "Answer the user's question directly. For purchase decisions, start with Yes, No, or Maybe, "
                "then explain the budget impact using their actual income, expenses, surplus, goals, and risk profile."
            ),
        }
    ]
    for item in chat_history:
        role = item.get("role", "user")
        content = item.get("content", "")
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": question})

    response = _client().chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=messages,
        temperature=0.35,
    )
    return response.choices[0].message.content or ""


def run_scenario(scenario: str, user_profile: dict[str, Any]) -> str:
    """Run a what-if financial scenario through DeepSeek."""
    prompt = f"""
Analyze this what-if scenario for the user's financial plan:

Scenario:
{scenario}

Current profile:
{_profile_json(user_profile)}

Return a structured scenario analysis with:
1. What changes in the monthly budget
2. Before vs after estimate for income, expenses, surplus, and savings rate
3. Effect on each financial goal and timeline
4. Risks created or reduced
5. Recommended adjustments

If exact recalculation is impossible from the scenario text, state the assumptions you used.
""".strip()

    response = _client().chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": build_system_prompt(user_profile)},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content or ""


def generate_financial_plan(user_profile: dict[str, Any], api_key: str | None = None) -> str:
    """Backward-compatible wrapper used by older questionnaire code."""
    if api_key:
        client = OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": build_system_prompt(user_profile)},
                {"role": "user", "content": "Generate my complete structured financial analysis."},
            ],
            temperature=0.25,
        )
        return response.choices[0].message.content or ""
    return generate_financial_report(user_profile)
