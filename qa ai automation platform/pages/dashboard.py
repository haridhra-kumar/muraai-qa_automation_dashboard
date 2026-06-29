"""
Dashboard — executive overview. Not the analytics page.
KPIs, data source info, recent AI summary, quick actions.
"""

import streamlit as st
import pandas as pd
from core.data_provider import get_provider
from core.capabilities import get_capabilities
from core.context_builder import build_kpi_summary
from utils.kpis import (
    filter_by_project, open_issue_count, closed_issue_count,
    critical_issue_count, high_issue_count, avg_resolution_days,
    escalated_count, total_log_hours, closure_rate,
)
from utils.charts import status_pie, severity_pie, monthly_trend_line


def _kpi_row(df: pd.DataFrame, caps, col_count: int = 4):
    """Render the KPI metric cards."""
    kpis = build_kpi_summary(df, caps)
    total = kpis.get("total_issues", 0)

    metrics = [("Total Issues", total, None)]

    if caps.supports_status:
        open_c  = open_issue_count(df)
        close_c = closed_issue_count(df)
        rate    = closure_rate(df)
        metrics.append(("Open Issues", open_c, None))
        metrics.append(("Closed Issues", close_c, None))
        metrics.append(("Closure Rate", f"{rate}%", None))

    if caps.supports_severity:
        crit = critical_issue_count(df)
        high = high_issue_count(df)
        metrics.append(("Critical Issues", crit, "inverse" if crit > 0 else "normal"))
        metrics.append(("High Severity", high, "inverse" if high > 0 else "normal"))

    if caps.supports_aging:
        avg_days = avg_resolution_days(df)
        if avg_days is not None:
            metrics.append(("Avg Resolution (days)", avg_days, None))

    if caps.supports_escalation:
        esc = escalated_count(df)
        metrics.append(("Escalated Issues", esc, "inverse" if esc > 0 else "normal"))

    if caps.supports_effort:
        hrs = total_log_hours(df)
        metrics.append(("Total Log Hours", hrs, None))

    if caps.supports_project:
        metrics.append(("Projects", caps.project_count, None))

    # Render in rows of col_count
    for i in range(0, len(metrics), col_count):
        chunk = metrics[i:i+col_count]
        cols = st.columns(len(chunk))
        for col, (label, value, delta_color) in zip(cols, chunk):
            with col:
                st.metric(label=label, value=value)


def render():
    provider = get_provider()

    st.title("🏠 QA Dashboard")
    st.markdown("Executive overview of QA health across all tracked projects.")

    # ── No data state ─────────────────────────────────────────────────────────
    if not provider.is_loaded():
        st.warning("No dataset loaded. Please upload your Excel file in **⚙ Settings**.")
        if st.button("Go to Settings"):
            st.session_state["_page_override"] = "⚙ Settings"
            st.rerun()
        return

    df_full = provider.get_dataframe()
    caps = get_capabilities(df_full)
    selected = st.session_state.get("selected_project", "All Projects")
    df = filter_by_project(df_full, selected)

    if df.empty:
        st.warning(f"No issues found for project: **{selected}**")
        return

    # ── Data source info bar ─────────────────────────────────────────────────
    col_info1, col_info2, col_info3, col_info4 = st.columns([2, 2, 2, 1])
    with col_info1:
        st.caption(f"**Data Source:** {provider.source_label}")
    with col_info2:
        st.caption(f"**Last Refresh:** {provider.loaded_at.strftime('%d %b %Y, %H:%M') if provider.loaded_at else '—'}")
    with col_info3:
        st.caption(f"**Scope:** {selected}")
    with col_info4:
        if st.button("🔄 Refresh", use_container_width=True):
            from core.data_provider import try_autoload
            from core.capabilities import invalidate_capabilities, build_capabilities
            invalidate_capabilities()
            provider_new = get_provider()
            if provider_new.raw_filename and provider_new.raw_filename != "latest_qa.xlsx":
                st.info("Re-upload the file in Settings to refresh.")
            else:
                try_autoload("data/latest_qa.xlsx")
                if provider_new.is_loaded():
                    st.session_state.capabilities = build_capabilities(provider_new.get_dataframe())
            st.rerun()

    st.markdown("---")

    # ── KPI Cards ────────────────────────────────────────────────────────────
    st.subheader("Key Metrics")
    _kpi_row(df, caps)

    st.markdown("---")

    # ── Summary visualization (one small chart) ───────────────────────────────
    left_col, right_col = st.columns([1, 1])

    with left_col:
        st.subheader("Status at a Glance")
        fig = status_pie(df) if caps.supports_status else None
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        elif caps.supports_severity:
            fig2 = severity_pie(df)
            if fig2:
                st.plotly_chart(fig2, use_container_width=True)
        else:
            # Fallback: show project distribution if multi-project
            if caps.supports_project and caps.has_multi_project:
                from utils.charts import project_issue_count
                fig3 = project_issue_count(df)
                if fig3:
                    st.plotly_chart(fig3, use_container_width=True)

    with right_col:
        st.subheader("Issue Trend")
        fig_trend = monthly_trend_line(df) if caps.supports_created_dates else None
        if fig_trend:
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("No date information available for trend analysis.")

    st.markdown("---")

    # ── AI Executive Summary ─────────────────────────────────────────────────
    st.subheader("🤖 AI Executive Summary")

    if "dashboard_ai_summary" not in st.session_state:
        st.session_state.dashboard_ai_summary = None

    if st.button("Generate AI Executive Summary", type="primary"):
        import os
        from groq import Groq
        from core.context_builder import build_ai_context

        api_key = os.getenv("GROQ_API_KEY", "")
        if not api_key or api_key == "your_groq_api_key_here":
            st.error("Groq API key not configured. Add it to your .env file.")
        else:
            with st.spinner("Generating executive summary..."):
                try:
                    context = build_ai_context(df, caps, selected)
                    client = Groq(api_key=api_key)
                    response = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {
                                "role": "system",
                                "content": (
                                    "You are a senior QA analyst presenting to company management. "
                                    "Write a concise executive summary (3-5 sentences) covering: "
                                    "overall quality health, key risks, top issues, and one recommendation. "
                                    "Be direct, data-driven, and professional. No fluff."
                                ),
                            },
                            {
                                "role": "user",
                                "content": f"Generate an executive summary from this QA data:\n\n{context}",
                            },
                        ],
                        max_tokens=400,
                        temperature=0.4,
                    )
                    st.session_state.dashboard_ai_summary = response.choices[0].message.content
                except Exception as e:
                    st.error(f"Error generating summary: {e}")

    if st.session_state.dashboard_ai_summary:
        st.info(st.session_state.dashboard_ai_summary)