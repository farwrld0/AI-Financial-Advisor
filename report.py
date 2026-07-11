"""Dashboard-style financial report page."""

from __future__ import annotations

import re
from datetime import date
from html import escape
from typing import Any

import streamlit as st

from llm import generate_financial_report


def _compact_html(html: str) -> str:
    """Prevent Markdown from treating indented HTML as code blocks."""
    return "".join(line.strip() for line in html.splitlines())


def _money_value(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _money(value: Any) -> str:
    return f"${_money_value(value):,.0f}"


def _percent(value: float) -> str:
    return f"{value:.0f}%"


def _initials(profile: dict[str, Any]) -> str:
    name = str(profile.get("full_name") or "").strip()
    if not name:
        return "KM"
    parts = [part for part in name.split() if part]
    return "".join(part[0].upper() for part in parts[:2]) or "KM"


def _emergency_months(profile: dict[str, Any], expenses: float) -> float:
    liquid = _money_value(profile.get("cash_savings")) + _money_value(profile.get("checking_account"))
    if expenses > 0:
        return liquid / expenses

    label = str(profile.get("emergency_fund_months") or "")
    if "12+" in label:
        return 12.0
    if "6-12" in label:
        return 6.0
    if "3-6" in label:
        return 3.0
    if "1-3" in label:
        return 1.0
    return 0.0


def _health_score(profile: dict[str, Any]) -> int:
    income = _money_value(profile.get("total_monthly_income"))
    expenses = _money_value(profile.get("total_monthly_expenses"))
    debt = _money_value(profile.get("total_debt"))
    assets = _money_value(profile.get("total_assets"))
    emergency_months = _emergency_months(profile, expenses)

    if income <= 0 and assets <= 0:
        return 20

    surplus = income - expenses
    savings_rate = (surplus / income * 100) if income else 0
    debt_ratio = (debt / max(income * 12, 1)) if income else 0

    score = 45
    score += min(max(savings_rate, 0), 35) * 0.75
    score += min(emergency_months, 6) * 3.5
    score += 10 if assets > debt else 0
    score -= min(debt_ratio * 25, 18)
    score -= 10 if surplus < 0 else 0
    return max(0, min(100, round(score)))


def _score_from_report(report: str, fallback: int) -> int:
    patterns = [
        r"financial\s+health\s+score[^0-9]{0,30}(\d{1,3})\s*/\s*100",
        r"score[^0-9]{0,20}(\d{1,3})\s*/\s*100",
        r"(\d{1,3})\s*/\s*100",
    ]
    for pattern in patterns:
        match = re.search(pattern, report or "", flags=re.IGNORECASE)
        if match:
            return max(0, min(100, int(match.group(1))))
    return fallback


def _score_label(score: int) -> str:
    if score >= 80:
        return "Excellent"
    if score >= 60:
        return "Good"
    if score >= 40:
        return "Needs Improvement"
    return "Needs Attention"


def _score_color(score: int) -> str:
    if score >= 70:
        return "#22c55e"
    if score >= 40:
        return "#f59e0b"
    return "#ef4444"


def _percentile(score: int) -> str:
    if score >= 80:
        return "Top 20%"
    if score >= 60:
        return "Top 40%"
    return "Needs Review"


def _score_description(score: int) -> str:
    if score >= 80:
        return "Great job! You are on track to achieve your financial goals."
    if score >= 60:
        return "You have a solid foundation with a few areas to strengthen."
    if score >= 40:
        return "Your plan has useful building blocks, but several priorities need attention."
    return "Focus first on income, essential expenses, and building a basic cushion."


def _data_quality(profile: dict[str, Any]) -> str:
    important_fields = [
        "age",
        "city",
        "employment_status",
        "monthly_income_after_tax",
        "cash_savings",
        "rent_mortgage",
        "groceries",
        "risk_preference",
    ]
    filled = sum(1 for field in important_fields if profile.get(field) not in ("", None, 0))
    if filled >= 6:
        return "Excellent"
    if filled >= 4:
        return "Good"
    return "Limited"


def _profile_metrics(profile: dict[str, Any]) -> dict[str, float]:
    income = _money_value(profile.get("total_monthly_income"))
    expenses = _money_value(profile.get("total_monthly_expenses"))
    surplus = income - expenses
    savings_rate = (surplus / income * 100) if income else 0.0
    return {
        "income": income,
        "expenses": expenses,
        "surplus": surplus,
        "savings_rate": savings_rate,
        "net_worth": _money_value(profile.get("net_worth")),
        "debt": _money_value(profile.get("total_debt")),
        "assets": _money_value(profile.get("total_assets")),
        "emergency_months": _emergency_months(profile, expenses),
    }


def _budget_parts(profile: dict[str, Any], metrics: dict[str, float]) -> dict[str, float]:
    needs = (
        _money_value(profile.get("rent_mortgage"))
        + _money_value(profile.get("utilities"))
        + _money_value(profile.get("insurance"))
        + _money_value(profile.get("transportation_fixed"))
        + _money_value(profile.get("loan_repayments"))
        + _money_value(profile.get("internet_phone"))
        + _money_value(profile.get("groceries"))
    )
    wants = (
        _money_value(profile.get("subscriptions"))
        + _money_value(profile.get("dining_out"))
        + _money_value(profile.get("entertainment"))
        + _money_value(profile.get("shopping"))
        + _money_value(profile.get("travel"))
        + _money_value(profile.get("other_variable_expenses"))
        + _money_value(profile.get("other_fixed_expenses"))
    )
    savings = max(metrics["surplus"], 0)
    total = max(needs + wants + savings, 1)
    return {"needs": needs, "wants": wants, "savings": savings, "total": total}


def _insights(profile: dict[str, Any], metrics: dict[str, float]) -> list[tuple[str, str, str]]:
    items: list[tuple[str, str, str]] = []
    if metrics["savings_rate"] > 20:
        items.append(("ok", "Strong savings rate", f"You are saving {_percent(metrics['savings_rate'])} of your income."))
    else:
        items.append(("warn", "Savings rate can improve", "Try moving above a 20% monthly savings target."))

    if metrics["emergency_months"] >= 3:
        items.append(("ok", "Emergency fund is healthy", f"You have about {metrics['emergency_months']:.1f} months of expenses saved."))
    else:
        items.append(("warn", "Emergency fund needs attention", "Build toward 3-6 months of essential expenses."))

    housing_ratio = (_money_value(profile.get("rent_mortgage")) / metrics["income"] * 100) if metrics["income"] else 0
    if housing_ratio and housing_ratio < 30:
        items.append(("ok", "Housing costs are below average", f"Housing is about {housing_ratio:.0f}% of monthly income."))
    else:
        items.append(("warn", "Housing cost is elevated", f"Housing is about {housing_ratio:.0f}% of monthly income."))

    investments = _money_value(profile.get("investment_accounts")) + _money_value(profile.get("retirement_accounts"))
    if metrics["assets"] and investments / metrics["assets"] >= 0.35:
        items.append(("ok", "Investments are meaningful", "A solid share of assets is working for long-term growth."))
    else:
        items.append(("warn", "Investment diversification could improve", "Consider increasing diversified long-term investments over time."))
    return items[:4]


def _recommendations(profile: dict[str, Any], metrics: dict[str, float]) -> list[tuple[str, str, str, str, str, str]]:
    target_savings = _money_value(profile.get("target_savings"))
    if metrics["emergency_months"] < 6:
        monthly_gap = max(metrics["expenses"] * 6 - (_money_value(profile.get("cash_savings")) + _money_value(profile.get("checking_account"))), 0)
        months = max(round(monthly_gap / max(metrics["surplus"], 1)), 1) if monthly_gap else 0
        emergency_detail = f"At your current surplus, a 6-month fund is about {months} months away." if metrics["surplus"] > 0 else "Start with a small automatic transfer each month."
    else:
        emergency_detail = "Keep this fund separate from long-term investments."

    return [
        (
            "ti-trending-up",
            "Increase investment allocation",
            "Use your risk preference to guide a diversified long-term mix.",
            "Potential Impact",
            "+ long-term growth",
            "positive",
        ),
        (
            "ti-shield",
            "Build emergency fund to 6 months",
            emergency_detail,
            "Priority",
            "High" if metrics["emergency_months"] < 6 else "Maintain",
            "positive",
        ),
        (
            "ti-scissors",
            "Reduce flexible spending",
            f"Review dining, shopping, travel, and subscriptions for quick savings toward {_money(target_savings)}.",
            "Potential Savings",
            f"{_money(max(_money_value(profile.get('subscriptions')), metrics['income'] * 0.03))} / month",
            "warning",
        ),
    ]


def _budget_tip(needs_pct: float, wants_pct: float) -> str:
    if needs_pct <= 50 and wants_pct <= 30:
        return "You're following the 50/30/20 guideline closely! ✓"
    if needs_pct > 60:
        return "⚠️ Your needs are taking up too much of your income."
    if wants_pct > 30:
        return "⚠️ Consider reducing discretionary spending."
    return "Your budget is close to target; keep tuning needs, wants, and savings."


def _timeline(profile: dict[str, Any], metrics: dict[str, float]) -> list[tuple[str, str, str]]:
    current_year = date.today().year
    goal = str(profile.get("primary_goal") or "Primary financial goal")
    timeline = str(profile.get("goal_timeline") or "1-3 years")
    return [
        ("Today", "You are here", ""),
        ("Emergency Fund Complete", "6 months of expenses saved", str(current_year + (0 if metrics["emergency_months"] >= 6 else 1))),
        (goal, timeline, str(current_year + 2)),
        ("Net Worth Milestone", "Assets growing faster than liabilities", str(current_year + 4)),
        ("Financial Independence", "Long-term direction depends on savings rate", str(current_year + 15)),
    ]


def _render_report_html(profile: dict[str, Any], report: str) -> None:
    metrics = _profile_metrics(profile)
    parts = _budget_parts(profile, metrics)
    score = _score_from_report(report, _health_score(profile))
    label = _score_label(score)
    score_color = _score_color(score)
    needs_pct = parts["needs"] / parts["total"] * 100
    wants_pct = parts["wants"] / parts["total"] * 100
    savings_pct = parts["savings"] / parts["total"] * 100
    budget_tip = _budget_tip(needs_pct, wants_pct)
    today = date.today().strftime("%b %d, %Y")
    data_quality = _data_quality(profile)
    insight_rows = "".join(
        f"""
        <div class="rf-insight">
            <div class="rf-status {'ok' if status == 'ok' else 'warn'}"><i class="ti {'ti-circle-check' if status == 'ok' else 'ti-alert-circle'}"></i></div>
            <div><div class="rf-insight-title">{escape(title)}</div><div class="rf-muted">{escape(body)}</div></div>
        </div>
        """
        for status, title, body in _insights(profile, metrics)
    )
    recommendation_cards = "".join(
        f"""
        <div class="rf-rec-card">
            <div class="rf-rec-icon"><i class="ti {escape(icon)}"></i></div>
            <div class="rf-rec-title">{escape(title)}</div>
            <div class="rf-muted">{escape(body)}</div>
            <div class="rf-impact rf-impact-{escape(tag_style)}"><span>{escape(label_text)}</span><strong>{escape(value)}</strong></div>
        </div>
        """
        for icon, title, body, label_text, value, tag_style in _recommendations(profile, metrics)
    )
    timeline_items = "".join(
        f"""
        <div class="rf-timeline-row rf-timeline-{index}">
            <div class="rf-dot">{'<i class="ti ti-map-pin"></i>' if index == 0 else ''}</div>
            <div><div class="rf-insight-title">{escape(title)}</div><div class="rf-muted">{escape(body)}</div></div>
            <div class="rf-year">{escape(year)}</div>
        </div>
        """
        for index, (title, body, year) in enumerate(_timeline(profile, metrics))
    )

    html = f"""
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@latest/tabler-icons.min.css">
    <style>
    #MainMenu, header[data-testid="stHeader"], footer, section[data-testid="stSidebar"] {{ display: none !important; }}
    .block-container {{ max-width: 100% !important; padding: 0 !important; }}
    .stApp {{ background: #f5f5f7; color: #101426; }}
    .rf-page {{ min-height: 100vh; background: #f5f5f7; font-family: Inter, Sora, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    .rf-nav {{ height: 76px; display: flex; align-items: center; justify-content: space-between; padding: 0 38px; border-bottom: 1px solid #e8edf5; background: rgba(255,255,255,.94); backdrop-filter: blur(18px); }}
    .rf-brand {{ display: flex; align-items: center; gap: 15px; color: #0d1220; font-size: 21px; font-weight: 850; }}
    .rf-logo {{ width: 39px; height: 39px; display: grid; place-items: center; border-radius: 10px; color: white; background: linear-gradient(135deg, #2658ff, #7d36f6); box-shadow: 0 14px 26px rgba(91,75,245,.2); }}
    .rf-links {{ display: flex; align-items: center; gap: 18px; }}
    .rf-link {{ padding: 11px 16px; border-radius: 12px; color: #162033; font-size: 14px; font-weight: 700; text-decoration: none; }}
    .rf-link.active {{ color: #4f46e5; background: rgba(99,102,241,.12); }}
    .rf-avatar {{ width: 42px; height: 42px; display: grid; place-items: center; border-radius: 999px; color: #5d34ee; font-weight: 850; background: linear-gradient(135deg, #eee9ff, #e3d4ff); }}
    .rf-wrap {{ max-width: 1190px; margin: 0 auto; padding: 32px 28px 46px; }}
    .rf-card {{ margin-bottom: 16px; border: 1px solid #e3e8f3; border-radius: 14px; background: rgba(255,255,255,.94); box-shadow: 0 18px 48px rgba(20,31,56,.06); }}
    .rf-hero {{ display: grid; grid-template-columns: 1.05fr .9fr .78fr; gap: 28px; align-items: center; padding: 20px; background: radial-gradient(circle at 32% 42%, rgba(126,55,246,.12), transparent 18rem), radial-gradient(circle at 55% 76%, rgba(25,180,76,.12), transparent 16rem), rgba(255,255,255,.92); }}
    .rf-kicker {{ color: #101426; font-size: 15px; font-weight: 850; margin-bottom: 16px; }}
    .rf-score-line {{ color: {score_color}; font-size: 58px; line-height: 1; font-weight: 900; }}
    .rf-score-line span {{ color: #3a4358; font-size: 30px; font-weight: 650; }}
    .rf-label {{ color: {score_color}; font-size: 25px; font-weight: 850; margin-top: 14px; }}
    .rf-muted {{ color: #53617a; font-size: 13px; line-height: 1.45; }}
    .rf-ghost-btn {{ display: inline-flex; margin-top: 20px; padding: 11px 17px; border: 1px solid #8e72ff; border-radius: 8px; color: #4f46e5; font-size: 14px; font-weight: 800; text-decoration: none; }}
    .rf-ring {{ width: 225px; aspect-ratio: 1; display: grid; place-items: center; margin: auto; border-radius: 999px; background: conic-gradient({score_color} {score * 3.6}deg, #e8ecf3 0); box-shadow: 0 22px 40px rgba(23,178,74,.18); }}
    .rf-ring-inner {{ width: 162px; aspect-ratio: 1; display: grid; place-items: center; border-radius: 999px; background: #fff; color: {score_color}; font-size: 54px; font-weight: 900; }}
    .rf-ring-inner span {{ display: block; margin-top: 4px; color: #354057; font-size: 18px; font-weight: 650; text-align: center; }}
    .rf-factbox {{ padding: 8px 20px; }}
    .rf-fact {{ display: grid; grid-template-columns: 44px 1fr; gap: 14px; align-items: center; padding: 18px 0; border-bottom: 1px solid #e8edf5; }}
    .rf-fact:last-child {{ border-bottom: 0; }}
    .rf-fact-icon {{ width: 42px; height: 42px; display: grid; place-items: center; border-radius: 12px; color: #6366f1; background: #f1edff; font-size: 22px; font-weight: 850; }}
    .rf-section {{ padding: 20px; }}
    .rf-section-head {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; }}
    .rf-title {{ color: #101426; font-size: 18px; font-weight: 600; }}
    .rf-small-link {{ color: #4f46e5; font-size: 13px; font-weight: 850; text-decoration: none; }}
    .rf-snapshot {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 18px; }}
    .rf-metric {{ min-height: 103px; display: grid; grid-template-columns: 52px 1fr; gap: 14px; align-items: center; padding: 18px; border: 1px solid #e3e8f3; border-radius: 10px; background: #fff; }}
    .rf-metric-icon {{ width: 40px; height: 40px; display: grid; place-items: center; border-radius: 999px; font-size: 21px; font-weight: 900; }}
    .green {{ color: #18ad47; background: #e9f9ef; }} .blue {{ color: #2867ff; background: #eaf1ff; }} .purple {{ color: #6366f1; background: #f0e9ff; }} .orange {{ color: #f08a18; background: #fff1df; }}
    .rf-metric-label {{ color: #273149; font-size: 13px; font-weight: 800; }} .rf-metric-value {{ color: #101426; font-size: 26px; line-height: 1.1; font-weight: 900; margin-top: 8px; }}
    .rf-grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
    .rf-budget-body {{ display: grid; grid-template-columns: 235px 1fr; gap: 24px; align-items: center; }}
    .rf-donut {{ width: 205px; aspect-ratio: 1; display: grid; place-items: center; border-radius: 999px; background: conic-gradient(#7462ee 0 {needs_pct:.2f}%, #ff9f2d {needs_pct:.2f}% {needs_pct + wants_pct:.2f}%, #22c55e {needs_pct + wants_pct:.2f}% 100%); }}
    .rf-donut-inner {{ width: 122px; aspect-ratio: 1; display: grid; place-items: center; border-radius: 999px; background: white; color: #111827; font-size: 21px; font-weight: 900; text-align: center; }}
    .rf-donut-inner span {{ display: block; color: #53617a; font-size: 12px; font-weight: 650; }}
    .rf-budget-row {{ display: grid; grid-template-columns: 1fr auto auto; gap: 16px; padding: 18px 16px; border: 1px solid #e3e8f3; border-bottom: 0; }}
    .rf-budget-row:first-child {{ border-radius: 10px 10px 0 0; }} .rf-budget-row:last-child {{ border-bottom: 1px solid #e3e8f3; border-radius: 0 0 10px 10px; }}
    .rf-dot-small {{ width: 16px; height: 16px; display: inline-block; margin-right: 10px; border-radius: 999px; vertical-align: -2px; }}
    .rf-insights-box {{ border: 1px solid #e3e8f3; border-radius: 10px; overflow: hidden; background: #fff; }}
    .rf-insight {{ display: grid; grid-template-columns: 35px 1fr; gap: 14px; align-items: start; padding: 15px 18px; border-bottom: 1px solid #e8edf5; }}
    .rf-insight:last-child {{ border-bottom: 0; }}
    .rf-status {{ width: 28px; height: 28px; display: grid; place-items: center; border-radius: 999px; font-size: 24px; font-weight: 900; }}
    .rf-status.ok {{ color: #22c55e; }} .rf-status.warn {{ color: #f59e0b; }}
    .rf-insight-title {{ color: #182036; font-size: 14px; font-weight: 850; }}
    .rf-rec-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; }}
    .rf-rec-card {{ min-height: 178px; padding: 20px; border: 1px solid #e3e8f3; border-radius: 10px; background: #fff; }}
    .rf-rec-icon {{ width: 46px; height: 46px; display: grid; place-items: center; float: left; margin-right: 16px; border-radius: 999px; color: #6e3df4; background: #f0e9ff; font-size: 24px; font-weight: 900; }}
    .rf-rec-title {{ color: #101426; font-size: 16px; font-weight: 900; margin-bottom: 8px; }}
    .rf-impact {{ clear: both; margin-top: 16px; padding: 12px; border-radius: 8px; }}
    .rf-impact-positive {{ background: #f0fdf4; }} .rf-impact-positive span, .rf-impact-positive strong {{ color: #15803d; }}
    .rf-impact-warning {{ background: #fff7ed; }} .rf-impact-warning span, .rf-impact-warning strong {{ color: #c2410c; }}
    .rf-impact span {{ display: block; font-size: 12px; font-weight: 800; }} .rf-impact strong {{ display: block; margin-top: 5px; font-size: 15px; }}
    .rf-timeline-row {{ position: relative; display: grid; grid-template-columns: 28px 1fr 60px; gap: 14px; padding: 8px 0; align-items: start; }}
    .rf-dot {{ width: 22px; height: 22px; display: grid; place-items: center; margin-top: 1px; border-radius: 999px; color: #fff; font-size: 13px; background: #6366f1; box-shadow: 0 0 0 5px #eeeaff; }}
    .rf-timeline-0 .rf-dot {{ background: #22c55e; box-shadow: 0 0 0 5px #dcfce7; }}
    .rf-timeline-0 .rf-muted {{ color: #22c55e; }}
    .rf-timeline-1 .rf-dot {{ background: #3b82f6; box-shadow: 0 0 0 5px #dbeafe; }}
    .rf-timeline-2 .rf-dot {{ background: #8b5cf6; box-shadow: 0 0 0 5px #ede9fe; }}
    .rf-timeline-3 .rf-dot {{ background: #f59e0b; box-shadow: 0 0 0 5px #ffedd5; }}
    .rf-timeline-4 .rf-dot {{ background: #6366f1; box-shadow: 0 0 0 5px #e0e7ff; }}
    .rf-year {{ color: #53617a; font-size: 13px; text-align: right; }}
    .rf-scenario-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 16px; }}
    .rf-scenario {{ display: flex; align-items: center; gap: 12px; min-height: 54px; padding: 14px 16px; border: 1px solid #e5e7eb; border-radius: 10px; color: #182036; font-weight: 850; background: #fff; transition: background 160ms ease, border-color 160ms ease, transform 160ms ease; }}
    .rf-scenario:hover {{ border-color: #6366f1; background: #fff; transform: translateY(-1px); }}
    .rf-scenario i {{ color: #6366f1; font-size: 23px; }}
    .rf-primary {{ display: block; margin-top: 16px; padding: 14px 18px; border-radius: 9px; text-align: center; color: white !important; font-weight: 900; text-decoration: none; background: linear-gradient(135deg, #2658ff, #7d36f6); }}
    .rf-export {{ display: grid; grid-template-columns: 1fr 260px 260px; gap: 18px; align-items: center; }}
    .export-btn {{ display: flex; align-items: center; gap: 12px; padding: 16px 20px; border: 1px solid #e5e7eb; border-radius: 12px; background: white; cursor: pointer; text-decoration: none; color: #101426 !important; }}
    .export-btn:hover {{ border-color: #6366f1; background: #f5f3ff; }}
    .export-icon {{ width: 40px; height: 40px; border-radius: 8px; display: flex; align-items: center; justify-content: center; }}
    .rf-download-title {{ color: #111827; font-size: 15px; font-weight: 900; }}
    @media (max-width: 960px) {{ .rf-nav {{ padding: 0 18px; }} .rf-links {{ gap: 4px; }} .rf-link {{ padding: 9px 10px; font-size: 12px; }} .rf-brand span {{ display: none; }} .rf-hero, .rf-grid-2, .rf-snapshot, .rf-rec-grid {{ grid-template-columns: 1fr; }} .rf-budget-body {{ grid-template-columns: 1fr; }} }}
    </style>
    <div class="rf-page">
        <nav class="rf-nav">
            <a class="rf-brand" href="?page=home"><div class="rf-logo"><i class="ti ti-sparkles"></i></div><span>AI Personal Finance Agent</span></a>
            <div class="rf-links">
                <a class="rf-link" href="?page=home">Home</a>
                <a class="rf-link" href="?page=questionnaire">Questionnaire</a>
                <a class="rf-link active" href="?page=report">Report</a>
                <a class="rf-link" href="?page=chat">Chat</a>
                <a class="rf-link" href="?page=scenarios">Scenarios</a>
                <div class="rf-avatar">{escape(_initials(profile))}</div>
            </div>
        </nav>
        <main class="rf-wrap">
            <section class="rf-card rf-hero">
                <div>
                    <div class="rf-kicker">Financial Health Score</div>
                    <div class="rf-score-line">{score}<span> / 100</span></div>
                    <div class="rf-label">{label}</div>
                    <div class="rf-muted">{escape(_score_description(score))}</div>
                    <a class="rf-ghost-btn" href="#ai-insights">View Key Insights →</a>
                </div>
                <div class="rf-ring"><div class="rf-ring-inner"><div>{score}<span>/100</span></div></div></div>
                <div class="rf-card rf-factbox">
                    <div class="rf-fact"><div class="rf-fact-icon"><i class="ti ti-arrow-up-right"></i></div><div><div class="rf-muted">Percentile</div><div class="rf-insight-title">{_percentile(score)}</div></div></div>
                    <div class="rf-fact"><div class="rf-fact-icon"><i class="ti ti-shield-check"></i></div><div><div class="rf-muted">Data Quality</div><div class="rf-insight-title">{data_quality}</div></div></div>
                    <div class="rf-fact"><div class="rf-fact-icon"><i class="ti ti-refresh"></i></div><div><div class="rf-muted">Last Updated</div><div class="rf-insight-title">{today}</div></div></div>
                </div>
            </section>

            <section class="rf-card rf-section">
                <div class="rf-section-head"><div class="rf-title">Financial Snapshot</div><a class="rf-small-link" href="#ai-insights">View Details →</a></div>
                <div class="rf-snapshot">
                    <div class="rf-metric"><div class="rf-metric-icon green"><i class="ti ti-cash"></i></div><div><div class="rf-metric-label">Monthly Income</div><div class="rf-metric-value">{_money(metrics["income"])}</div><div class="rf-muted">After-tax</div></div></div>
                    <div class="rf-metric"><div class="rf-metric-icon blue"><i class="ti ti-credit-card"></i></div><div><div class="rf-metric-label">Monthly Expenses</div><div class="rf-metric-value">{_money(metrics["expenses"])}</div><div class="rf-muted">Total</div></div></div>
                    <div class="rf-metric"><div class="rf-metric-icon purple"><i class="ti ti-trending-up"></i></div><div><div class="rf-metric-label">Savings Rate</div><div class="rf-metric-value">{_percent(metrics["savings_rate"])}</div><div class="rf-muted">{_score_label(score)}</div></div></div>
                    <div class="rf-metric"><div class="rf-metric-icon orange"><i class="ti ti-building-bank"></i></div><div><div class="rf-metric-label">Net Worth</div><div class="rf-metric-value">{_money(metrics["net_worth"])}</div><div class="rf-muted">Assets - Liabilities</div></div></div>
                </div>
            </section>

            <div class="rf-grid-2">
                <section class="rf-card rf-section">
                    <div class="rf-section-head"><div class="rf-title">Budget Analysis</div><a class="rf-small-link" href="#ai-insights">View Details →</a></div>
                    <div class="rf-budget-body">
                        <div class="rf-donut"><div class="rf-donut-inner"><div>{_money(metrics["expenses"])}<span>Total Expenses</span></div></div></div>
                        <div>
                            <div class="rf-budget-row"><div><span class="rf-dot-small" style="background:#7462ee"></span>Needs</div><strong>{_money(parts["needs"])}</strong><span>{needs_pct:.0f}%</span></div>
                            <div class="rf-budget-row"><div><span class="rf-dot-small" style="background:#ff9f2d"></span>Wants</div><strong>{_money(parts["wants"])}</strong><span>{wants_pct:.0f}%</span></div>
                            <div class="rf-budget-row"><div><span class="rf-dot-small" style="background:#22c55e"></span>Savings</div><strong>{_money(parts["savings"])}</strong><span>{savings_pct:.0f}%</span></div>
                        </div>
                    </div>
                    <div class="rf-muted" style="margin-top:18px; padding:12px 14px; border-radius:8px; background:#f7f9ff;">{escape(budget_tip)}</div>
                </section>
                <section class="rf-card rf-section" id="ai-insights">
                    <div class="rf-section-head"><div class="rf-title">AI Insights</div><a class="rf-small-link" href="#ai-insights">View All →</a></div>
                    <div class="rf-insights-box">{insight_rows}</div>
                </section>
            </div>

            <section class="rf-card rf-section">
                <div class="rf-section-head"><div class="rf-title">Personalized Recommendations</div><a class="rf-small-link" href="#ai-insights">View All →</a></div>
                <div class="rf-rec-grid">{recommendation_cards}</div>
            </section>

            <div class="rf-grid-2">
                <section class="rf-card rf-section">
                    <div class="rf-section-head"><div class="rf-title">Goal Timeline</div><a class="rf-small-link" href="#ai-insights">View All →</a></div>
                    {timeline_items}
                </section>
                <section class="rf-card rf-section">
                    <div class="rf-title">Scenario Preview</div>
                    <div class="rf-muted">Explore different life scenarios and see how they impact your financial future.</div>
                    <div class="rf-scenario-grid">
                        <div class="rf-scenario"><i class="ti ti-trending-up"></i><span>+20% Salary</span></div>
                        <div class="rf-scenario"><i class="ti ti-briefcase-off"></i><span>Lose Your Job</span></div>
                        <div class="rf-scenario"><i class="ti ti-home"></i><span>Buy a House</span></div>
                        <div class="rf-scenario"><i class="ti ti-car"></i><span>Buy a Car</span></div>
                        <div class="rf-scenario"><i class="ti ti-beach"></i><span>Retire at 55</span></div>
                        <div class="rf-scenario"><i class="ti ti-plus"></i><span>New Goal</span></div>
                    </div>
                    <a class="rf-primary" href="?page=scenarios">Open Scenario Planner →</a>
                </section>
            </div>
        </main>
    </div>
    """
    st.markdown(_compact_html(html), unsafe_allow_html=True)


def render_report_dashboard(profile: dict[str, Any]) -> None:
    """Render the dashboard and generate the DeepSeek report when needed."""
    if not st.session_state.get("financial_report"):
        with st.spinner("Analyzing your finances..."):
            try:
                st.session_state.financial_report = generate_financial_report(profile)
            except Exception as exc:
                st.session_state.financial_report_error = str(exc)

    report = st.session_state.get("financial_report", "")
    _render_report_html(profile, report)

    if not report:
        st.error(f"Could not generate report: {st.session_state.get('financial_report_error', 'Unknown error')}")
        if st.button("Try Again", type="primary"):
            st.session_state.financial_report_error = ""
            with st.spinner("Analyzing your finances..."):
                try:
                    st.session_state.financial_report = generate_financial_report(profile)
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not generate report: {exc}")
