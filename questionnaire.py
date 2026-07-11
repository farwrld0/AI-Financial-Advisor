"""Clean multi-step questionnaire for the AI Personal Finance Agent."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any

import streamlit as st


STEPS = [
    "Basic Info",
    "Income",
    "Fixed Expenses",
    "Variable Expenses",
    "Future Plans",
    "Planned Purchases",
]

CITY_OPTIONS = ["Select your city", "New York", "San Francisco", "Shanghai", "Tokyo", "London", "Other"]
STATE_OPTIONS = ["Select your state / province", "California", "New York", "Texas", "Shanghai", "Tokyo", "London", "Other"]
EMPLOYMENT_OPTIONS = ["Select your employment status", "Full-time", "Part-time", "Self-employed", "Student", "Unemployed"]
EDUCATION_OPTIONS = ["Select your education level", "High school", "Associate", "Bachelor's", "Master's", "Doctorate", "Other"]
PURCHASE_CATEGORY_OPTIONS = ["Electronics", "Furniture", "Clothing", "Appliances", "Travel", "Other"]
PURCHASE_PRIORITY_OPTIONS = ["High", "Medium", "Low"]
INTEREST_OPTIONS = ["Travel", "Fitness", "Gaming", "Cooking", "Reading", "Music", "Art", "Sports", "Technology", "Fashion", "Other"]
SKILL_OPTIONS = ["Programming", "Design", "Writing", "Marketing", "Teaching", "Finance", "Sales", "Engineering", "Healthcare", "Other"]
WEEKLY_FREE_HOURS_OPTIONS = ["Less than 5 hours", "5–10 hours", "10–20 hours", "More than 20 hours"]
SIDE_HUSTLE_OPTIONS = ["Yes, actively looking", "Open to it", "Not right now", "No"]
PROFILE_CACHE_PATH = Path(__file__).with_name(".user_profile_cache.json")


def compact_html(html: str) -> str:
    return "".join(line.strip() for line in html.splitlines())


def init_state() -> None:
    if "questionnaire_step" not in st.session_state:
        st.session_state.questionnaire_step = 0
    if "answers" not in st.session_state:
        st.session_state.answers = {}
    if "user_profile" not in st.session_state:
        st.session_state.user_profile = {}
    if "planned_purchase_count" not in st.session_state:
        existing = st.session_state.get("answers", {}).get("planned_purchases", [])
        st.session_state.planned_purchase_count = max(1, len(existing) if isinstance(existing, list) else 1)


def get_profile_value(key: str, default: Any) -> Any:
    return st.session_state.get("answers", {}).get(key, st.session_state.get("user_profile", {}).get(key, default))


def save_answers(values: dict[str, Any]) -> None:
    st.session_state.answers.update(values)
    st.session_state.user_profile.update(values)


def parse_money(value: Any) -> float:
    text = str(value or "0").replace("$", "").replace(",", "").strip()
    try:
        return max(0.0, float(text or 0))
    except ValueError:
        return 0.0


def money(value: Any) -> str:
    try:
        return f"${float(value or 0):,.0f}"
    except (TypeError, ValueError):
        return "$0"


def profile_has_data(profile: Any) -> bool:
    if not isinstance(profile, dict):
        return False
    meaningful_keys = (
        "total_monthly_income",
        "monthly_income_after_tax",
        "total_monthly_expenses",
        "total_fixed_expenses",
        "total_variable_expenses",
        "total_assets",
        "net_worth",
        "age",
    )
    return any(profile.get(key) not in ("", None, 0, 0.0) for key in meaningful_keys)


def save_profile_cache(profile: dict[str, Any]) -> None:
    if not profile_has_data(profile):
        return
    try:
        PROFILE_CACHE_PATH.write_text(json.dumps(profile, indent=2, sort_keys=True))
    except OSError:
        pass


def set_step(step: int) -> None:
    st.session_state.questionnaire_step = max(0, min(len(STEPS), step))
    st.rerun()


def option_index(options: list[str], value: Any) -> int:
    text = str(value or "")
    return options.index(text) if text in options else 0


def seed_text(key: str, default: Any = "") -> None:
    if key not in st.session_state:
        st.session_state[key] = str(get_profile_value(key, default) or "")


def render_global_questionnaire_style() -> None:
    st.markdown(
        compact_html(
            """
            <style>
            html, body, .stApp, [data-testid="stAppViewContainer"] {
                color-scheme: light !important;
                color: #0b1020 !important;
                font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", Inter, sans-serif;
                background:
                    radial-gradient(circle at 8% 78%, rgba(45, 111, 255, .11), transparent 21rem),
                    radial-gradient(circle at 100% 34%, rgba(126, 55, 246, .13), transparent 24rem),
                    linear-gradient(180deg, #ffffff 0%, #f8fbff 100%) !important;
            }
            * { color-scheme: light !important; }
            #MainMenu, header[data-testid="stHeader"], footer, section[data-testid="stSidebar"] { display: none !important; }
            .block-container { max-width: 1220px !important; padding: 0 0 38px !important; }
            .q-nav {
                height: 58px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin: 0 0 24px;
                padding: 0 10px;
                border-bottom: 1px solid #e8edf5;
                background: rgba(255,255,255,.92);
                backdrop-filter: blur(22px);
            }
            .q-brand, .q-links, .q-right { display: flex; align-items: center; }
            .q-brand { gap: 14px; color: #0f172a; font-size: 20px; font-weight: 850; }
            .q-logo {
                width: 36px; height: 36px; display: grid; place-items: center; border-radius: 11px;
                color: white; background: linear-gradient(135deg, #245fff, #7b35f6);
                box-shadow: 0 16px 28px rgba(82,74,245,.22);
            }
            .q-logo::before { content: "✦"; font-size: 22px; }
            .q-right { gap: 28px; }
            .q-links { gap: 24px; }
            .q-link {
                padding: 10px 16px; border-radius: 13px; color: #273044; text-decoration: none;
                font-size: 14px; font-weight: 650;
            }
            .q-link.active {
                color: #5731ed;
                background: linear-gradient(135deg, rgba(33,101,255,.09), rgba(126,55,246,.13));
            }
            .q-avatar {
                width: 40px; height: 40px; display: grid; place-items: center; border-radius: 999px;
                color: #5d34ee; font-size: 15px; font-weight: 850;
                background: linear-gradient(135deg, #eee9ff, #e3d4ff);
            }
            .q-sidebar {
                min-height: 520px;
                padding: 22px 20px 18px;
                border: 1px solid rgba(224,229,239,.95);
                border-radius: 16px;
                background: rgba(255,255,255,.92);
                box-shadow: 0 16px 46px rgba(18,31,56,.08);
            }
            .q-card-head {
                display: flex;
                align-items: center;
                gap: 18px;
                padding: 22px 24px 20px;
                border-bottom: 1px solid #e8edf5;
            }
            .q-icon {
                width: 46px;
                height: 46px;
                display: grid;
                place-items: center;
                border-radius: 14px;
                color: #6138f5;
                font-size: 25px;
                line-height: 1;
                background: linear-gradient(135deg, #eef4ff, #f0e9ff);
            }
            .q-title { margin: 0; color: #0b1020; font-size: 22px; line-height: 1.1; font-weight: 850; }
            .q-subtitle { margin: 5px 0 0; color: #52627a; font-size: 13px; }
            .kicker { margin: 0 0 4px; color: #2867ff; font-size: 15px; font-weight: 850; }
            .side-title { margin: 0; color: #0b1020; font-size: 18px; font-weight: 850; }
            .side-copy { margin: 10px 0 22px; color: #5a667c; font-size: 12px; line-height: 1.45; }
            .step-row { position: relative; display: grid; grid-template-columns: 34px 1fr; gap: 12px; min-height: 53px; }
            .step-row:not(:last-child)::after {
                content: ""; position: absolute; left: 15px; top: 28px; bottom: -3px; width: 2px;
                border-radius: 999px; background: #e7ebf3;
            }
            .step-dot {
                position: relative; z-index: 1; width: 30px; height: 30px; display: grid; place-items: center;
                border-radius: 999px; color: #758196; font-size: 14px; font-weight: 850; background: #eef2f7;
            }
            .step-row.active .step-dot, .step-row.done .step-dot {
                color: #fff; background: linear-gradient(135deg, #2367ff, #7735f5);
                box-shadow: 0 12px 24px rgba(91,70,245,.28);
            }
            .step-name { margin: 1px 0 2px; color: #1c2434; font-size: 13px; font-weight: 850; }
            .step-row.active .step-name { color: #5d35f2; }
            .step-desc { margin: 0; color: #718097; font-size: 11px; line-height: 1.2; }
            .privacy {
                display: grid; grid-template-columns: 34px 1fr; gap: 12px; margin-top: 20px; padding: 12px;
                border-radius: 10px; background: linear-gradient(135deg, rgba(242,247,255,.96), rgba(247,243,255,.96));
            }
            .privacy-icon {
                width: 30px; height: 30px; display: grid; place-items: center; border-radius: 10px;
                color: #4a64ff; background: rgba(255,255,255,.78);
            }
            .privacy-title { margin: 0 0 2px; color: #293244; font-size: 12px; font-weight: 850; }
            .privacy-copy { margin: 0; color: #657289; font-size: 11px; line-height: 1.25; }
            div[data-testid="stVerticalBlockBorderWrapper"] {
                min-height: 520px !important;
                overflow: visible !important;
                border: 1px solid rgba(224,229,239,.95) !important;
                border-radius: 16px !important;
                background: rgba(255,255,255,.92) !important;
                box-shadow: 0 16px 46px rgba(18,31,56,.08) !important;
            }
            div[data-testid="stVerticalBlockBorderWrapper"] > div { padding: 0 24px 18px !important; background: transparent !important; }
            div[data-testid="stVerticalBlockBorderWrapper"] > div > div:first-child { margin-left: -24px !important; margin-right: -24px !important; }
            div[data-testid="stTextInput"] label p,
            div[data-testid="stSelectbox"] label p,
            div[data-testid="stRadio"] label p { color: #0b1020 !important; font-size: 12px !important; font-weight: 850 !important; }
            div[data-testid="stTextInput"], div[data-testid="stSelectbox"] { margin-bottom: 12px !important; }
            div[data-baseweb="input"], div[data-baseweb="base-input"], div[data-baseweb="select"] > div {
                min-height: 39px !important;
                border: 1px solid #dce3ee !important;
                border-radius: 8px !important;
                background: #ffffff !important;
                box-shadow: none !important;
            }
            div[data-baseweb="input"]:focus-within, div[data-baseweb="select"]:focus-within > div {
                border-color: #7357f6 !important;
                box-shadow: 0 0 0 4px rgba(103,84,246,.13) !important;
            }
            div[data-baseweb="input"] input,
            div[data-baseweb="base-input"] input,
            div[data-testid="stTextInput"] input {
                height: 37px !important;
                color: #0b1020 !important;
                -webkit-text-fill-color: #0b1020 !important;
                font-size: 13px !important;
                font-weight: 500 !important;
                background: #ffffff !important;
                caret-color: #2367ff !important;
                opacity: 1 !important;
            }
            input:-webkit-autofill,
            input:-webkit-autofill:hover,
            input:-webkit-autofill:focus,
            input:-webkit-autofill:active {
                -webkit-text-fill-color: #0b1020 !important;
                box-shadow: 0 0 0 1000px #ffffff inset !important;
                transition: background-color 999999s ease-in-out 0s !important;
            }
            div[data-testid="stTextInput"] input::placeholder {
                color: #8a97ad !important;
                -webkit-text-fill-color: #8a97ad !important;
                opacity: 1 !important;
            }
            div[data-baseweb="select"] span, div[data-baseweb="select"] div { color: #0b1020 !important; }
            div[data-baseweb="select"] svg { color: #64748b !important; fill: #64748b !important; }
            div[data-testid="stButton"] button {
                color: #1f2937 !important;
                border: 1px solid #dce3ee !important;
                background: #ffffff !important;
                box-shadow: none !important;
                height: 40px !important; border-radius: 9px !important; font-size: 13px !important;
                font-weight: 850 !important;
            }
            div[data-testid="stButton"] button[kind="primary"],
            button[data-testid="baseButton-primary"] {
                color: #fff !important; border: 0 !important;
                background: linear-gradient(135deg, #2367ff 0%, #7b35f6 100%) !important;
                box-shadow: 0 16px 32px rgba(86,72,245,.28) !important;
            }
            .q-summary {
                min-height: 72px; display: grid; grid-template-columns: 1fr 1fr; margin-top: 14px;
                border-radius: 10px; background: linear-gradient(135deg, rgba(242,247,255,.94), rgba(247,243,255,.96));
            }
            .q-summary.one { grid-template-columns: 1fr; }
            .q-summary-item { display: grid; grid-template-columns: 42px 1fr; gap: 14px; align-items: center; padding: 14px 22px; }
            .q-summary-item + .q-summary-item { border-left: 1px solid rgba(218,224,237,.95); }
            .q-summary-icon {
                width: 34px; height: 34px; display: grid; place-items: center; border-radius: 10px;
                color: #6138f5; background: rgba(255,255,255,.66);
            }
            .q-summary-label { margin: 0 0 4px; color: #52627a; font-size: 12px; font-weight: 750; }
            .q-summary-value { margin: 0; color: #0b1020; font-size: 21px; font-weight: 900; }
            .q-divider { height: 1px; margin: 18px 0 16px; background: #e8edf5; }
            .q-help { margin: 0 0 12px; color: #52627a; font-size: 13px; line-height: 1.45; }
            .stApp div[data-testid="stSegmentedControl"] {
                margin-top: 7px !important;
                margin-bottom: 14px !important;
            }
            .stApp div[data-testid="stSegmentedControl"] div[role="radiogroup"] {
                display: grid !important;
                grid-template-columns: repeat(5, 1fr) !important;
                gap: 10px !important;
                width: 100% !important;
            }
            .stApp div[data-testid="stSegmentedControl"] button,
            .stApp div[data-testid="stSegmentedControl"] label {
                min-height: 40px !important;
                border-radius: 7px !important;
                border: 1px solid #dce3ee !important;
                background: #fff !important;
                color: #0b1020 !important;
                font-size: 13px !important;
                font-weight: 750 !important;
            }
            .stApp div[data-testid="stSegmentedControl"] button[aria-pressed="true"],
            .stApp div[data-testid="stSegmentedControl"] label:has(input:checked) {
                border-color: #835cff !important;
                color: #5731ed !important;
                background: linear-gradient(135deg, rgba(35,103,255,.05), rgba(123,53,246,.10)) !important;
            }
            .q-divider {
                margin: 13px 0 11px !important;
            }
            .stApp div[data-testid="stButton"] button[kind="primary"],
            .stApp button[data-testid="baseButton-primary"] {
                max-width: 180px !important;
                margin-left: auto !important;
            }
            @media (max-width: 980px) {
                .q-nav { height: auto; align-items: flex-start; flex-direction: column; gap: 14px; padding-top: 16px; padding-bottom: 16px; }
                .q-links { flex-wrap: wrap; gap: 8px; }
            }
            </style>
            """
        ),
        unsafe_allow_html=True,
    )


def render_top_nav() -> None:
    st.html(
        compact_html(
            """
            <nav class="q-nav">
                <div class="q-brand"><span class="q-logo"></span><span>AI Finance Agent</span></div>
                <div class="q-right">
                    <div class="q-links">
                        <a class="q-link" href="?page=home">Home</a>
                        <a class="q-link active" href="?page=questionnaire">Questionnaire</a>
                        <a class="q-link" href="?page=report">Report</a>
                        <a class="q-link" href="?page=chat">Chat</a>
                        <a class="q-link" href="?page=scenarios">Scenarios</a>
                    </div>
                    <span class="q-avatar">KM</span>
                </div>
            </nav>
            """
        )
    )


def step_info(step: int) -> tuple[str, str]:
    info = {
        0: ("Basic Information", "Let's start with some basic details about you."),
        1: ("Income & Assets", "Tell us about your financial resources and risk profile."),
        2: ("Fixed Expenses", "Tell us about your essential monthly fixed expenses."),
        3: ("Variable Spending", "Tell us about your monthly flexible spending."),
        4: ("Goals & Constraints", "Tell us about future plans and constraints."),
        5: ("Planned Purchases", "List major items you may want to buy."),
    }
    return info.get(step, ("Questionnaire", ""))


def render_stepper(current_step: int) -> None:
    title, copy = step_info(current_step)
    rows = [
        ("Basic Information", "Let's start with some basic details about you."),
        ("Income & Assets", "Your income, assets, and risk context."),
        ("Fixed Expenses", "Housing, insurance, loans."),
        ("Variable Spending", "Needs, wants, and monthly habits."),
        ("Goals & Constraints", "Future plans and debt."),
        ("Planned Purchases", "Major upcoming items."),
    ]
    row_html = []
    for index, (name, desc) in enumerate(rows):
        if index < current_step:
            state = "done"
            dot = "✓"
            status = "Completed"
        elif index == current_step:
            state = "active"
            dot = str(index + 1)
            status = "In progress"
        else:
            state = ""
            dot = str(index + 1)
            status = desc
        row_html.append(
            f'<div class="step-row {state}"><div class="step-dot">{dot}</div>'
            f'<div><p class="step-name">{escape(name)}</p><p class="step-desc">{escape(status)}</p></div></div>'
        )
    st.html(
        compact_html(
            f"""
            <aside class="q-sidebar">
                <p class="kicker">Step {current_step + 1} of {len(STEPS)}</p>
                <h2 class="side-title">{escape(title)}</h2>
                <p class="side-copy">{escape(copy)}</p>
                {''.join(row_html)}
                <div class="privacy">
                    <div class="privacy-icon">⌁</div>
                    <div><p class="privacy-title">Your data is private and secure.</p><p class="privacy-copy">Your data is encrypted and never shared.</p></div>
                </div>
            </aside>
            """
        )
    )


def render_card_header(title: str, subtitle: str, icon: str) -> None:
    icons = {
        "user": "♙",
        "wallet": "▣",
        "home": "⌂",
        "cart": "▦",
        "target": "◎",
        "purchase": "◇",
    }
    st.html(
        compact_html(
            f"""
            <div class="q-card-head">
                <div class="q-icon">{escape(icons.get(icon, icons["user"]))}</div>
                <div><h1 class="q-title">{escape(title)}</h1><p class="q-subtitle">{escape(subtitle)}</p></div>
            </div>
            """
        )
    )


def render_layout(step: int):
    init_state()
    render_global_questionnaire_style()
    render_top_nav()
    left_col, right_col = st.columns([300, 920], gap="medium", vertical_alignment="top")
    with left_col:
        render_stepper(step)
    return right_col


def render_progress() -> None:
    step = st.session_state.get("questionnaire_step", 0)
    st.progress((step + 1) / len(STEPS), text=f"Step {step + 1} of {len(STEPS)}: {STEPS[step]}")


def render_basic_info() -> None:
    right_col = render_layout(0)
    seed_text("full_name")
    seed_text("age")
    with right_col:
        with st.container(border=True):
            render_card_header("Basic Information", "Tell us a little about yourself.", "user")
            col_1, col_2 = st.columns(2, gap="large")
            with col_1:
                st.text_input("Full Name", key="full_name", placeholder="Enter your full name")
                st.selectbox("City", CITY_OPTIONS, index=option_index(CITY_OPTIONS, get_profile_value("city", "")), key="city")
            with col_2:
                st.text_input("Age", key="age", placeholder="Enter your age")
                st.selectbox("State / Province", STATE_OPTIONS, index=option_index(STATE_OPTIONS, get_profile_value("state", "")), key="state")
            st.markdown("**Household Size**")
            st.markdown('<p class="q-help">Including yourself, how many people are in your household?</p>', unsafe_allow_html=True)
            household = st.segmented_control(
                "Household Size",
                options=["1", "2", "3", "4", "5+"],
                selection_mode="single",
                key="household_size",
                label_visibility="collapsed",
            )
            household = household or "1"
            col_3, col_4 = st.columns(2, gap="large")
            with col_3:
                st.selectbox(
                    "Employment Status",
                    EMPLOYMENT_OPTIONS,
                    index=option_index(EMPLOYMENT_OPTIONS, get_profile_value("employment_status", "")),
                    key="employment_status",
                )
            with col_4:
                st.selectbox(
                    "Education Level",
                    EDUCATION_OPTIONS,
                    index=option_index(EDUCATION_OPTIONS, get_profile_value("education_level", "")),
                    key="education_level",
                )
            st.html('<div class="q-divider"></div>')
            back_col, spacer_col, next_col = st.columns([1.15, 4.7, 1.65])
            with back_col:
                st.button("← Back", key="basic_back", disabled=True)
            with spacer_col:
                st.empty()
            with next_col:
                if st.button("Next: Income →", type="primary", key="basic_next", use_container_width=True):
                    values = {
                        "full_name": st.session_state.full_name,
                        "age": st.session_state.age,
                        "city": "" if st.session_state.city == CITY_OPTIONS[0] else st.session_state.city,
                        "state": "" if st.session_state.state == STATE_OPTIONS[0] else st.session_state.state,
                        "household_size": household,
                        "employment_status": "" if st.session_state.employment_status == EMPLOYMENT_OPTIONS[0] else st.session_state.employment_status,
                        "education_level": "" if st.session_state.education_level == EDUCATION_OPTIONS[0] else st.session_state.education_level,
                    }
                    save_answers(values)
                    set_step(1)


def render_income() -> None:
    right_col = render_layout(1)
    for key in [
        "monthly_income_after_tax",
        "secondary_income",
        "cash_savings",
        "checking_account",
        "investment_accounts",
        "retirement_accounts",
    ]:
        seed_text(key, 0)
    with right_col:
        with st.container(border=True):
            render_card_header("Income & Assets", "Tell us about your financial resources and risk profile.", "wallet")
            col_1, col_2 = st.columns(2, gap="large")
            with col_1:
                st.text_input("Monthly Income", key="monthly_income_after_tax", placeholder="Enter amount")
                st.text_input("Cash / Savings", key="cash_savings", placeholder="Enter amount")
                st.text_input("Investment Account", key="investment_accounts", placeholder="Enter amount")
                st.selectbox("Emergency Fund", ["Select an option", "Less than 1 month", "1-3 months", "3-6 months", "6-12 months", "12+ months"], key="emergency_fund_months")
            with col_2:
                st.text_input("Side Income", key="secondary_income", placeholder="Enter amount")
                st.text_input("Checking Account", key="checking_account", placeholder="Enter amount")
                st.text_input("Retirement Account", key="retirement_accounts", placeholder="Enter amount")
                st.selectbox("Risk Preference", ["Select an option", "Conservative", "Balanced", "Growth", "Aggressive"], key="risk_preference")
            total_income = parse_money(st.session_state.monthly_income_after_tax) + parse_money(st.session_state.secondary_income)
            total_assets = (
                parse_money(st.session_state.cash_savings)
                + parse_money(st.session_state.checking_account)
                + parse_money(st.session_state.investment_accounts)
                + parse_money(st.session_state.retirement_accounts)
            )
            st.html(
                compact_html(
                    f"""
                    <div class="q-summary">
                        <div class="q-summary-item"><div class="q-summary-icon">▦</div><div><p class="q-summary-label">Total Monthly Income</p><p class="q-summary-value">{money(total_income)}</p></div></div>
                        <div class="q-summary-item"><div class="q-summary-icon">◔</div><div><p class="q-summary-label">Total Assets</p><p class="q-summary-value">{money(total_assets)}</p></div></div>
                    </div>
                    <div class="q-divider"></div>
                    """
                )
            )
            back_col, spacer_col, next_col = st.columns([1, 3.2, 1.75])
            with back_col:
                if st.button("← Back", key="income_back"):
                    set_step(0)
            with spacer_col:
                st.empty()
            with next_col:
                if st.button("Next: Fixed Expenses →", type="primary", key="income_next", use_container_width=True):
                    values = {
                        "monthly_income_after_tax": parse_money(st.session_state.monthly_income_after_tax),
                        "secondary_income": parse_money(st.session_state.secondary_income),
                        "cash_savings": parse_money(st.session_state.cash_savings),
                        "checking_account": parse_money(st.session_state.checking_account),
                        "investment_accounts": parse_money(st.session_state.investment_accounts),
                        "retirement_accounts": parse_money(st.session_state.retirement_accounts),
                        "emergency_fund_months": "" if st.session_state.emergency_fund_months == "Select an option" else st.session_state.emergency_fund_months,
                        "risk_preference": "" if st.session_state.risk_preference == "Select an option" else st.session_state.risk_preference,
                        "total_monthly_income": total_income,
                        "total_assets": total_assets,
                        "net_worth": total_assets - parse_money(get_profile_value("total_debt", 0)),
                    }
                    save_answers(values)
                    set_step(2)


def render_fixed_expenses() -> None:
    right_col = render_layout(2)
    fields = [
        ("rent_mortgage", "Housing (Rent / Mortgage)"),
        ("utilities", "Utilities (Electric, Water, Gas, etc.)"),
        ("insurance", "Insurance (Health, Auto, Home, etc.)"),
        ("transportation_fixed", "Transportation (Car, Public Transit, etc.)"),
        ("loan_repayments", "Loan Payments (Student, Personal, etc.)"),
        ("subscriptions", "Subscriptions (Netflix, Spotify, etc.)"),
        ("internet_phone", "Internet / Phone"),
        ("other_fixed_expenses", "Other Fixed Expenses"),
    ]
    for key, _ in fields:
        seed_text(key, 0)
    with right_col:
        with st.container(border=True):
            render_card_header("Fixed Expenses", "Tell us about your essential monthly fixed expenses.", "home")
            columns = st.columns(2, gap="large")
            for index, (key, label) in enumerate(fields):
                with columns[index % 2]:
                    st.text_input(label, key=key, placeholder="0")
            total = sum(parse_money(st.session_state[key]) for key, _ in fields)
            st.html(
                compact_html(
                    f"""
                    <div class="q-summary one">
                        <div class="q-summary-item"><div class="q-summary-icon">▦</div><div><p class="q-summary-label">Total Monthly Fixed Expenses</p><p class="q-summary-value">{money(total)}</p></div></div>
                    </div>
                    <div class="q-divider"></div>
                    """
                )
            )
            back_col, spacer_col, next_col = st.columns([1, 3.2, 1.75])
            with back_col:
                if st.button("← Back", key="fixed_back"):
                    set_step(1)
            with spacer_col:
                st.empty()
            with next_col:
                if st.button("Next: Variable Spending →", type="primary", key="fixed_next", use_container_width=True):
                    values = {key: parse_money(st.session_state[key]) for key, _ in fields}
                    values["total_fixed_expenses"] = total
                    save_answers(values)
                    set_step(3)


def render_variable_expenses() -> None:
    right_col = render_layout(3)
    fields = [
        ("groceries", "Groceries"),
        ("dining_out", "Dining Out"),
        ("entertainment", "Entertainment"),
        ("shopping", "Shopping"),
        ("travel", "Travel"),
        ("other_variable_expenses", "Other Variable Spending"),
    ]
    for key, _ in fields:
        seed_text(key, 0)
    with right_col:
        with st.container(border=True):
            render_card_header("Variable Spending", "Tell us about your monthly flexible spending.", "cart")
            columns = st.columns(2, gap="large")
            for index, (key, label) in enumerate(fields):
                with columns[index % 2]:
                    st.text_input(label, key=key, placeholder="0")
            total = sum(parse_money(st.session_state[key]) for key, _ in fields)
            st.html(
                compact_html(
                    f"""
                    <div class="q-summary one">
                        <div class="q-summary-item"><div class="q-summary-icon">▦</div><div><p class="q-summary-label">Total Monthly Variable Spending</p><p class="q-summary-value">{money(total)}</p></div></div>
                    </div>
                    <div class="q-divider"></div>
                    """
                )
            )
            back_col, spacer_col, next_col = st.columns([1, 3.2, 1.75])
            with back_col:
                if st.button("← Back", key="variable_back"):
                    set_step(2)
            with spacer_col:
                st.empty()
            with next_col:
                if st.button("Next: Goals & Constraints →", type="primary", key="variable_next", use_container_width=True):
                    values = {key: parse_money(st.session_state[key]) for key, _ in fields}
                    values["total_variable_expenses"] = total
                    save_answers(values)
                    set_step(4)


def render_future_plans() -> None:
    right_col = render_layout(4)
    seed_text("total_debt", 0)
    seed_text("target_savings", 0)
    with right_col:
        with st.container(border=True):
            render_card_header("Goals & Constraints", "Tell us about future plans and debt.", "target")
            col_1, col_2 = st.columns(2, gap="large")
            with col_1:
                st.text_input("Total Debt", key="total_debt", placeholder="0")
                st.text_input("Target Savings", key="target_savings", placeholder="0")
            with col_2:
                st.selectbox("Primary Goal", ["Select an option", "Build emergency fund", "Pay off debt", "Buy a home", "Invest more", "Retire early"], key="primary_goal")
                st.selectbox("Timeline", ["Select an option", "0-1 year", "1-3 years", "3-5 years", "5+ years"], key="goal_timeline")
            st.html('<div class="q-divider"></div>')
            back_col, spacer_col, next_col = st.columns([1, 3.2, 1.75])
            with back_col:
                if st.button("← Back", key="goals_back"):
                    set_step(3)
            with spacer_col:
                st.empty()
            with next_col:
                if st.button("Next: Planned Purchases →", type="primary", key="goals_next", use_container_width=True):
                    values = {
                        "total_debt": parse_money(st.session_state.total_debt),
                        "target_savings": parse_money(st.session_state.target_savings),
                        "primary_goal": "" if st.session_state.primary_goal == "Select an option" else st.session_state.primary_goal,
                        "goal_timeline": "" if st.session_state.goal_timeline == "Select an option" else st.session_state.goal_timeline,
                    }
                    save_answers(values)
                    set_step(5)


def render_planned_purchases() -> None:
    right_col = render_layout(5)
    existing = get_profile_value("planned_purchases", [])
    existing_interests = get_profile_value("interests", [])
    existing_skills = get_profile_value("skills", [])
    if "interests" not in st.session_state:
        st.session_state.interests = existing_interests if isinstance(existing_interests, list) else []
    if "skills" not in st.session_state:
        st.session_state.skills = existing_skills if isinstance(existing_skills, list) else []
    if "weekly_free_hours" not in st.session_state:
        weekly_value = get_profile_value("weekly_free_hours", WEEKLY_FREE_HOURS_OPTIONS[0])
        st.session_state.weekly_free_hours = weekly_value if weekly_value in WEEKLY_FREE_HOURS_OPTIONS else WEEKLY_FREE_HOURS_OPTIONS[0]
    if "open_to_side_hustle" not in st.session_state:
        side_hustle_value = get_profile_value("open_to_side_hustle", SIDE_HUSTLE_OPTIONS[1])
        st.session_state.open_to_side_hustle = side_hustle_value if side_hustle_value in SIDE_HUSTLE_OPTIONS else SIDE_HUSTLE_OPTIONS[1]
    if isinstance(existing, list):
        st.session_state.planned_purchase_count = max(st.session_state.get("planned_purchase_count", 1), len(existing), 1)
        for index, item in enumerate(existing):
            if not isinstance(item, dict):
                continue
            st.session_state.setdefault(f"purchase_name_{index}", str(item.get("name", "")))
            st.session_state.setdefault(f"purchase_cost_{index}", float(item.get("cost", 0) or 0))
            category = item.get("category", PURCHASE_CATEGORY_OPTIONS[0])
            priority = item.get("priority", PURCHASE_PRIORITY_OPTIONS[1])
            st.session_state.setdefault(
                f"purchase_category_{index}",
                category if category in PURCHASE_CATEGORY_OPTIONS else PURCHASE_CATEGORY_OPTIONS[0],
            )
            st.session_state.setdefault(
                f"purchase_priority_{index}",
                priority if priority in PURCHASE_PRIORITY_OPTIONS else PURCHASE_PRIORITY_OPTIONS[1],
            )

    with right_col:
        with st.container(border=True):
            render_card_header("Planned Purchases", "Add major items you may want to buy in the future.", "purchase")
            st.html(
                compact_html(
                    """
                    <p class="q-help">Include larger upcoming purchases so your financial report can account for near-term spending pressure.</p>
                    """
                )
            )

            for index in range(st.session_state.planned_purchase_count):
                if index:
                    st.html('<div class="q-divider"></div>')
                cols = st.columns([2.1, 1.25, 1.35, 1.15], gap="large")
                with cols[0]:
                    st.text_input("Item name", key=f"purchase_name_{index}", placeholder="Laptop, sofa, trip...")
                with cols[1]:
                    st.number_input(
                        "Estimated cost",
                        min_value=0.0,
                        step=50.0,
                        key=f"purchase_cost_{index}",
                        format="%.2f",
                    )
                with cols[2]:
                    st.selectbox("Category", PURCHASE_CATEGORY_OPTIONS, key=f"purchase_category_{index}")
                with cols[3]:
                    st.selectbox("Priority", PURCHASE_PRIORITY_OPTIONS, key=f"purchase_priority_{index}")

            purchases = []
            for index in range(st.session_state.planned_purchase_count):
                name = str(st.session_state.get(f"purchase_name_{index}", "") or "").strip()
                cost = float(st.session_state.get(f"purchase_cost_{index}", 0) or 0)
                category = st.session_state.get(f"purchase_category_{index}", PURCHASE_CATEGORY_OPTIONS[0])
                priority = st.session_state.get(f"purchase_priority_{index}", PURCHASE_PRIORITY_OPTIONS[1])
                if name or cost > 0:
                    purchases.append({"name": name, "cost": cost, "category": category, "priority": priority})

            st.html(
                compact_html(
                    """
                    <div class="q-divider"></div>
                    <p class="q-help">Your interests, skills, and available time help us suggest realistic ways to earn or save more.</p>
                    """
                )
            )
            interest_col, skill_col = st.columns(2, gap="large")
            with interest_col:
                st.multiselect(
                    "What are your main interests or hobbies?",
                    INTEREST_OPTIONS,
                    key="interests",
                )
                st.selectbox(
                    "How many hours of free time do you have per week?",
                    WEEKLY_FREE_HOURS_OPTIONS,
                    key="weekly_free_hours",
                )
            with skill_col:
                st.multiselect(
                    "What are your main skills?",
                    SKILL_OPTIONS,
                    key="skills",
                )
                st.radio(
                    "Are you open to starting a side hustle or extra income stream?",
                    SIDE_HUSTLE_OPTIONS,
                    key="open_to_side_hustle",
                )

            total = sum(item["cost"] for item in purchases)
            st.html(
                compact_html(
                    f"""
                    <div class="q-summary one">
                        <div class="q-summary-item"><div class="q-summary-icon">◇</div><div><p class="q-summary-label">Planned Purchase Total</p><p class="q-summary-value">{money(total)}</p></div></div>
                    </div>
                    <div class="q-divider"></div>
                    """
                )
            )

            add_col, spacer_col, back_col, submit_col = st.columns([1.7, 2.2, 1, 1.75])
            with add_col:
                if st.button("+ Add another item", key="add_planned_purchase", use_container_width=True):
                    st.session_state.planned_purchase_count += 1
                    st.rerun()
            with spacer_col:
                st.empty()
            with back_col:
                if st.button("← Back", key="planned_back"):
                    set_step(4)
            with submit_col:
                if st.button("Submit & View Report →", type="primary", key="planned_submit", use_container_width=True):
                    save_answers(
                        {
                            "planned_purchases": purchases,
                            "interests": st.session_state.interests,
                            "skills": st.session_state.skills,
                            "weekly_free_hours": st.session_state.weekly_free_hours,
                            "open_to_side_hustle": st.session_state.open_to_side_hustle,
                        }
                    )
                    profile = build_complete_profile()
                    st.session_state.profile = profile
                    st.session_state.user_profile = profile
                    st.session_state.questionnaire_complete = True
                    st.session_state.questionnaire_step = len(STEPS)
                    save_profile_cache(profile)
                    st.session_state.selected_page = "📊 My Financial Report"
                    st.rerun()


def build_complete_profile() -> dict[str, Any]:
    profile = dict(st.session_state.get("answers", {}))
    fixed = float(profile.get("total_fixed_expenses", 0) or 0)
    variable = float(profile.get("total_variable_expenses", 0) or 0)
    income = float(profile.get("total_monthly_income", 0) or 0)
    assets = float(profile.get("total_assets", 0) or 0)
    debt = float(profile.get("total_debt", 0) or 0)
    profile["total_monthly_expenses"] = fixed + variable
    profile["monthly_surplus"] = income - profile["total_monthly_expenses"]
    profile["net_worth"] = assets - debt
    return profile


def render_summary() -> None:
    from report import render_report_dashboard

    profile = build_complete_profile()
    st.session_state.profile = profile
    st.session_state.user_profile = profile
    st.session_state.questionnaire_complete = True
    save_profile_cache(profile)

    render_report_dashboard(profile)


def render_questionnaire_page() -> None:
    step = st.session_state.get("questionnaire_step", 0)
    if step == 0:
        render_basic_info()
    elif step == 1:
        render_income()
    elif step == 2:
        render_fixed_expenses()
    elif step == 3:
        render_variable_expenses()
    elif step == 4:
        render_future_plans()
    elif step == 5:
        render_planned_purchases()
    else:
        render_summary()
