"""Adapter from Streamlit questionnaire state to Kayla's backend schema."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from questionnaire_schema import (
    DebtItem,
    EmploymentType,
    ExpenseItem,
    ExpenseTag,
    FutureGoal,
    RiskTolerance,
    UserFinancialProfile,
)

try:
    from questionnaire_schema import PlannedPurchase
except ImportError:
    @dataclass
    class PlannedPurchase:
        item_name: str
        estimated_cost: float
        planned_month: str
        priority: int


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value or default)
    except (TypeError, ValueError):
        return default


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value or default))
    except (TypeError, ValueError):
        return default


def _employment_type(value: Any) -> EmploymentType:
    normalized = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    mapping = {
        "full_time": EmploymentType.FULL_TIME,
        "part_time": EmploymentType.PART_TIME,
        "self_employed": EmploymentType.SELF_EMPLOYED,
        "student": EmploymentType.STUDENT,
        "unemployed": EmploymentType.UNEMPLOYED,
        "retired": EmploymentType.RETIRED,
    }
    return mapping.get(normalized, EmploymentType.FULL_TIME)


def _risk_tolerance(value: Any) -> RiskTolerance:
    normalized = str(value or "").strip().lower()
    if normalized in {"conservative", "low"}:
        return RiskTolerance.CONSERVATIVE
    if normalized in {"aggressive", "growth", "high"}:
        return RiskTolerance.AGGRESSIVE
    return RiskTolerance.MODERATE


def _emergency_months(value: Any) -> float:
    text = str(value or "").strip().lower()
    if not text:
        return 0.0
    if "12+" in text:
        return 12.0
    if "6-12" in text:
        return 6.0
    if "3-6" in text:
        return 3.0
    if "1-3" in text:
        return 1.0
    if "less" in text:
        return 0.5
    return _float(text, 0.0)


def _city_state(session_data: dict[str, Any]) -> str:
    city = str(session_data.get("city") or "").strip()
    state = str(session_data.get("state") or "").strip()
    if city and state:
        return f"{city}, {state}"
    return city or state


def _expense_tag(session_data: dict[str, Any], key: str, default: ExpenseTag) -> ExpenseTag:
    tags = session_data.get("need_want_breakdown") or session_data.get("expense_tags") or {}
    value = tags.get(key) if isinstance(tags, dict) else None
    normalized = str(value or "").strip().lower()
    if normalized in {"need", "needs"}:
        return ExpenseTag.NEED
    if normalized in {"want", "wants"}:
        return ExpenseTag.WANT
    return default


def _add_expense(
    expenses: list[ExpenseItem],
    session_data: dict[str, Any],
    key: str,
    category: str,
    default_tag: ExpenseTag,
) -> None:
    amount = _float(session_data.get(key))
    if amount > 0:
        expenses.append(ExpenseItem(category, amount, _expense_tag(session_data, key, default_tag)))


def _build_expenses(session_data: dict[str, Any]) -> list[ExpenseItem]:
    expenses: list[ExpenseItem] = []
    fixed_needs = [
        ("rent_mortgage", "Rent / Mortgage"),
        ("utilities", "Utilities"),
        ("insurance", "Insurance"),
        ("transportation_fixed", "Transportation"),
    ]
    for key, category in fixed_needs:
        _add_expense(expenses, session_data, key, category, ExpenseTag.NEED)

    _add_expense(expenses, session_data, "groceries", "Groceries", ExpenseTag.NEED)
    _add_expense(expenses, session_data, "food", "Food", ExpenseTag.NEED)
    _add_expense(expenses, session_data, "entertainment", "Entertainment", ExpenseTag.WANT)
    _add_expense(expenses, session_data, "dining_out", "Dining Out", ExpenseTag.WANT)
    _add_expense(expenses, session_data, "shopping", "Shopping", ExpenseTag.WANT)
    _add_expense(expenses, session_data, "travel", "Travel", ExpenseTag.WANT)
    _add_expense(expenses, session_data, "subscriptions", "Subscriptions", ExpenseTag.WANT)
    _add_expense(expenses, session_data, "other_variable_expenses", "Other Variable Spending", ExpenseTag.WANT)
    _add_expense(expenses, session_data, "other_fixed_expenses", "Other Fixed Expenses", ExpenseTag.NEED)
    _add_expense(expenses, session_data, "internet_phone", "Internet / Phone", ExpenseTag.NEED)
    return expenses


def _build_debts(session_data: dict[str, Any]) -> list[DebtItem]:
    debts: list[DebtItem] = []
    loan_payment = _float(session_data.get("loan_repayments"))
    if loan_payment > 0:
        total_amount = _float(session_data.get("total_debt"), loan_payment * 12)
        debts.append(DebtItem("Loan", total_amount, loan_payment, 0.05))
    return debts


def _timeline_years(value: Any) -> float:
    text = str(value or "").strip().lower()
    if "0-1" in text:
        return 1.0
    if "1-3" in text:
        return 3.0
    if "3-5" in text:
        return 5.0
    if "5+" in text:
        return 6.0
    return _float(text, 1.0)


def _build_goals(session_data: dict[str, Any]) -> list[FutureGoal]:
    future_goals = session_data.get("future_goals")
    if isinstance(future_goals, list):
        goals = []
        for index, item in enumerate(future_goals, start=1):
            if not isinstance(item, dict):
                continue
            description = str(item.get("description") or item.get("goal") or "").strip()
            target = _float(item.get("target_amount") or item.get("target"))
            timeline = _float(item.get("timeline_years"), 1.0)
            priority = _int(item.get("priority"), index)
            if description and target > 0:
                goals.append(FutureGoal(description, target, timeline, priority))
        return goals

    primary_goal = str(session_data.get("primary_goal") or "").strip()
    target_savings = _float(session_data.get("target_savings"))
    if primary_goal and target_savings > 0:
        return [
            FutureGoal(
                description=primary_goal,
                target_amount=target_savings,
                timeline_years=_timeline_years(session_data.get("goal_timeline")),
                priority=1,
            )
        ]
    return []


def questionnaire_to_profile(session_data: dict) -> UserFinancialProfile:
    """Convert st.session_state['user_profile'] dict to UserFinancialProfile object."""
    current_savings = _float(session_data.get("cash_savings")) + _float(session_data.get("checking_account"))
    emergency_months = _emergency_months(session_data.get("emergency_fund_months"))
    planned_purchases = []
    raw_purchases = (
        session_data.get("planned_purchases")
        or session_data.get("planned_items")
        or session_data.get("shopping_list")
        or session_data.get("future_purchases")
        or []
    )
    if isinstance(raw_purchases, list):
        for item in raw_purchases:
            if isinstance(item, dict):
                planned_purchases.append(
                    PlannedPurchase(
                        item_name=item.get("name", ""),
                        estimated_cost=_float(item.get("cost", 0)),
                        planned_month=item.get("month", ""),
                        priority=item.get("priority", 1),
                    )
                )

    profile_kwargs = dict(
        age=_int(session_data.get("age"), 0),
        employment_type=_employment_type(session_data.get("employment_status")),
        household_size=max(1, _int(session_data.get("household_size"), 1)),
        city=_city_state(session_data),
        monthly_income_after_tax=_float(session_data.get("monthly_income_after_tax")),
        other_income=_float(session_data.get("secondary_income")),
        monthly_subsidy=_float(session_data.get("monthly_subsidy") or session_data.get("government_subsidies")),
        expenses=_build_expenses(session_data),
        monthly_medical_bills=_float(session_data.get("monthly_medical_bills") or session_data.get("medical_bills")),
        current_savings=current_savings,
        has_emergency_fund=emergency_months > 0 or current_savings > 0,
        emergency_fund_months=emergency_months,
        debts=_build_debts(session_data),
        future_goals=_build_goals(session_data),
        risk_tolerance=_risk_tolerance(session_data.get("risk_preference")),
        constraints=str(session_data.get("constraints") or "").strip() or None,
        expectations=str(session_data.get("expectations") or session_data.get("primary_goal") or "").strip() or None,
    )
    if "planned_purchases" in getattr(UserFinancialProfile, "__dataclass_fields__", {}):
        profile_kwargs["planned_purchases"] = planned_purchases
    return UserFinancialProfile(**profile_kwargs)


def profile_to_session_dict(profile: UserFinancialProfile) -> dict[str, Any]:
    """Convert a UserFinancialProfile back to dashboard-compatible dict data."""
    expenses = {expense.category.lower().replace(" / ", "_").replace(" ", "_"): expense.amount for expense in profile.expenses}
    total_assets = profile.current_savings
    return {
        "age": profile.age,
        "city": profile.city,
        "household_size": profile.household_size,
        "employment_status": profile.employment_type.value,
        "monthly_income_after_tax": profile.monthly_income_after_tax,
        "secondary_income": profile.other_income,
        "cash_savings": profile.current_savings,
        "checking_account": 0.0,
        "investment_accounts": 0.0,
        "retirement_accounts": 0.0,
        "emergency_fund_months": profile.emergency_fund_months,
        "risk_preference": profile.risk_tolerance.value,
        "total_monthly_income": profile.total_monthly_income,
        "total_monthly_expenses": profile.total_monthly_expenses,
        "monthly_surplus": profile.net_monthly_savings,
        "total_assets": total_assets,
        "net_worth": total_assets - profile.total_debt,
        "rent_mortgage": expenses.get("rent_mortgage", expenses.get("rent", 0.0)),
        "utilities": expenses.get("utilities", 0.0),
        "insurance": expenses.get("insurance", 0.0),
        "transportation_fixed": expenses.get("transportation", 0.0),
        "loan_repayments": sum(debt.monthly_payment for debt in profile.debts),
        "groceries": expenses.get("groceries", 0.0),
        "dining_out": expenses.get("dining_out", 0.0),
        "entertainment": expenses.get("entertainment", 0.0),
        "shopping": expenses.get("shopping", 0.0),
        "travel": expenses.get("travel", 0.0),
        "subscriptions": expenses.get("subscriptions", 0.0),
        "total_debt": profile.total_debt,
        "target_savings": sum(goal.target_amount for goal in profile.future_goals),
        "primary_goal": profile.future_goals[0].description if profile.future_goals else "",
        "goal_timeline": f"{profile.future_goals[0].timeline_years:g} years" if profile.future_goals else "",
    }
