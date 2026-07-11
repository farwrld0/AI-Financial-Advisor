"""Cost-of-living helpers for the AI Personal Finance Agent."""

from __future__ import annotations

from typing import Any


COST_OF_LIVING_INDEX = {
    "New York": 100,
    "San Francisco": 106,
    "Los Angeles": 84,
    "Chicago": 72,
    "London": 88,
    "Tokyo": 76,
    "Shanghai": 58,
    "Singapore": 92,
    "Sydney": 82,
    "Toronto": 74,
}

BASELINE_BENCHMARKS = {
    "rent": 2200,
    "food": 650,
    "transport": 180,
}


def normalize_city(city: str) -> str:
    """Return a supported city name, defaulting unknown values to New York."""
    if city in COST_OF_LIVING_INDEX:
        return city
    return "New York"


def calculate_cost_of_living(
    city: str,
    monthly_income: float,
    expenses: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Return local budget benchmarks and savings guidance.

    Args:
        city: User-selected city or region.
        monthly_income: Monthly income after tax plus secondary income and benefits.
        expenses: Optional expense dictionary used to compare against local averages.

    Returns:
        Dictionary with cost-of-living index, local benchmark values, adjusted
        savings target, and benchmark comparison details.
    """
    selected_city = normalize_city(city)
    col_index = COST_OF_LIVING_INDEX[selected_city]
    multiplier = col_index / 100
    expenses = expenses or {}

    local_avg_rent = round(BASELINE_BENCHMARKS["rent"] * multiplier, 2)
    local_avg_food = round(BASELINE_BENCHMARKS["food"] * multiplier, 2)
    local_avg_transport = round(BASELINE_BENCHMARKS["transport"] * multiplier, 2)

    baseline_savings_rate = 0.20
    if col_index >= 95:
        savings_rate = 0.15
    elif col_index <= 65:
        savings_rate = 0.25
    else:
        savings_rate = baseline_savings_rate

    adjusted_savings_target = round(max(monthly_income, 0) * savings_rate, 2)

    rent = float(expenses.get("rent_mortgage", expenses.get("rent", 0)) or 0)
    food = float(expenses.get("food", 0) or 0)
    transport = float(expenses.get("transportation", expenses.get("transport", 0)) or 0)

    comparisons = {
        "rent": compare_to_benchmark(rent, local_avg_rent),
        "food": compare_to_benchmark(food, local_avg_food),
        "transport": compare_to_benchmark(transport, local_avg_transport),
    }

    return {
        "city": selected_city,
        "col_index": col_index,
        "local_avg_rent": local_avg_rent,
        "local_avg_food": local_avg_food,
        "local_avg_transport": local_avg_transport,
        "adjusted_savings_target": adjusted_savings_target,
        "benchmark_comparison": comparisons,
    }


def compare_to_benchmark(actual: float, benchmark: float) -> dict[str, Any]:
    """Compare one user expense against a local average benchmark."""
    difference = round(actual - benchmark, 2)
    if actual == 0:
        status = "not provided"
    elif actual > benchmark * 1.1:
        status = "above local average"
    elif actual < benchmark * 0.9:
        status = "below local average"
    else:
        status = "near local average"

    return {
        "actual": round(actual, 2),
        "benchmark": round(benchmark, 2),
        "difference": difference,
        "status": status,
    }
