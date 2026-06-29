"""
Analytics — all visualizations organized into tabs.
Only renders charts when the required capabilities exist.
Never shows empty charts or placeholder boxes.
"""

import streamlit as st
import pandas as pd
import uuid
from core.data_provider import get_provider
from core.capabilities import get_capabilities
from utils.kpis import filter_by_project
from utils import charts


def _chart(fig, label: str = ""):
    """Render a chart only if fig is not None."""
    if fig is None:
        return False

    # Always use a unique key to avoid duplicate element errors
    chart_key = f"{label}_{uuid.uuid4().hex}" if label else f"chart_{uuid.uuid4().hex}"

    st.plotly_chart(
        fig,
        use_container_width=True,
        key=chart_key,
    )
    return True


def _no_data_msg(feature: str):
    st.caption(f"_{feature} data not available in the current dataset._")


def render():
    provider = get_provider()

    st.title("📊 Analytics")
    st.markdown("Deep-dive into QA metrics. All charts update based on the selected project filter.")

    if not provider.is_loaded():
        st.warning("No dataset loaded. Please upload your Excel file in **⚙ Settings**.")
        return

    df_full = provider.get_dataframe()
    caps = get_capabilities(df_full)
    selected = st.session_state.get("selected_project", "All Projects")
    df = filter_by_project(df_full, selected)

    if df.empty:
        st.warning(f"No issues found for project: **{selected}**")
        return

    st.caption(f"Showing **{len(df)}** issues · Scope: **{selected}**")

    # ── Build tabs based on available capabilities ────────────────────────────
    tab_labels = ["Overview"]
    if caps.supports_project and caps.has_multi_project:
        tab_labels.append("Projects")
    if caps.supports_severity:
        tab_labels.append("Severity")
    if caps.supports_phase:
        tab_labels.append("Phase")
    if caps.supports_module:
        tab_labels.append("Modules")
    if caps.supports_created_dates or caps.supports_aging:
        tab_labels.append("Timeline")
    if caps.supports_reporter or caps.supports_assignee:
        tab_labels.append("People")
    if caps.supports_effort:
        tab_labels.append("Effort")

    tabs = st.tabs(tab_labels)
    tab_map = {label: tab for label, tab in zip(tab_labels, tabs)}

    # ── Overview ──────────────────────────────────────────────────────────────
    with tab_map["Overview"]:
        st.subheader("Issue Overview")

        col1, col2 = st.columns(2)
        with col1:
            if caps.supports_status:
                _chart(charts.status_pie(df), "overview_status_pie")
            elif caps.supports_severity:
                _chart(charts.severity_pie(df), "overview_severity_pie")
        with col2:
            if caps.supports_severity:
                _chart(charts.severity_bar(df), "overview_severity_bar")
            elif caps.supports_classification:
                _chart(charts.classification_bar(df), "overview_classification_bar")

        if caps.supports_status:
            st.markdown("#### Status Distribution")
            _chart(charts.status_bar(df), "overview_status_bar")


        if caps.supports_classification:
            st.markdown("#### Classification Breakdown")
            _chart(charts.classification_bar(df), "overview_classification_bar2")


        if not any([caps.supports_status, caps.supports_severity,
                    caps.supports_classification]):
            _no_data_msg("Status, Severity, and Classification")

    # ── Projects ──────────────────────────────────────────────────────────────
    if "Projects" in tab_map:
        with tab_map["Projects"]:
            st.subheader("Project Comparison")

            _chart(charts.project_issue_count(df), "Project Issue Count")

            if caps.supports_status:
                st.markdown("#### Status by Project")
                _chart(charts.status_bar(df, by_project=True))

            if caps.supports_severity:
                st.markdown("#### Severity by Project")
                _chart(charts.severity_bar(df, by_project=True))

            if caps.supports_phase:
                st.markdown("#### Phase by Project")
                _chart(charts.phase_bar(df, by_project=True))

            if caps.supports_severity:
                st.markdown("#### Severity Heat Map")
                _chart(charts.severity_heatmap(df))

            if caps.supports_aging:
                st.markdown("#### Issue Aging by Project")
                _chart(charts.aging_by_project(df))

            if caps.supports_effort:
                st.markdown("#### Effort by Project")
                _chart(charts.effort_by_project(df), "effort_by_project")

    # ── Severity ──────────────────────────────────────────────────────────────
    if "Severity" in tab_map:
        with tab_map["Severity"]:
            st.subheader("Severity Analysis")

            col1, col2 = st.columns(2)
            with col1:
                _chart(charts.severity_pie(df), "severity_pie")
            with col2:
                _chart(charts.severity_bar(df), "severity_bar")

            if caps.has_multi_project:
                st.markdown("#### Severity vs Project")
                _chart(charts.severity_bar(df, by_project=True))
                st.markdown("#### Severity Heat Map")
                _chart(charts.severity_heatmap(df))

            # Severity table
            st.markdown("#### Severity Summary Table")
            sev_data = df["severity"].value_counts().reset_index()
            sev_data.columns = ["Severity", "Count"]
            sev_data["%"] = (sev_data["Count"] / len(df) * 100).round(1).astype(str) + "%"
            st.dataframe(sev_data, use_container_width=True, hide_index=True)

    # ── Phase ─────────────────────────────────────────────────────────────────
    if "Phase" in tab_map:
        with tab_map["Phase"]:
            st.subheader("Phase Distribution")

            col1, col2 = st.columns(2)
            with col1:
                _chart(charts.phase_pie(df), "phase_pie")
            with col2:
                _chart(charts.phase_bar(df), "phase_bar")

            if caps.has_multi_project:
                st.markdown("#### Phase vs Project")
                _chart(charts.phase_bar(df, by_project=True))

            # Phase + Severity cross-tab (if both exist)
            if caps.supports_severity:
                st.markdown("#### Phase × Severity Cross-Tab")
                try:
                    cross = pd.crosstab(df["phase"], df["severity"])
                    st.dataframe(cross, use_container_width=True)
                except Exception:
                    pass

    # ── Modules ───────────────────────────────────────────────────────────────
    if "Modules" in tab_map:
        with tab_map["Modules"]:
            st.subheader("Module Analysis")

            _chart(charts.module_bar(df, top_n=20))

            if caps.supports_severity:
                st.markdown("#### Module × Severity Cross-Tab")
                try:
                    cross = pd.crosstab(df["module"], df["severity"]).head(15)
                    st.dataframe(cross, use_container_width=True)
                except Exception:
                    pass

            st.markdown("#### Module Summary")
            mod_data = df["module"].value_counts().reset_index().head(20)
            mod_data.columns = ["Module", "Count"]
            mod_data["%"] = (mod_data["Count"] / len(df) * 100).round(1).astype(str) + "%"
            st.dataframe(mod_data, use_container_width=True, hide_index=True)

    # ── Timeline ──────────────────────────────────────────────────────────────
    if "Timeline" in tab_map:
        with tab_map["Timeline"]:
            st.subheader("Issue Timeline")

            if caps.supports_created_dates:
                st.markdown("#### Monthly Issue Creation Trend")
                _chart(charts.monthly_trend_line(df), "timeline_monthly_trend")

                if caps.has_multi_project:
                    st.markdown("#### Monthly Trend by Project")
                    _chart(charts.monthly_trend_by_project(df))

            if caps.supports_aging:
                st.markdown("#### Resolution Age Distribution")
                _chart(charts.aging_histogram(df), "timeline_aging_histogram")

                if caps.has_multi_project:
                    st.markdown("#### Aging by Project")
                    _chart(charts.aging_by_project(df))

                # Stats
                sub = df.dropna(subset=["created_time", "closed_time"]).copy()
                sub["age_days"] = (sub["closed_time"] - sub["created_time"]).dt.days
                sub = sub[sub["age_days"] >= 0]
                if not sub.empty:
                    st.markdown("#### Aging Statistics")
                    age_stats = {
                        "Average (days)": round(sub["age_days"].mean(), 1),
                        "Median (days)": round(sub["age_days"].median(), 1),
                        "Max (days)": int(sub["age_days"].max()),
                        "Min (days)": int(sub["age_days"].min()),
                        "Issues with age data": len(sub),
                    }
                    stat_cols = st.columns(len(age_stats))
                    for col, (label, val) in zip(stat_cols, age_stats.items()):
                        col.metric(label, val)

            if not caps.supports_created_dates and not caps.supports_aging:
                _no_data_msg("Date and timeline")

    # ── People ────────────────────────────────────────────────────────────────
    if "People" in tab_map:
        with tab_map["People"]:
            st.subheader("Team Analysis")

            if caps.supports_assignee:
                st.markdown("#### Assignee Workload")
                _chart(charts.assignee_workload(df, top_n=20), "assignee_workload")

                # Assignee + severity breakdown
                if caps.supports_severity:
                    st.markdown("#### Assignee × Severity")
                    try:
                        cross = pd.crosstab(df["assignee"], df["severity"]).head(15)
                        st.dataframe(cross, use_container_width=True)
                    except Exception:
                        pass

            if caps.supports_reporter:
                st.markdown("#### Reporter Analysis")
                _chart(charts.reporter_bar(df, top_n=15), "reporter_bar")

    # ── Effort ────────────────────────────────────────────────────────────────
    if "Effort" in tab_map:
        with tab_map["Effort"]:
            st.subheader("Effort & Hours Analysis")

            col1, col2 = st.columns(2)
            with col1:
                _chart(charts.effort_by_project(df), "effort_by_project")
            with col2:
                _chart(charts.billable_vs_nonbillable(df), "billable_nonbillable")

            # Hours summary
            st.markdown("#### Hours Summary")
            effort_rows = {}
            if "total_log_hours" in df.columns:
                effort_rows["Total Log Hours"] = round(pd.to_numeric(df["total_log_hours"], errors="coerce").sum(), 1)
            if "billable_hours" in df.columns:
                effort_rows["Billable Hours"] = round(pd.to_numeric(df["billable_hours"], errors="coerce").sum(), 1)
            if "non_billable_hours" in df.columns:
                effort_rows["Non-Billable Hours"] = round(pd.to_numeric(df["non_billable_hours"], errors="coerce").sum(), 1)

            if effort_rows:
                effort_cols = st.columns(len(effort_rows))
                for col, (label, val) in zip(effort_cols, effort_rows.items()):
                    col.metric(label, val)