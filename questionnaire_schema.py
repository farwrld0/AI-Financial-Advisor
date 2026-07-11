"""
questionnaire_schema.py
AI Personal Finance Agent — IST 495 SU26
Author: Ruohan (Kayla) Mei
Week 2 — Task 2.2: Questionnaire Data Structuring & Validation

Defines the full data schema for the financial questionnaire.
All fields are validated before being passed to the DeepSeek LLM.
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


# ── Enums ─────────────────────────────────────────────────

class EmploymentType(str, Enum):
    FULL_TIME    = "full_time"
    PART_TIME    = "part_time"
    SELF_EMPLOYED = "self_employed"
    STUDENT      = "student"
    UNEMPLOYED   = "unemployed"
    RETIRED      = "retired"

class RiskTolerance(str, Enum):
    CONSERVATIVE = "conservative"
    MODERATE     = "moderate"
    AGGRESSIVE   = "aggressive"

class ExpenseTag(str, Enum):
    NEED = "need"
    WANT = "want"


# ── Expense Item ──────────────────────────────────────────

@dataclass
class ExpenseItem:
    """A single expense entry with needs/wants classification."""
    category: str          # e.g. "Rent", "Food", "Entertainment"
    amount: float          # monthly amount in USD
    tag: ExpenseTag        # need or want
    notes: Optional[str] = None

    def validate(self):
        if self.amount < 0:
            raise ValueError(f"Expense amount cannot be negative: {self.category}")
        if not self.category.strip():
            raise ValueError("Expense category cannot be empty")


# ── Future Goal ───────────────────────────────────────────

@dataclass
class FutureGoal:
    """A planned future financial goal."""
    description: str       # e.g. "Buy a house", "Graduate school tuition"
    target_amount: float   # total amount needed in USD
    timeline_years: float  # how many years from now
    priority: int          # 1 = highest priority

    def monthly_savings_needed(self, current_savings: float = 0) -> float:
        """Calculate how much to save monthly to reach this goal."""
        remaining = max(0, self.target_amount - current_savings)
        months = self.timeline_years * 12
        return remaining / months if months > 0 else remaining


# ── Debt Item ─────────────────────────────────────────────

@dataclass
class DebtItem:
    """An existing debt obligation."""
    debt_type: str         # e.g. "Student Loan", "Credit Card", "Car Loan"
    total_amount: float    # total outstanding balance
    monthly_payment: float # minimum monthly payment
    interest_rate: float   # annual interest rate as decimal (e.g. 0.05 for 5%)


# ── Main User Profile ─────────────────────────────────────

@dataclass
class UserFinancialProfile:
    """
    Complete financial profile collected from the questionnaire.
    This is the standardized data dictionary passed to DeepSeek for analysis.
    """

    # ── Personal Info ──────────────────────────────────
    age: int
    employment_type: EmploymentType
    household_size: int                    # number of people in household
    city: str                              # city/region for cost-of-living context

    # ── Income ────────────────────────────────────────
    monthly_income_after_tax: float
    other_income: float = 0.0              # freelance, rental, side income
    monthly_subsidy: float = 0.0           # government benefits, scholarships, etc.

    # ── Expenses ──────────────────────────────────────
    expenses: list[ExpenseItem] = field(default_factory=list)

    # ── Special Expenses ──────────────────────────────
    monthly_medical_bills: float = 0.0     # ongoing medical/healthcare costs
    monthly_childcare: float = 0.0         # childcare or dependent care

    # ── Savings & Assets ──────────────────────────────
    current_savings: float = 0.0
    has_emergency_fund: bool = False
    emergency_fund_months: float = 0.0    # how many months of expenses covered

    # ── Debts ─────────────────────────────────────────
    debts: list[DebtItem] = field(default_factory=list)

    # ── Future Plans ──────────────────────────────────
    future_goals: list[FutureGoal] = field(default_factory=list)

    # ── Preferences ───────────────────────────────────
    risk_tolerance: RiskTolerance = RiskTolerance.MODERATE
    constraints: Optional[str] = None     # any special constraints, free text
    expectations: Optional[str] = None   # what the user hopes to achieve, free text

    # ── Computed Properties ───────────────────────────

    @property
    def total_monthly_income(self) -> float:
        return self.monthly_income_after_tax + self.other_income + self.monthly_subsidy

    @property
    def total_monthly_expenses(self) -> float:
        return (
            sum(e.amount for e in self.expenses)
            + self.monthly_medical_bills
            + self.monthly_childcare
            + sum(d.monthly_payment for d in self.debts)
        )

    @property
    def net_monthly_savings(self) -> float:
        return self.total_monthly_income - self.total_monthly_expenses

    @property
    def savings_rate(self) -> float:
        if self.total_monthly_income == 0:
            return 0.0
        return self.net_monthly_savings / self.total_monthly_income

    @property
    def needs_total(self) -> float:
        return sum(e.amount for e in self.expenses if e.tag == ExpenseTag.NEED)

    @property
    def wants_total(self) -> float:
        return sum(e.amount for e in self.expenses if e.tag == ExpenseTag.WANT)

    @property
    def wants_ratio(self) -> float:
        if self.total_monthly_income == 0:
            return 0.0
        return self.wants_total / self.total_monthly_income

    @property
    def total_debt(self) -> float:
        return sum(d.total_amount for d in self.debts)

    def to_summary_dict(self) -> dict:
        """Convert profile to a clean summary dict for LLM input."""
        return {
            "personal": {
                "age": self.age,
                "employment": self.employment_type.value,
                "household_size": self.household_size,
                "city": self.city,
            },
            "income": {
                "monthly_take_home": self.monthly_income_after_tax,
                "other_income": self.other_income,
                "subsidies": self.monthly_subsidy,
                "total_monthly_income": round(self.total_monthly_income, 2),
            },
            "expenses": {
                "breakdown": [
                    {"category": e.category, "amount": e.amount, "tag": e.tag.value}
                    for e in self.expenses
                ],
                "medical_bills": self.monthly_medical_bills,
                "childcare": self.monthly_childcare,
                "total_expenses": round(self.total_monthly_expenses, 2),
                "needs_total": round(self.needs_total, 2),
                "wants_total": round(self.wants_total, 2),
                "wants_ratio_pct": round(self.wants_ratio * 100, 1),
            },
            "savings": {
                "net_monthly_savings": round(self.net_monthly_savings, 2),
                "savings_rate_pct": round(self.savings_rate * 100, 1),
                "current_savings": self.current_savings,
                "has_emergency_fund": self.has_emergency_fund,
                "emergency_fund_months": self.emergency_fund_months,
            },
            "debts": [
                {
                    "type": d.debt_type,
                    "total": d.total_amount,
                    "monthly_payment": d.monthly_payment,
                    "interest_rate_pct": round(d.interest_rate * 100, 1),
                }
                for d in self.debts
            ],
            "future_goals": [
                {
                    "goal": g.description,
                    "target": g.target_amount,
                    "timeline_years": g.timeline_years,
                    "monthly_needed": round(g.monthly_savings_needed(self.current_savings / max(len(self.future_goals), 1)), 2),
                }
                for g in self.future_goals
            ],
            "preferences": {
                "risk_tolerance": self.risk_tolerance.value,
                "constraints": self.constraints,
                "expectations": self.expectations,
            },
        }


# ── Validation ────────────────────────────────────────────

def validate_profile(profile: UserFinancialProfile) -> list[str]:
    """
    Validate a UserFinancialProfile and return a list of error messages.
    Empty list = valid.
    """
    errors = []

    if not (18 <= profile.age <= 100):
        errors.append(f"Age must be between 18 and 100. Got: {profile.age}")

    if profile.monthly_income_after_tax < 0:
        errors.append("Monthly income cannot be negative.")

    if profile.household_size < 1:
        errors.append("Household size must be at least 1.")

    if not profile.city.strip():
        errors.append("City cannot be empty.")

    for expense in profile.expenses:
        try:
            expense.validate()
        except ValueError as e:
            errors.append(str(e))

    if profile.current_savings < 0:
        errors.append("Current savings cannot be negative.")

    for debt in profile.debts:
        if debt.monthly_payment < 0:
            errors.append(f"Debt monthly payment cannot be negative: {debt.debt_type}")
        if not (0 <= debt.interest_rate <= 1):
            errors.append(f"Interest rate must be between 0 and 1: {debt.debt_type}")

    for goal in profile.future_goals:
        if goal.target_amount <= 0:
            errors.append(f"Goal target amount must be positive: {goal.description}")
        if goal.timeline_years <= 0:
            errors.append(f"Goal timeline must be positive: {goal.description}")

    return errors


# ── Sample Profile (for testing) ─────────────────────────

def create_sample_profile() -> UserFinancialProfile:
    """Create a sample user profile for testing."""
    return UserFinancialProfile(
        age=26,
        employment_type=EmploymentType.FULL_TIME,
        household_size=1,
        city="State College, PA",
        monthly_income_after_tax=4500.0,
        other_income=300.0,
        monthly_subsidy=0.0,
        expenses=[
            ExpenseItem("Rent",          1200.0, ExpenseTag.NEED),
            ExpenseItem("Groceries",      400.0, ExpenseTag.NEED),
            ExpenseItem("Transportation", 250.0, ExpenseTag.NEED),
            ExpenseItem("Utilities",      120.0, ExpenseTag.NEED),
            ExpenseItem("Healthcare",      80.0, ExpenseTag.NEED),
            ExpenseItem("Entertainment",  300.0, ExpenseTag.WANT),
            ExpenseItem("Dining Out",     250.0, ExpenseTag.WANT),
            ExpenseItem("Shopping",       200.0, ExpenseTag.WANT),
            ExpenseItem("Subscriptions",   50.0, ExpenseTag.WANT),
        ],
        monthly_medical_bills=0.0,
        current_savings=8000.0,
        has_emergency_fund=True,
        emergency_fund_months=2.5,
        debts=[
            DebtItem("Student Loan", 25000.0, 280.0, 0.045),
        ],
        future_goals=[
            FutureGoal("Build 6-month emergency fund", 15000.0, 1.5, 1),
            FutureGoal("Europe trip",                   5000.0, 1.0, 2),
            FutureGoal("Down payment for a car",       10000.0, 3.0, 3),
        ],
        risk_tolerance=RiskTolerance.MODERATE,
        constraints="Cannot reduce rent — lease locked in until December 2026",
        expectations="Want to save more aggressively and understand if I can afford a car in 3 years",
    )


if __name__ == "__main__":
    profile = create_sample_profile()
    errors = validate_profile(profile)

    if errors:
        print("❌ Validation errors:")
        for e in errors:
            print(f"   - {e}")
    else:
        print("✅ Profile valid!")
        import json
        print(json.dumps(profile.to_summary_dict(), indent=2))
