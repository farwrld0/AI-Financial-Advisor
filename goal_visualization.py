"""
goal_visualization.py
AI Personal Finance Agent — IST 495 SU26
Author: Ruohan (Kayla) Mei
Week 7 — Task 4.4: Goal Progress Visualization

Generates plotly charts for goal progress.
Ken calls these functions inside the Streamlit Report page.

Usage:
    from goal_visualization import render_goal_charts
    render_goal_charts(profile)
"""

from goal_planner import analyze_all_goals, goal_summary, GoalStatus
from questionnaire_schema_v3 import UserFinancialProfile


# ── Color palette ─────────────────────────────────────────
COLOR_ON_TRACK      = "#2ECC71"   # green
COLOR_NEEDS_ADJUST  = "#F39C12"   # orange
COLOR_AT_RISK       = "#E74C3C"   # red
COLOR_REMAINING     = "#ECF0F1"   # light grey (unfilled portion)
COLOR_SAVINGS       = "#3498DB"   # blue (savings bar)
COLOR_NEEDED        = "#E67E22"   # dark orange (needed bar)
BG_COLOR            = "rgba(0,0,0,0)"  # transparent background


def _status_color(status: str) -> str:
    if "On Track" in status:
        return COLOR_ON_TRACK
    if "Needs" in status:
        return COLOR_NEEDS_ADJUST
    return COLOR_AT_RISK


def chart_goal_progress_bars(statuses: list[GoalStatus]) -> "go.Figure":
    """
    Horizontal stacked bar chart showing % saved vs % remaining for each goal.
    Each bar is color-coded by status (green / orange / red).
    """
    import plotly.graph_objects as go

    labels   = [s.goal.description for s in statuses]
    saved    = [s.progress_pct for s in statuses]
    remaining = [max(0.0, 100.0 - s.progress_pct) for s in statuses]
    colors   = [_status_color(s.status) for s in statuses]
    hover_saved = [
        f"<b>{s.goal.description}</b><br>"
        f"Saved: {s.progress_pct:.1f}%<br>"
        f"Status: {s.status}<br>"
        f"Monthly needed: ${s.monthly_needed:,.0f}<br>"
        f"Monthly allocated: ${s.monthly_available:,.0f}"
        for s in statuses
    ]

    fig = go.Figure()

    # Saved portion
    fig.add_trace(go.Bar(
        name="Saved",
        y=labels,
        x=saved,
        orientation="h",
        marker_color=colors,
        hovertext=hover_saved,
        hoverinfo="text",
        text=[f"{p:.0f}%" for p in saved],
        textposition="inside",
        insidetextanchor="middle",
    ))

    # Remaining portion
    fig.add_trace(go.Bar(
        name="Remaining",
        y=labels,
        x=remaining,
        orientation="h",
        marker_color=COLOR_REMAINING,
        hoverinfo="skip",
        showlegend=False,
    ))

    fig.update_layout(
        barmode="stack",
        title="Goal Progress",
        xaxis=dict(title="% Toward Goal", range=[0, 100], ticksuffix="%"),
        yaxis=dict(title="", automargin=True),
        plot_bgcolor=BG_COLOR,
        paper_bgcolor=BG_COLOR,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=50, b=20),
        height=max(250, len(statuses) * 80),
    )
    return fig


def chart_monthly_savings_vs_needed(
    statuses: list[GoalStatus],
    net_monthly_savings: float,
) -> "go.Figure":
    """
    Grouped bar chart comparing monthly savings allocated vs monthly savings needed
    per goal, with a horizontal line showing total net savings.
    """
    import plotly.graph_objects as go

    labels  = [s.goal.description for s in statuses]
    needed  = [s.monthly_needed for s in statuses]
    avail   = [s.monthly_available for s in statuses]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        name="Monthly Needed",
        x=labels,
        y=needed,
        marker_color=COLOR_NEEDED,
        text=[f"${v:,.0f}" for v in needed],
        textposition="outside",
    ))

    fig.add_trace(go.Bar(
        name="Monthly Allocated",
        x=labels,
        y=avail,
        marker_color=COLOR_SAVINGS,
        text=[f"${v:,.0f}" for v in avail],
        textposition="outside",
    ))

    # Horizontal line: total net savings
    fig.add_hline(
        y=net_monthly_savings,
        line_dash="dash",
        line_color="#2C3E50",
        annotation_text=f"Total savings: ${net_monthly_savings:,.0f}/mo",
        annotation_position="top right",
    )

    fig.update_layout(
        barmode="group",
        title="Monthly Savings: Needed vs. Allocated per Goal",
        xaxis=dict(title=""),
        yaxis=dict(title="$ / month", tickprefix="$"),
        plot_bgcolor=BG_COLOR,
        paper_bgcolor=BG_COLOR,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=60, b=20),
        height=350,
    )
    return fig


def chart_goal_timeline(statuses: list[GoalStatus]) -> "go.Figure":
    """
    Gantt-style timeline showing each goal's target completion date
    and estimated actual completion at current savings rate.
    """
    import plotly.graph_objects as go
    from datetime import datetime, timedelta

    today = datetime.today()
    fig = go.Figure()

    for i, s in enumerate(statuses):
        target_months  = s.goal.timeline_years * 12
        target_date    = today + timedelta(days=target_months * 30.44)
        eta_months     = s.months_to_goal
        eta_date       = (today + timedelta(days=eta_months * 30.44)
                          if eta_months is not None else None)
        color = _status_color(s.status)

        # Target bar (planned)
        fig.add_trace(go.Bar(
            name="Target date" if i == 0 else None,
            x=[target_months],
            y=[s.goal.description],
            orientation="h",
            marker_color=color,
            opacity=0.4,
            showlegend=(i == 0),
            hovertext=f"Target: {target_date.strftime('%b %Y')}",
            hoverinfo="text",
        ))

        # ETA bar (actual at current rate)
        if eta_months is not None:
            fig.add_trace(go.Bar(
                name="ETA at current rate" if i == 0 else None,
                x=[eta_months],
                y=[s.goal.description],
                orientation="h",
                marker_color=color,
                showlegend=(i == 0),
                hovertext=(
                    f"ETA: {eta_date.strftime('%b %Y')}"
                    if eta_date else "Not funded"
                ),
                hoverinfo="text",
            ))

    fig.update_layout(
        barmode="overlay",
        title="Goal Timeline — Planned vs. Estimated Completion",
        xaxis=dict(title="Months from today", ticksuffix=" mo"),
        yaxis=dict(title="", automargin=True),
        plot_bgcolor=BG_COLOR,
        paper_bgcolor=BG_COLOR,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=60, b=20),
        height=max(250, len(statuses) * 80),
    )
    return fig


# ── Main Streamlit render function ────────────────────────

def render_goal_charts(profile: UserFinancialProfile):
    """
    Render all three goal charts in Streamlit.
    Ken calls this in the Report page:

        from goal_visualization import render_goal_charts
        render_goal_charts(profile)
    """
    try:
        import streamlit as st
        import plotly.graph_objects as go
    except ImportError:
        print("Streamlit / plotly not available. Run inside Streamlit.")
        return

    statuses = analyze_all_goals(profile)
    if not statuses:
        st.info("No financial goals to display.")
        return

    summary = goal_summary(profile)
    net = summary["net_monthly_savings"]

    # ── Summary metrics row ───────────────────────────────
    cols = st.columns(3)
    cols[0].metric("Net Monthly Savings",  f"${net:,.0f}")
    cols[1].metric("Total Needed/Month",   f"${summary['total_monthly_needed_for_all_goals']:,.0f}")
    gap = summary["monthly_gap"]
    cols[2].metric(
        "Monthly Gap",
        f"${gap:,.0f}",
        delta=f"-${gap:,.0f}" if gap > 0 else "Fully funded",
        delta_color="inverse" if gap > 0 else "normal",
    )

    st.markdown("---")

    # ── Chart 1: Progress bars ────────────────────────────
    st.plotly_chart(
        chart_goal_progress_bars(statuses),
        use_container_width=True,
        key="goal_progress_bars",
    )

    # ── Chart 2: Monthly savings comparison ──────────────
    st.plotly_chart(
        chart_monthly_savings_vs_needed(statuses, net),
        use_container_width=True,
        key="goal_savings_comparison",
    )

    # ── Chart 3: Timeline ─────────────────────────────────
    st.plotly_chart(
        chart_goal_timeline(statuses),
        use_container_width=True,
        key="goal_timeline",
    )


# ── Test (no Streamlit) ───────────────────────────────────

if __name__ == "__main__":
    from questionnaire_schema_v3 import create_sample_profile

    profile  = create_sample_profile()
    statuses = analyze_all_goals(profile)
    summary  = goal_summary(profile)

    print("=== Goal Visualization Test ===")
    print(f"Goals: {len(statuses)}")
    print(f"Overall: {summary['overall_status']}")
    print()
    for s in statuses:
        print(f"  {s.goal.description}")
        print(f"    Progress bar: {s.progress_pct:.1f}% filled, color={_status_color(s.status)}")
        print(f"    Monthly bar:  needed=${s.monthly_needed:.0f}, allocated=${s.monthly_available:.0f}")
        eta = f"{s.months_to_goal:.1f} months" if s.months_to_goal else "unfunded"
        print(f"    Timeline ETA: {eta}")
        print()

    print("All chart data computed successfully.")
    print("Run inside Streamlit to see the actual charts.")
    print("\nKen: add this to report.py:")
    print("  from goal_visualization import render_goal_charts")
    print("  render_goal_charts(profile)")
