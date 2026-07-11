"""Main Streamlit router for the AI Personal Finance Agent."""

from __future__ import annotations

import copy
import html
import json
import os
import re
from pathlib import Path
from typing import Any

import streamlit as st

st.set_page_config(
    page_title="AI Personal Finance Agent",
    page_icon="💙",
    layout="wide",
    initial_sidebar_state="expanded",
)

from adapter import profile_to_session_dict, questionnaire_to_profile
import questionnaire
from home import render_global_style, render_home
from llm import ask_chatbot, run_scenario
from questionnaire_schema import create_sample_profile, validate_profile
from report import render_report_dashboard
from system_prompt_v2 import analyze_with_deepseek


PAGES = [
    "🏠 Home",
    "📋 Questionnaire",
    "📊 My Financial Report",
    "💬 Chat Advisor",
    "🔮 Scenario Planner",
]

PROFILE_CACHE_PATH = Path(__file__).with_name(".user_profile_cache.json")


def profile_has_data(profile: Any) -> bool:
    """Return True when a profile has enough questionnaire data to power analysis pages."""
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


def load_profile_cache() -> dict[str, Any]:
    """Load the most recent completed questionnaire profile for other Streamlit tabs."""
    try:
        if not PROFILE_CACHE_PATH.exists():
            return {}
        data = json.loads(PROFILE_CACHE_PATH.read_text())
        return data if profile_has_data(data) else {}
    except (OSError, json.JSONDecodeError, TypeError):
        return {}


def save_profile_cache(profile: dict[str, Any]) -> None:
    """Persist profile across Streamlit browser-tab sessions."""
    if not profile_has_data(profile):
        return
    try:
        PROFILE_CACHE_PATH.write_text(json.dumps(profile, indent=2, sort_keys=True))
    except OSError:
        pass


def init_app_state() -> None:
    """Initialize app-level state."""
    questionnaire.init_state()
    # Persist user_profile across page navigation.
    if "user_profile" not in st.session_state:
        st.session_state["user_profile"] = {}
    defaults = {
        "user_profile": {},
        "questionnaire_complete": False,
        "chat_history": [],
        "financial_report": "",
        "ai_analysis": "",
        "financial_report_error": "",
        "previous_profile": None,
        "use_sample_profile": False,
        "scenario_text": "",
        "scenario_result": "",
        "scenario_after_profile": {},
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    if not profile_has_data(st.session_state.get("user_profile")):
        cached_profile = load_profile_cache()
        if cached_profile:
            st.session_state.user_profile = cached_profile
            st.session_state.profile = cached_profile
            st.session_state.answers.update(cached_profile)
            st.session_state.questionnaire_complete = True


def sync_completed_profile() -> None:
    """Copy the completed questionnaire profile into app-level state."""
    if st.session_state.get("questionnaire_step", 0) >= len(questionnaire.STEPS):
        profile = questionnaire.build_complete_profile()
        st.session_state.user_profile = profile
        st.session_state.questionnaire_complete = True
        st.session_state.profile = profile
        if not st.session_state.get("use_sample_profile"):
            st.session_state.use_sample_profile = False
        save_profile_cache(profile)


def get_profile() -> dict[str, Any]:
    sync_completed_profile()
    profile = st.session_state.get("user_profile", {}) or {}
    if not profile_has_data(profile):
        cached_profile = load_profile_cache()
        if cached_profile:
            st.session_state.user_profile = cached_profile
            st.session_state.profile = cached_profile
            st.session_state.answers.update(cached_profile)
            st.session_state.questionnaire_complete = True
            return cached_profile
    return profile


def _go_to_questionnaire() -> None:
    st.session_state["nav_page"] = "📋 Questionnaire"


def go_to_questionnaire() -> None:
    _go_to_questionnaire()


def require_profile() -> dict[str, Any] | None:
    """Gate analysis pages until the questionnaire is complete."""
    profile = get_profile()
    if not st.session_state.get("questionnaire_complete") or not profile:
        st.warning("Please complete the questionnaire first before using this page.")
        st.button("Go to Questionnaire", type="primary", on_click=go_to_questionnaire)
        return None
    return profile


def money(value: Any) -> str:
    try:
        return f"${float(value or 0):,.0f}"
    except (TypeError, ValueError):
        return "$0"


def compact_html(markup: str) -> str:
    """Prevent indented raw HTML from being treated as Markdown code."""
    return "".join(line.strip() for line in markup.splitlines())


def profile_metrics(profile: dict[str, Any]) -> dict[str, float]:
    income = float(profile.get("total_monthly_income", 0) or 0)
    expenses = float(profile.get("total_monthly_expenses", 0) or 0)
    surplus = income - expenses
    savings_rate = (surplus / income * 100) if income else 0.0
    return {
        "income": income,
        "expenses": expenses,
        "surplus": surplus,
        "savings_rate": savings_rate,
    }


def render_sidebar_summary(profile: dict[str, Any]) -> None:
    """Show key financial stats in the sidebar."""
    st.sidebar.divider()
    st.sidebar.subheader("Financial Snapshot")
    if not profile:
        st.sidebar.info("Complete the questionnaire to unlock your snapshot.")
        return

    metrics = profile_metrics(profile)
    st.sidebar.metric("Monthly income", money(metrics["income"]))
    st.sidebar.metric("Monthly expenses", money(metrics["expenses"]))
    st.sidebar.metric("Monthly surplus", money(metrics["surplus"]))
    st.sidebar.metric("Savings rate", f"{metrics['savings_rate']:.1f}%")


def render_chat_sidebar_snapshot(profile: dict[str, Any]) -> None:
    """Render premium Chat Advisor sidebar stats below the existing navigation."""
    st.sidebar.divider()
    metrics = profile_metrics(profile)
    stat_cards = [
        ("💵", "Monthly Income", money(metrics["income"]), "Income after all sources", "#ecfdf5", "#10b981"),
        ("💳", "Monthly Expenses", money(metrics["expenses"]), "Recurring monthly spend", "#eff6ff", "#2563eb"),
        ("📈", "Savings Rate", f"{metrics['savings_rate']:.1f}%", "Income kept each month", "#f5f3ff", "#7c3aed"),
    ]
    cards_html = "".join(
        compact_html(
            f"""
        <div class="sidebar-stat-card">
            <div class="sidebar-stat-icon" style="background:{bg}; color:{color};">{icon}</div>
            <div>
                <div class="sidebar-stat-label">{label}</div>
                <div class="sidebar-stat-value">{value}</div>
                <div class="sidebar-stat-subtitle">{subtitle}</div>
            </div>
        </div>
        """
        )
        for icon, label, value, subtitle, bg, color in stat_cards
    )
    st.sidebar.markdown(
        compact_html(
            f"""
        <div class="sidebar-snapshot">
            <div class="sidebar-snapshot-title">Financial Snapshot</div>
            {cards_html}
        </div>
        """,
        ),
        unsafe_allow_html=True,
    )
    if st.sidebar.button("🗑 Clear Conversation", key="clear_chat_sidebar", use_container_width=True):
        st.session_state["chat_history"] = []
        st.rerun()


def _chat_net_worth(profile: dict[str, Any]) -> float:
    return (
        float(profile.get("cash_savings", 0) or 0)
        + float(profile.get("checking_account", 0) or 0)
        + float(profile.get("investment_accounts", 0) or 0)
        + float(profile.get("retirement_accounts", 0) or 0)
        - float(profile.get("total_debt", 0) or 0)
    )


def _chat_profile_metrics(profile: dict[str, Any]) -> dict[str, float]:
    metrics = profile_metrics(profile)
    if not metrics["expenses"]:
        expense_keys = [
            "rent_mortgage",
            "utilities",
            "insurance",
            "transportation_fixed",
            "loan_repayments",
            "groceries",
            "food",
            "dining_out",
            "entertainment",
            "shopping",
            "subscriptions",
        ]
        metrics["expenses"] = sum(float(profile.get(key, 0) or 0) for key in expense_keys)
        metrics["surplus"] = metrics["income"] - metrics["expenses"]
        metrics["savings_rate"] = (metrics["surplus"] / metrics["income"] * 100) if metrics["income"] else 0.0
    metrics["net_worth"] = _chat_net_worth(profile)
    return metrics


def render_chat_custom_sidebar(profile: dict[str, Any]) -> None:
    """Render a custom Apple-style sidebar for the Chat page."""
    nav_items = [
        ("📋", "Questionnaire", "?page=questionnaire", False),
        ("📊", "My Financial Report", "?page=report", False),
        ("💬", "Chat Advisor", "?page=chat", True),
        ("🔮", "Scenario Planner", "?page=scenarios", False),
    ]
    nav_html = "".join(
        compact_html(
            f"""
            <a class="chat-nav-item {'active' if active else ''}" href="{href}">
                <span>{icon}</span><strong>{label}</strong>
            </a>
            """
        )
        for icon, label, href, active in nav_items
    )
    st.sidebar.markdown(
        compact_html(
            f"""
            <div class="chat-side-shell">
                <div class="chat-side-brand">
                    <div class="chat-side-logo">✦</div>
                    <div>
                        <div class="chat-side-app">AI Finance Agent</div>
                        <div class="chat-side-sub">Personal dashboard</div>
                    </div>
                </div>
                <div class="chat-side-title">Navigation</div>
                <div class="chat-nav-list">{nav_html}</div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )
    if st.sidebar.button("🗑 Clear Conversation", key="chat_sidebar_clear", use_container_width=True):
        st.session_state["chat_history"] = []
        st.session_state.pop("pending_chat_question", None)
        st.rerun()


def render_questionnaire_page() -> None:
    """Render questionnaire.py inside the main app router."""
    questionnaire.render_questionnaire_page()
    if st.session_state.get("questionnaire_step", 0) >= len(questionnaire.STEPS):
        sync_completed_profile()


def render_report_page() -> None:
    """Generate and display the full DeepSeek financial report."""
    sync_completed_profile()
    raw_data = st.session_state.get("user_profile", {}) or {}
    if not raw_data:
        st.warning("Please complete the questionnaire first")
        col_1, col_2 = st.columns([1, 1])
        with col_1:
            st.button("Go to Questionnaire", type="primary", on_click=go_to_questionnaire)
        with col_2:
            if st.button("Use Sample Data (Demo)"):
                sample_profile = create_sample_profile()
                st.session_state.user_profile = profile_to_session_dict(sample_profile)
                st.session_state.profile = st.session_state.user_profile
                st.session_state.questionnaire_complete = True
                save_profile_cache(st.session_state.user_profile)
                st.session_state.financial_report = ""
                st.session_state.ai_analysis = ""
                st.session_state.financial_report_error = ""
                st.session_state.use_sample_profile = True
                st.rerun()
        return

    if st.button("Use Sample Data (Demo)"):
        sample_profile = create_sample_profile()
        st.session_state.user_profile = profile_to_session_dict(sample_profile)
        st.session_state.profile = st.session_state.user_profile
        st.session_state.questionnaire_complete = True
        save_profile_cache(st.session_state.user_profile)
        st.session_state.financial_report = ""
        st.session_state.ai_analysis = ""
        st.session_state.financial_report_error = ""
        st.session_state.use_sample_profile = True
        st.rerun()

    if st.session_state.get("use_sample_profile"):
        profile = create_sample_profile()
        dashboard_data = profile_to_session_dict(profile)
    else:
        profile = questionnaire_to_profile(raw_data)
        dashboard_data = raw_data

    errors = validate_profile(profile)
    if errors:
        st.warning("Some profile data is incomplete. Using best available data.")

    api_key = st.secrets.get("DEEPSEEK_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        st.error("Missing DEEPSEEK_API_KEY. Add it to Streamlit secrets or your environment.")
        return

    if not st.session_state.get("financial_report"):
        with st.spinner("Analyzing your finances..."):
            try:
                result = analyze_with_deepseek(profile, api_key)
                st.session_state.financial_report = result
                st.session_state.ai_analysis = result
                st.session_state.financial_report_error = ""
            except Exception as exc:
                st.session_state.financial_report_error = str(exc)
    elif not st.session_state.get("ai_analysis"):
        st.session_state.ai_analysis = st.session_state.financial_report

    if st.session_state.get("financial_report_error") and not st.session_state.get("financial_report"):
        st.error(f"Could not generate report: {st.session_state.financial_report_error}")
        if st.button("Try Again", type="primary"):
            st.session_state.financial_report_error = ""
            st.rerun()
        return

    render_report_dashboard(dashboard_data)

    st.markdown("---")
    st.markdown("### Month-over-Month Comparison")
    previous_profile = st.session_state.get("previous_profile", None)
    if previous_profile:
        try:
            from monthly_comparison import render_comparison

            render_comparison(previous_profile, profile)
        except Exception:
            st.info("Monthly comparison will appear when Kayla's comparison module is available.")
    else:
        st.info("Save this report as a baseline, then come back next month to compare your progress.")

    if st.button("Save as baseline for next month's comparison"):
        st.session_state["previous_profile"] = profile
        st.success("Saved! Come back next month to see your progress.")

    st.markdown("---")
    st.markdown("### Export Report")
    if st.button("Download PDF"):
        try:
            from report_generator import generate_pdf_report

            with st.spinner("Generating PDF..."):
                ai_text = st.session_state.get("ai_analysis", "")
                pdf_bytes = generate_pdf_report(profile, ai_text)
                st.download_button(
                    label="📄 Click here to download",
                    data=pdf_bytes,
                    file_name="financial_report.pdf",
                    mime="application/pdf",
                )
        except Exception:
            st.info("PDF export will be available when Kayla's report generator module is available.")

    st.markdown("---")
    st.markdown("### 📈 Goal Progress Details")
    try:
        from goal_visualization import render_goal_charts

        render_goal_charts(profile)
    except Exception:
        st.info("Complete the questionnaire with financial goals to see goal charts.")


def append_chat_turn(user_message: str, profile: dict[str, Any]) -> None:
    """Call DeepSeek and append one user/assistant exchange."""
    st.session_state.chat_history.append({"role": "user", "content": user_message})
    with st.spinner("Asking your AI financial advisor..."):
        try:
            response = ask_chatbot(user_message, profile, st.session_state.chat_history)
        except Exception as exc:
            response = f"Sorry, I could not answer right now: {exc}"
            st.error(response)
    st.session_state.chat_history.append({"role": "assistant", "content": response})


def render_chat_style() -> None:
    st.markdown(
        """
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@latest/tabler-icons.min.css">
        <style>
        html, body, [class*="css"] {
            font-family: Inter, Sora, -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", sans-serif;
        }
        html, body, .stApp, [data-testid="stAppViewContainer"], .main {
            min-height: 100vh !important;
            overflow: auto !important;
        }
        .stApp { background: #f5f5f7; color: #0f172a; }
        .block-container {
            max-width: 100% !important;
            padding: 0.5rem 30px 20px !important;
        }
        div[data-testid="stVerticalBlock"] { gap: 0.4rem !important; }
        div[data-testid="stVerticalBlock"] > div { gap: 0.4rem !important; }
        div[data-testid="stVerticalBlock"] > div:empty { display: none !important; }
        div[data-testid="element-container"] { margin: 0 !important; }
        h1, h2, h3 { margin: 0.3rem 0 !important; }
        header[data-testid="stHeader"], footer { display: none !important; }
        section[data-testid="stSidebar"] {
            display: block !important;
            height: 100vh !important;
            overflow: hidden !important;
            background: rgba(255,255,255,.96) !important;
            border-right: 1px solid #e5e7eb !important;
            box-shadow: 12px 0 42px rgba(15,23,42,.035);
        }
        section[data-testid="stSidebar"] > div { height: 100vh !important; overflow: hidden !important; padding-top: 14px !important; }
        section[data-testid="stSidebar"] div[role="radiogroup"],
        section[data-testid="stSidebar"] label[data-testid="stWidgetLabel"] { display: none !important; }
        .chat-side-shell { padding: 2px 4px 12px; }
        .chat-side-brand { display:flex; align-items:center; gap:10px; margin:0 0 14px; }
        .chat-side-logo {
            width:36px; height:36px; display:grid; place-items:center; border-radius:11px;
            color:white; background:linear-gradient(135deg,#6366f1,#7c3aed);
            box-shadow:0 12px 26px rgba(99,102,241,.20); font-size:18px; font-weight:900;
        }
        .chat-side-app { color:#111827; font-size:15px; font-weight:850; line-height:1.1; }
        .chat-side-sub { margin-top:2px; color:#94a3b8; font-size:11px; font-weight:650; }
        .chat-side-title { margin: 12px 0 8px; color:#64748b; font-size:11px; font-weight:850; text-transform:uppercase; letter-spacing:.06em; }
        .chat-nav-list { display:grid; gap:6px; }
        .chat-nav-item {
            display:flex; align-items:center; gap:10px; padding:9px 11px; border-radius:12px;
            color:#334155 !important; text-decoration:none !important; border:1px solid transparent;
            background:transparent; font-size:13px;
        }
        .chat-nav-item:hover { background:#f8fafc; border-color:#e5e7eb; }
        .chat-nav-item.active {
            color:#4f46e5 !important; background:#f5f3ff; border-color:#e9d5ff;
            box-shadow:0 12px 28px rgba(99,102,241,.10);
        }
        .chat-nav-item span { width:24px; text-align:center; }
        section[data-testid="stSidebar"] div[data-testid="stButton"] button {
            height:38px !important; margin-top:8px !important; border-radius:12px !important;
            border:1px solid #e5e7eb !important; color:#334155 !important; background:white !important;
            box-shadow:0 10px 24px rgba(15,23,42,.04) !important; font-size:12px !important;
        }
        .chat-shell { min-height: 0; }
        .chat-hero {
            margin: 0 auto 6px;
            text-align: center;
        }
        .chat-title-row {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }
        .chat-hero-icon {
            width: 36px;
            height: 36px;
            display: grid;
            place-items: center;
            border-radius: 13px;
            background: linear-gradient(135deg, #6366f1, #7c3aed);
            box-shadow: 0 14px 30px rgba(99,102,241,.20);
            font-size: 20px;
        }
        .chat-title {
            margin: 0;
            color: #0b1020;
            font-size: 26px;
            line-height: 1.08;
            font-weight: 850;
            letter-spacing: 0;
        }
        .chat-subtitle {
            max-width: 620px;
            margin: 3px auto 0;
            color: #64748b;
            font-size: 13px;
            line-height: 1.35;
            font-weight: 520;
        }
        div[data-testid="stButton"] button {
            border-radius: 12px !important;
            font-weight: 760 !important;
        }
        .chat-summary-bar {
            display:flex;
            align-items:center;
            justify-content:center;
            gap:18px;
            margin: 6px 0 6px;
            padding: 9px 14px;
            border: 1px solid #e5e7eb;
            border-radius: 14px;
            background: rgba(255,255,255,.96);
            box-shadow: 0 10px 28px rgba(15,23,42,.045);
            color:#334155;
            font-size:13px;
            font-weight:760;
            white-space:nowrap;
        }
        .chat-summary-bar strong { color:#0f172a; font-weight:850; }
        .asking-title { margin: 6px 0 3px; color:#111827; font-size:13px; font-weight:850; }
        .chip-row [data-testid="stButton"] button {
            min-height: 40px !important;
            padding: 7px 10px !important;
            border: 1px solid #e5e7eb !important;
            border-radius: 16px !important;
            background: rgba(255,255,255,.94) !important;
            color: #172033 !important;
            box-shadow: 0 14px 34px rgba(15,23,42,.05) !important;
            font-size: 12px !important;
            line-height: 1.25 !important;
            white-space: normal !important;
            text-align: left !important;
        }
        .chip-row [data-testid="stButton"] button:hover {
            border-color: #6366f1 !important;
            background: #ffffff !important;
            color: #4338ca !important;
            box-shadow: 0 18px 42px rgba(99,102,241,.13) !important;
            transform: translateY(-1px);
        }
        .chat-empty-line { text-align:center; color:#86868b; margin:12px 0; font-size:14px; }
        .chat-api-error {
            padding:14px 16px; border:1px solid #fecaca; border-radius:14px; background:#fff7f7;
            color:#991b1b; font-size:14px; line-height:1.5;
        }
        .chat-messages-panel {
            height: clamp(340px, calc(100vh - 410px), 680px);
            min-height: 0;
            overflow-y: auto;
            margin-top: 6px;
            padding: 4px 8px 4px 2px;
            border-radius: 16px;
            scrollbar-width: thin;
        }
        .chat-messages-panel::-webkit-scrollbar { width: 8px; }
        .chat-messages-panel::-webkit-scrollbar-thumb { background: #d1d5db; border-radius: 999px; }
        div[data-testid="stChatMessage"] {
            background: transparent !important;
            padding: 4px 0 !important;
        }
        div[data-testid="stChatMessage"] [data-testid="chatAvatarIcon-user"],
        div[data-testid="stChatMessage"] [data-testid="chatAvatarIcon-assistant"] { display: none !important; }
        .message-row { display: flex; gap: 10px; margin: 7px 0; }
        .message-row.user { justify-content: flex-end; }
        .message-row.assistant { justify-content: flex-start; align-items: flex-start; }
        .chat-assistant-system-icon {
            width: 34px;
            height: 34px;
            flex: 0 0 34px;
            display: grid;
            place-items: center;
            border-radius: 11px;
            color: white;
            background: #f59e0b;
            box-shadow: 0 12px 24px rgba(245,158,11,.20);
            font-size: 17px;
        }
        .user-bubble {
            max-width: min(620px, 74%);
            margin-left: auto;
            padding: 12px 16px;
            border-radius: 16px 16px 4px 16px;
            color: #221044;
            background: linear-gradient(135deg, #f0eaff, #ebe7ff);
            box-shadow: 0 12px 28px rgba(88,72,207,.10);
            font-size: 14px;
            line-height: 1.5;
            font-weight: 620;
            white-space: pre-wrap;
        }
        .assistant-card {
            max-width: min(720px, 82%);
            padding: 13px 16px;
            border: 1px solid #e5e7eb;
            border-radius: 16px;
            background: white;
            box-shadow: 0 14px 34px rgba(15,23,42,.055);
            color: #1f2937;
        }
        .assistant-card p { margin: 0 0 10px; color: #334155; font-size: 14px; line-height: 1.55; }
        .assistant-card p:last-child { margin-bottom: 0; }
        .assistant-card ul, .assistant-card ol { margin: 7px 0 10px 20px; color: #334155; line-height: 1.55; font-size: 14px; }
        .assistant-card strong { color: #0f172a; }
        .message-toolbar {
            display: flex;
            gap: 8px;
            margin: 6px 0 4px 44px;
        }
        .message-toolbar a,
        .message-toolbar button {
            appearance: none;
            border: 1px solid #e5e7eb;
            border-radius: 9px;
            padding: 7px 11px;
            color: #475569 !important;
            background: #ffffff;
            text-decoration: none !important;
            font-size: 12px;
            font-weight: 760;
            cursor: pointer;
        }
        .message-toolbar a:hover,
        .message-toolbar button:hover { color: #4f46e5 !important; border-color: #c7d2fe; background:#f8f7ff; }
        div[data-testid="stForm"] {
            position: static !important;
            width: 100% !important;
            max-width: 100% !important;
            box-sizing: border-box !important;
            z-index: 1000 !important;
            margin: 8px 0 0 !important;
            padding: 8px 10px !important;
            border: 1px solid #e5e7eb !important;
            border-radius: 16px !important;
            background: rgba(255,255,255,.96) !important;
            backdrop-filter: blur(18px) !important;
            box-shadow: 0 18px 46px rgba(15,23,42,.12) !important;
        }
        div[data-testid="stTextInput"] input {
            border: 1px solid #e5e7eb !important;
            border-radius: 14px !important;
            background: white !important;
            box-shadow: 0 14px 34px rgba(15,23,42,.055) !important;
            height: 44px !important;
            padding: 0 14px !important;
            font-size: 15px !important;
        }
        div[data-testid="stFormSubmitButton"] button {
            width: 40px !important; height: 40px !important; border-radius: 11px !important;
            background: linear-gradient(135deg,#6366f1,#7c3aed) !important;
            color: white !important;
            box-shadow: 0 14px 30px rgba(99,102,241,.24) !important;
            border:0 !important;
            font-size:20px !important;
        }
        .chat-helper { margin: 2px 0 0; color:#64748b; font-size:11px; text-align:center; }
        @media (max-width: 900px) {
            html, body, .stApp, [data-testid="stAppViewContainer"], .main { overflow: auto !important; }
            .block-container { height: auto !important; overflow: visible !important; padding: 20px 18px 24px !important; }
            .chat-summary-bar { flex-wrap: wrap; gap: 8px; }
            .assistant-card, .user-bubble { max-width: 92%; }
            div[data-testid="stForm"] {
                width: 100% !important;
                margin-top: 10px !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def get_chat_user_profile() -> dict[str, Any]:
    profile = get_profile()
    return profile if profile_has_data(profile) else {}


def _inline_markdown(text: str) -> str:
    """Render a small, safe subset of inline Markdown."""
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", escaped)
    return escaped


def _is_table_block(lines: list[str]) -> bool:
    return (
        len(lines) >= 2
        and "|" in lines[0]
        and "|" in lines[1]
        and re.fullmatch(r"\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*", lines[1]) is not None
    )


def _render_table(lines: list[str]) -> str:
    rows = [[cell.strip() for cell in line.strip().strip("|").split("|")] for line in lines if "|" in line]
    if len(rows) < 2:
        return "".join(f"<p>{_inline_markdown(line)}</p>" for line in lines)
    header = rows[0]
    body = rows[2:]
    head_html = "".join(f"<th>{_inline_markdown(cell)}</th>" for cell in header)
    body_html = "".join(
        "<tr>" + "".join(f"<td>{_inline_markdown(cell)}</td>" for cell in row) + "</tr>"
        for row in body
    )
    return f"<table><thead><tr>{head_html}</tr></thead><tbody>{body_html}</tbody></table>"


def markdown_to_html(text: str) -> str:
    """Convert common assistant Markdown into safe HTML for custom chat cards."""
    lines = (text or "").splitlines()
    blocks: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        if line.strip().startswith("```"):
            code_lines: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code_lines.append(lines[index])
                index += 1
            index += 1
            blocks.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
            continue
        if line.lstrip().startswith(("- ", "• ")):
            items: list[str] = []
            while index < len(lines) and lines[index].lstrip().startswith(("- ", "• ")):
                items.append(lines[index].lstrip()[2:].strip())
                index += 1
            blocks.append("<ul>" + "".join(f"<li>{_inline_markdown(item)}</li>" for item in items) + "</ul>")
            continue
        if re.match(r"\s*\d+\.\s+", line):
            items = []
            while index < len(lines) and re.match(r"\s*\d+\.\s+", lines[index]):
                items.append(re.sub(r"\s*\d+\.\s+", "", lines[index]).strip())
                index += 1
            blocks.append("<ol>" + "".join(f"<li>{_inline_markdown(item)}</li>" for item in items) + "</ol>")
            continue
        table_lines: list[str] = []
        while index < len(lines) and "|" in lines[index] and lines[index].strip():
            table_lines.append(lines[index])
            index += 1
        if _is_table_block(table_lines):
            blocks.append(_render_table(table_lines))
            continue
        if table_lines:
            blocks.extend(f"<p>{_inline_markdown(table_line)}</p>" for table_line in table_lines)
            continue
        paragraph = [line.strip()]
        index += 1
        while index < len(lines) and lines[index].strip() and not lines[index].lstrip().startswith(("- ", "• ")) and not re.match(r"\s*\d+\.\s+", lines[index]) and not lines[index].strip().startswith("```"):
            if "|" in lines[index]:
                break
            paragraph.append(lines[index].strip())
            index += 1
        blocks.append(f"<p>{_inline_markdown(' '.join(paragraph))}</p>")
    return "".join(blocks) or "<p>I am ready to help.</p>"


def user_message_html(content: str) -> str:
    return compact_html(
        f"""
        <div class="message-row user">
            <div class="user-bubble">{html.escape(content)}</div>
        </div>
        """
    )


def ai_message_html(content: str, index: int | None = None) -> str:
    response_id = f"assistant-response-{index}" if index is not None else "assistant-response-current"
    regenerate_url = f"?page=chat&regenerate={index}" if index is not None else "?page=chat"
    body = content if str(content).startswith('<div class="chat-api-error">') else markdown_to_html(content)
    return compact_html(
        f"""
        <div class="message-row assistant">
            <div class="chat-assistant-system-icon"><i class="ti ti-robot"></i></div>
            <div id="{response_id}" class="assistant-card">{body}</div>
        </div>
        <div class="message-toolbar">
            <a href="?page=chat&feedback=helpful">👍 Helpful</a>
            <a href="?page=chat&feedback=not_helpful">👎 Not Helpful</a>
            <button type="button" onclick="navigator.clipboard && navigator.clipboard.writeText(document.getElementById('{response_id}').innerText)">📋 Copy</button>
            <a href="{regenerate_url}">🔄 Regenerate</a>
        </div>
        """
    )


def render_user_message(content: str) -> None:
    st.markdown(user_message_html(content), unsafe_allow_html=True)


def render_ai_message(content: str, index: int | None = None) -> None:
    st.markdown(
        ai_message_html(content, index),
        unsafe_allow_html=True,
    )


def render_thinking_state(step: str = "Analyzing your financial profile...") -> None:
    st.markdown(
        f"""
        <div class="thinking-card">
            <span>{html.escape(step)}</span>
            <span class="typing-dots"><i></i><i></i><i></i></span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def process_chat_message(user_message: str, user_profile: dict[str, Any]) -> None:
    st.session_state["chat_history"].append({"role": "user", "content": user_message})
    if not user_profile:
        st.session_state["chat_history"].append(
            {
                "role": "assistant",
                "content": "Please complete the questionnaire first so I can give personalized advice.",
            }
        )
        return
    with st.spinner("Analyzing your financial profile..."):
        try:
            response = ask_chatbot(user_message, user_profile, st.session_state["chat_history"])
        except Exception as exc:
            response = f'<div class="chat-api-error"><strong>Sorry, I had trouble analyzing this.</strong><br>{html.escape(str(exc))}</div>'

    st.session_state["chat_history"].append({"role": "assistant", "content": response})


def render_chat_page() -> None:
    """Render a full context-aware chat advisor."""
    render_chat_style()
    user_profile = get_chat_user_profile()
    render_chat_custom_sidebar(user_profile)

    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    regenerate_index = st.query_params.get("regenerate")
    if regenerate_index is not None:
        try:
            idx = int(regenerate_index)
            history = st.session_state["chat_history"]
            if 0 <= idx < len(history) and history[idx].get("role") == "assistant":
                previous_user = next((msg["content"] for msg in reversed(history[:idx]) if msg.get("role") == "user"), "")
                if previous_user:
                    st.session_state["chat_history"] = history[: idx - 1] if idx > 0 else []
                    st.session_state["pending_chat_question"] = previous_user
            st.query_params.clear()
        except (ValueError, IndexError):
            st.query_params.clear()

    header_left, header_center, header_right = st.columns([0.7, 2.6, 0.7], vertical_alignment="top")
    with header_center:
        st.markdown(
            """
            <div class="chat-shell">
            <div class="chat-hero">
                <div class="chat-title-row">
                    <div class="chat-hero-icon">💬</div>
                    <h1 class="chat-title">AI Financial Copilot ✨</h1>
                </div>
                <p class="chat-subtitle">Ask anything about your finances. I already understand your complete financial profile.</p>
            </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    metrics = _chat_profile_metrics(user_profile)
    net_worth = metrics["net_worth"]

    st.markdown(
        f"""
        <div class="chat-summary-bar">
            <span>💰 Income <strong>{money(metrics["income"])}</strong></span>
            <span>💳 Expenses <strong>{money(metrics["expenses"])}</strong></span>
            <span>📈 Savings <strong>{metrics["savings_rate"]:.1f}%</strong></span>
            <span>🏦 Net Worth <strong>{money(net_worth)}</strong></span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    suggested_questions = [
        "Should I buy a $500 gadget?",
        "How much can I spend on dining out?",
        "Am I on track for retirement?",
        "How can I improve my savings rate?",
    ]

    st.markdown('<div class="asking-title">Try asking something...</div>', unsafe_allow_html=True)
    st.markdown('<div class="chip-row">', unsafe_allow_html=True)
    chip_labels = [
        "🛒 $500 gadget?",
        "🍽 Dining budget?",
        "🎯 Retirement track?",
        "📈 Improve savings?",
    ]
    chip_cols = st.columns(4, gap="small")
    for index, (col, question, label) in enumerate(zip(chip_cols, suggested_questions, chip_labels)):
        with col:
            if st.button(label, key=f"chat_chip_{index}", use_container_width=True):
                st.session_state["pending_chat_question"] = question
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    pending_question = st.session_state.pop("pending_chat_question", None)
    if pending_question:
        process_chat_message(pending_question, user_profile)

    history = st.session_state["chat_history"]
    message_parts: list[str] = []
    if history:
        for index, message in enumerate(history):
            role = message.get("role", "assistant")
            content = message.get("content", "")
            if role == "user":
                message_parts.append(user_message_html(content))
            else:
                message_parts.append(ai_message_html(content, index))
    else:
        message_parts.append(
            compact_html(
                """
                <p class="chat-empty-line">💬 Ask me anything to get started.</p>
                """
            )
        )
    st.markdown(f'<div class="chat-messages-panel">{"".join(message_parts)}</div>', unsafe_allow_html=True)

    with st.form("chat_form", clear_on_submit=True):
        input_col, send_col = st.columns([10, 1], gap="small", vertical_alignment="center")
        with input_col:
            user_input = st.text_input(
                "Message",
                placeholder="Ask anything about your finances...",
                label_visibility="collapsed",
            )
        with send_col:
            submitted = st.form_submit_button("↑", use_container_width=True)
        st.markdown('<div class="chat-helper">Press Enter to send • Shift + Enter for new line</div>', unsafe_allow_html=True)

    if submitted and user_input.strip():
        process_chat_message(user_input.strip(), user_profile)
        st.rerun()


def estimate_after_scenario(scenario: str, profile: dict[str, Any]) -> dict[str, Any]:
    """Create a simple before/after estimate for scenario metrics."""
    updated = copy.deepcopy(profile)
    text = scenario.lower()
    income = float(updated.get("total_monthly_income", 0) or 0)
    monthly_income_after_tax = float(updated.get("monthly_income_after_tax", 0) or 0)
    expenses = float(updated.get("total_monthly_expenses", 0) or 0)

    if "lose my job" in text or "lost my job" in text:
        income = float(updated.get("government_subsidies", 0) or 0) + float(updated.get("secondary_income", 0) or 0)
        monthly_income_after_tax = 0.0
    elif "20% salary raise" in text or "20% raise" in text:
        raise_amount = monthly_income_after_tax * 0.20
        monthly_income_after_tax += raise_amount
        income += raise_amount
    elif match := re.search(r"income drops by \$?([\d,]+)", text):
        drop = float(match.group(1).replace(",", ""))
        monthly_income_after_tax = max(monthly_income_after_tax - drop, 0)
        income = max(income - drop, 0)
    elif match := re.search(r"income increases by \$?([\d,]+)", text):
        increase = float(match.group(1).replace(",", ""))
        monthly_income_after_tax += increase
        income += increase

    if "baby" in text:
        expenses += 900
    if "buy a house" in text or "house" in text:
        expenses += 1500

    updated["monthly_income_after_tax"] = monthly_income_after_tax
    updated["total_monthly_income"] = income
    updated["total_monthly_expenses"] = expenses
    updated["monthly_surplus_before_debt_paydown"] = income - expenses
    return updated


def render_metric_comparison(before: dict[str, Any], after: dict[str, Any]) -> None:
    before_metrics = profile_metrics(before)
    after_metrics = profile_metrics(after)
    rows = [
        ("Monthly Income", before_metrics["income"], after_metrics["income"]),
        ("Monthly Expenses", before_metrics["expenses"], after_metrics["expenses"]),
        ("Monthly Surplus", before_metrics["surplus"], after_metrics["surplus"]),
        ("Savings Rate", before_metrics["savings_rate"], after_metrics["savings_rate"]),
    ]

    st.subheader("Before / After Estimate")
    cols = st.columns(4)
    for col, (label, before_value, after_value) in zip(cols, rows):
        if "Rate" in label:
            col.metric(label, f"{after_value:.1f}%", delta=f"{after_value - before_value:.1f} pts")
        else:
            col.metric(label, money(after_value), delta=money(after_value - before_value))


SCENARIO_PRESETS = [
    ("📈", "+20% Salary Raise", "My monthly income increases by 20%"),
    ("💼", "Lose My Job", "I lose my job and have no income for 3 months"),
    ("🏠", "Buy a House", "I take on a mortgage of $2,000/month"),
    ("🚗", "Buy a Car", "I add a car payment of $500/month"),
    ("👶", "Have a Baby", "I have a baby and add $1,500/month in childcare costs"),
    ("🎓", "Go Back to School", "I reduce work to part-time and income drops by 40%"),
]


def render_scenario_style() -> None:
    st.markdown(
        """
        <style>
        #MainMenu, header[data-testid="stHeader"], footer, section[data-testid="stSidebar"] { display: none !important; }
        .block-container { max-width: 1180px !important; padding-top: 28px !important; }
        .stApp { background: #f5f5f7; color: #0f172a; }
        .scenario-hero { display:flex; align-items:center; gap:18px; margin: 10px 0 26px; }
        .scenario-orb { width:58px; height:58px; display:grid; place-items:center; border-radius:999px; background:linear-gradient(135deg,#ede9fe,#ddd6fe); font-size:34px; box-shadow:0 18px 38px rgba(99,102,241,.18); }
        .scenario-title { margin:0; color:#0f172a; font-size:34px; line-height:1.1; font-weight:850; letter-spacing:0; }
        .scenario-subtitle { margin:7px 0 0; color:#64748b; font-size:16px; }
        .scenario-section { margin-bottom:20px; padding:20px; border:1px solid #e5e7eb; border-radius:16px; background:rgba(255,255,255,.96); box-shadow:0 16px 40px rgba(15,23,42,.05); }
        .scenario-section-title { margin:0 0 18px; color:#111827; font-size:18px; font-weight:760; }
        .preset-card { min-height:118px; display:grid; grid-template-columns:58px 1fr; gap:16px; align-items:center; padding:18px; border:1px solid #e5e7eb; border-radius:12px; background:white; text-decoration:none !important; }
        .preset-card:hover { border-color:#6366f1; background:#fafaff; }
        .preset-card.selected { border-color:#6366f1; background:#f5f3ff; box-shadow:0 0 0 1px rgba(99,102,241,.18) inset; }
        .preset-icon { width:52px; height:52px; display:grid; place-items:center; border-radius:14px; background:#f1f5f9; font-size:30px; }
        .preset-title { color:#111827; font-size:16px; font-weight:850; }
        .preset-card.selected .preset-title { color:#4f46e5; }
        .preset-desc { margin-top:7px; color:#475569; font-size:14px; line-height:1.45; }
        div[data-testid="stButton"] button { border-radius:12px !important; font-weight:800 !important; }
        .scenario-section div[data-testid="stButton"] button[kind="primary"] { border:0 !important; color:white !important; background:linear-gradient(135deg,#3b82f6,#7c3aed) !important; }
        .metric-card { overflow:hidden; border:1px solid #dbeafe; border-radius:12px; background:white; }
        .metric-card.after.good { border-color:#86efac; }
        .metric-card.after.bad { border-color:#fca5a5; }
        .metric-head { padding:15px 20px; border-bottom:1px solid #e5e7eb; color:#2563eb; font-size:15px; font-weight:900; letter-spacing:.03em; background:#f8fbff; }
        .metric-head.after { color:#059669; background:#f0fdf4; }
        .metric-row { display:grid; grid-template-columns:34px 1fr auto auto; gap:12px; align-items:center; padding:14px 20px; border-bottom:1px solid #edf2f7; }
        .metric-row:last-child { border-bottom:0; }
        .metric-icon { width:25px; height:25px; display:grid; place-items:center; border-radius:7px; background:#eef2ff; color:#6366f1; font-size:14px; }
        .metric-label { color:#334155; font-size:14px; }
        .metric-value { color:#0f172a; font-size:18px; font-weight:850; text-align:right; }
        .metric-value.positive { color:#16a34a; }
        .metric-change.good { color:#16a34a; font-size:12px; font-weight:800; }
        .metric-change.bad { color:#dc2626; font-size:12px; font-weight:800; }
        .metric-change.neutral { color:#475569; font-size:12px; font-weight:700; }
        .metric-footer { padding:13px 20px; color:#64748b; font-size:12px; }
        .ai-box { padding:20px; border:1px solid #e5e7eb; border-radius:16px; background:linear-gradient(135deg,#ffffff,#fbfbff); }
        .ai-top { display:flex; justify-content:space-between; align-items:center; gap:16px; margin-bottom:20px; }
        .ai-left { display:flex; align-items:center; gap:12px; color:#475569; font-size:14px; }
        .ai-icon { width:38px; height:38px; display:grid; place-items:center; border-radius:12px; background:#f1edff; color:#6d28d9; font-size:22px; }
        .verdict-badge { padding:8px 12px; border-radius:999px; font-size:13px; font-weight:850; }
        .verdict-manageable { color:#15803d; background:#dcfce7; }
        .verdict-challenging { color:#b45309; background:#fef3c7; }
        .verdict-critical { color:#b91c1c; background:#fee2e2; }
        .ai-grid { display:grid; grid-template-columns:1fr 1fr; gap:26px; }
        .ai-grid h4 { margin:0 0 9px; color:#111827; font-size:15px; }
        .ai-grid ul { margin:0 0 18px 18px; color:#334155; font-size:14px; line-height:1.55; }
        .action-row { display:grid; grid-template-columns:28px 1fr; gap:12px; align-items:start; margin:0 0 15px; color:#334155; font-size:14px; }
        .action-num { width:25px; height:25px; display:grid; place-items:center; border-radius:999px; color:#15803d; background:#dcfce7; font-weight:850; }
        .scenario-footer { display:flex; align-items:center; justify-content:space-between; gap:18px; padding:18px 22px; border:1px solid #e5e7eb; border-radius:16px; background:white; color:#475569; }
        .back-report { padding:12px 18px; border:1px solid #e5e7eb; border-radius:10px; color:#111827 !important; text-decoration:none; font-weight:850; background:white; }
        @media (max-width: 900px) { .ai-grid { grid-template-columns:1fr; } .scenario-footer { flex-direction:column; align-items:flex-start; } }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _scenario_metrics(profile: Any) -> dict[str, float]:
    income = float(profile.total_monthly_income)
    expenses = float(profile.total_monthly_expenses)
    savings = income - expenses
    savings_rate = (savings / income * 100) if income else 0.0
    net_worth = float(profile.current_savings - profile.total_debt)
    return {"income": income, "expenses": expenses, "savings": savings, "savings_rate": savings_rate, "net_worth": net_worth}


def _apply_scenario(profile: Any, scenario_text: str) -> dict[str, float]:
    metrics = _scenario_metrics(profile)
    text = scenario_text.lower()
    income = metrics["income"]
    expenses = metrics["expenses"]
    net_worth = metrics["net_worth"]

    if "income increases by 20%" in text or "20% salary" in text or "salary raise" in text:
        income *= 1.2
    if "lose my job" in text:
        income = 0.0
    if match := re.search(r"mortgage of \$?([\d,]+)", text):
        expenses += float(match.group(1).replace(",", ""))
    if match := re.search(r"car payment of \$?([\d,]+)", text):
        expenses += float(match.group(1).replace(",", ""))
    if "childcare" in text:
        match = re.search(r"\$?([\d,]+)\s*/?\s*month[^.]*childcare|childcare[^$]*\$?([\d,]+)", text)
        expenses += float((match.group(1) or match.group(2)).replace(",", "")) if match else 1500.0
    if match := re.search(r"income drops by\s*(\d+(?:\.\d+)?)%", text):
        income *= 1 - (float(match.group(1)) / 100)

    savings = income - expenses
    savings_rate = (savings / income * 100) if income else 0.0
    projected_net_worth = net_worth + (savings * 12)
    return {"income": income, "expenses": expenses, "savings": savings, "savings_rate": savings_rate, "net_worth": projected_net_worth}


def _pct_change(before: float, after: float) -> str:
    if before == 0:
        return "(No baseline)" if after else "(No change)"
    change = (after - before) / abs(before) * 100
    if abs(change) < 0.05:
        return "(No change)"
    return f"({change:+.1f}%)"


def _pp_change(before: float, after: float) -> str:
    change = after - before
    if abs(change) < 0.05:
        return "(No change)"
    return f"({change:+.1f}pp)"


def _parse_ai_scenario_response(text: str) -> dict[str, Any]:
    sections: dict[str, Any] = {
        "VERDICT": "Challenging",
        "IMMEDIATE": [],
        "THREE_MONTH": [],
        "SIX_MONTH": [],
        "ACTION_1": "Review your budget before making changes.",
        "ACTION_2": "Protect your emergency fund.",
        "ACTION_3": "Adjust savings goals based on the new cash flow.",
        "OVERALL": "This scenario changes your financial picture. Review the before and after numbers before committing.",
    }
    current_key = ""
    for raw_line in text.splitlines():
        line = raw_line.strip().lstrip("-•").strip()
        if not line:
            continue
        match = re.match(r"^(VERDICT|IMMEDIATE|THREE_MONTH|SIX_MONTH|ACTION_1|ACTION_2|ACTION_3|OVERALL)\s*:\s*(.*)$", line)
        if match:
            current_key, value = match.groups()
            if current_key in {"IMMEDIATE", "THREE_MONTH", "SIX_MONTH"}:
                sections[current_key] = [value] if value else []
            else:
                sections[current_key] = value
        elif current_key in {"IMMEDIATE", "THREE_MONTH", "SIX_MONTH"}:
            sections[current_key].append(line)
    for key in ("IMMEDIATE", "THREE_MONTH", "SIX_MONTH"):
        sections[key] = sections[key][:2] or ["Review the cash-flow impact.", "Adjust savings targets accordingly."]
    return sections


def _analyze_scenario_with_deepseek(profile: Any, scenario_text: str) -> dict[str, Any]:
    result = run_scenario(scenario_text, profile.to_summary_dict())
    return _parse_ai_scenario_response(result)


def _render_metric_card(title: str, metrics: dict[str, float], footer: str, after: bool, before: dict[str, float] | None = None, improved: bool = True) -> None:
    header_class = "metric-head after" if after else "metric-head"
    card_class = f"metric-card after {'good' if improved else 'bad'}" if after else "metric-card"
    rows = [
        ("💵", "Monthly Income", metrics["income"], _pct_change(before["income"], metrics["income"]) if before else ""),
        ("💳", "Monthly Expenses", metrics["expenses"], _pct_change(before["expenses"], metrics["expenses"]) if before else ""),
        ("💸", "Monthly Savings", metrics["savings"], _pct_change(before["savings"], metrics["savings"]) if before else ""),
        ("⏱️", "Savings Rate", metrics["savings_rate"], _pp_change(before["savings_rate"], metrics["savings_rate"]) if before else ""),
        ("🏦", "Net Worth" + (" (Projected)" if after else ""), metrics["net_worth"], _pct_change(before["net_worth"], metrics["net_worth"]) if before else ""),
    ]
    row_html = []
    for icon, label, value, change in rows:
        is_rate = "Rate" in label
        value_text = f"{value:.1f}%" if is_rate else money(value)
        change_class = "neutral"
        if change.startswith("(+"):
            change_class = "good"
        elif change.startswith("(-"):
            change_class = "bad"
        positive_class = " positive" if label in {"Monthly Savings", "Savings Rate"} and value >= 0 else ""
        row_html.append(
            f'<div class="metric-row"><div class="metric-icon">{icon}</div><div class="metric-label">{label}</div>'
            f'<div class="metric-value{positive_class}">{value_text}</div><div class="metric-change {change_class}">{change}</div></div>'
        )
    st.markdown(
        f"""
        <div class="{card_class}">
            <div class="{header_class}">{title}</div>
            {''.join(row_html)}
            <div class="metric-footer">{footer}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_scenario_page() -> None:
    """Render Apple-style what-if scenario planner."""
    sync_completed_profile()
    # ── Check for user profile ────────────────────────
    raw = st.session_state.get("user_profile", {})

    # Use sample data if no real data exists
    if not raw or not isinstance(raw, dict) or len(raw) < 3:
        st.info("No profile found — using sample data for demo.")
        profile = create_sample_profile()
        using_sample = True
    else:
        try:
            profile = questionnaire_to_profile(raw)
            using_sample = False
        except Exception as e:
            st.warning(f"Could not load profile: {e}. Using sample data.")
            profile = create_sample_profile()
            using_sample = True

    _ = using_sample
    # ── Rest of Scenario Planner UI ───────────────────
    render_scenario_style()
    preset_index = st.query_params.get("scenario_preset")
    if preset_index is not None:
        try:
            _, preset_title, preset_desc = SCENARIO_PRESETS[int(preset_index)]
            st.session_state.selected_scenario = preset_title
            st.session_state.scenario_text = preset_desc
        except (ValueError, IndexError):
            pass

    st.markdown(
        """
        <div class="scenario-hero">
            <div class="scenario-orb">🔮</div>
            <div><h1 class="scenario-title">Scenario Planner</h1><p class="scenario-subtitle">Explore how different life events would impact your finances</p></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="scenario-section"><p class="scenario-section-title">1. Choose a preset scenario</p>', unsafe_allow_html=True)
    for row_start in range(0, len(SCENARIO_PRESETS), 3):
        cols = st.columns(3, gap="large")
        for offset, (col, (emoji, title, desc)) in enumerate(zip(cols, SCENARIO_PRESETS[row_start : row_start + 3])):
            preset_id = row_start + offset
            selected = st.session_state.get("selected_scenario") == title
            with col:
                st.markdown(
                    f"""
                    <a class="preset-card {'selected' if selected else ''}" href="?page=scenarios&scenario_preset={preset_id}">
                        <div class="preset-icon">{emoji}</div>
                        <div><div class="preset-title">{title}</div><div class="preset-desc">{desc}</div></div>
                    </a>
                    """,
                    unsafe_allow_html=True,
                )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="scenario-section"><p class="scenario-section-title">2. Or describe your own scenario...</p>', unsafe_allow_html=True)
    scenario = st.text_area(
        "Scenario description",
        key="scenario_text",
        label_visibility="collapsed",
        placeholder="e.g., I want to take a 6-month sabbatical and travel the world",
        height=110,
    )
    _, button_col = st.columns([3, 1])
    with button_col:
        analyze_clicked = st.button("Analyze This Scenario →", type="primary", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if analyze_clicked:
        if not scenario.strip():
            st.warning("Please choose or describe a scenario first.")
        else:
            before = _scenario_metrics(profile)
            after = _apply_scenario(profile, scenario)
            st.session_state.scenario_before_metrics = before
            st.session_state.scenario_after_metrics = after
            st.session_state.scenario_analyzed_text = scenario
            st.session_state.scenario_analyzed_name = st.session_state.get("selected_scenario", "Custom Scenario")
            with st.spinner("Analyzing scenario..."):
                try:
                    st.session_state.scenario_ai_sections = _analyze_scenario_with_deepseek(profile, scenario)
                except Exception:
                    st.session_state.scenario_ai_sections = _parse_ai_scenario_response("")

    if st.session_state.get("scenario_after_metrics"):
        before = st.session_state.scenario_before_metrics
        after = st.session_state.scenario_after_metrics
        improved = after["savings"] >= before["savings"]
        st.markdown('<div class="scenario-section"><p class="scenario-section-title">3. Scenario Results</p>', unsafe_allow_html=True)
        before_col, after_col = st.columns(2, gap="large")
        with before_col:
            _render_metric_card("BEFORE", before, "Based on your current financial profile", after=False)
        with after_col:
            _render_metric_card(
                "AFTER SCENARIO",
                after,
                f"After applying: {st.session_state.get('scenario_analyzed_name', 'Custom Scenario')}",
                after=True,
                before=before,
                improved=improved,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.get("scenario_ai_sections"):
        sections = st.session_state.scenario_ai_sections
        verdict = str(sections.get("VERDICT", "Challenging")).strip().title()
        verdict_class = "verdict-manageable" if verdict == "Manageable" else "verdict-critical" if verdict == "Critical" else "verdict-challenging"
        verdict_icon = "✅" if verdict == "Manageable" else "🔴" if verdict == "Critical" else "⚠️"
        bullet_html = lambda items: "<ul>" + "".join(f"<li>{item}</li>" for item in items) + "</ul>"
        st.markdown(
            f"""
            <div class="scenario-section">
                <p class="scenario-section-title">4. AI Analysis</p>
                <div class="ai-box">
                    <div class="ai-top">
                        <div class="ai-left"><div class="ai-icon">✦</div><span>Here's how this scenario could impact your financial future:</span></div>
                        <div class="verdict-badge {verdict_class}">Overall Verdict: {verdict_icon} {verdict}</div>
                    </div>
                    <div class="ai-grid">
                        <div>
                            <h4>1. Immediate Impact (Month 1)</h4>{bullet_html(sections["IMMEDIATE"])}
                            <h4>2. 3-Month Outlook</h4>{bullet_html(sections["THREE_MONTH"])}
                            <h4>3. 6-Month Outlook</h4>{bullet_html(sections["SIX_MONTH"])}
                        </div>
                        <div>
                            <h4>4. Top 3 Action Items</h4>
                            <div class="action-row"><div class="action-num">1</div><div>{sections["ACTION_1"]}</div></div>
                            <div class="action-row"><div class="action-num">2</div><div>{sections["ACTION_2"]}</div></div>
                            <div class="action-row"><div class="action-num">3</div><div>{sections["ACTION_3"]}</div></div>
                            <h4 style="margin-top:22px;">5. Overall Verdict</h4>
                            <p style="color:#334155; font-size:14px; line-height:1.55;">{sections["OVERALL"]}</p>
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        """
        <div class="scenario-footer">
            <div>💡 Scenario planning helps you prepare for life's big events. Try different scenarios to build a more resilient financial future.</div>
            <a class="back-report" href="?page=report">← Back to Report</a>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    init_app_state()
    sync_completed_profile()

    if "selected_page" not in st.session_state:
        st.session_state.selected_page = "🏠 Home"

    query_page = st.query_params.get("page")
    route_map = {
        "home": "🏠 Home",
        "questionnaire": "📋 Questionnaire",
        "report": "📊 My Financial Report",
        "analyze": "📊 My Financial Report",
        "chat": "💬 Chat Advisor",
        "scenarios": "🔮 Scenario Planner",
        "scenario": "🔮 Scenario Planner",
    }
    if query_page in route_map:
        st.session_state.selected_page = route_map[query_page]

    if "nav_page" in st.session_state:
        st.session_state.selected_page = st.session_state.pop("nav_page")

    query_step = st.query_params.get("set_step")
    if query_page == "questionnaire" and query_step is not None:
        try:
            st.session_state.questionnaire_step = max(0, min(len(questionnaire.STEPS) - 1, int(query_step)))
            st.query_params.clear()
        except ValueError:
            pass

    if st.session_state.selected_page == "🏠 Home":
        render_global_style()
        render_home()
        return

    if st.session_state.selected_page == "📋 Questionnaire":
        render_questionnaire_page()
        return

    if st.session_state.selected_page == "📊 My Financial Report":
        render_report_page()
        return

    if st.session_state.selected_page == "💬 Chat Advisor":
        render_chat_page()
        return

    page = st.sidebar.radio(
        "Navigation",
        PAGES,
        index=PAGES.index(st.session_state.selected_page),
        key="selected_page",
    )
    if page == "💬 Chat Advisor":
        render_chat_page()
        return

    sidebar_profile = get_profile()
    render_sidebar_summary(sidebar_profile)

    if page == "🏠 Home":
        render_home()
    elif page == "📋 Questionnaire":
        render_questionnaire_page()
    elif page == "📊 My Financial Report":
        render_report_page()
    elif page == "🔮 Scenario Planner":
        render_scenario_page()


if __name__ == "__main__":
    main()
