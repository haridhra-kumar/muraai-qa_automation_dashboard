"""
Weekly Reports — generates professional consulting-style QA reports.
Sections are dynamically included based on dataset capabilities.
Supports PDF and Markdown export.
"""

import streamlit as st
import pandas as pd
import io
from datetime import datetime, timedelta, date
from core.data_provider import get_provider
from core.capabilities import get_capabilities
from utils.kpis import (
    filter_by_project, open_issue_count, closed_issue_count,
    critical_issue_count, high_issue_count, avg_resolution_days,
    closure_rate, total_log_hours, top_n_values,
)
from utils.charts import (
    status_pie, severity_pie, phase_pie, module_bar, monthly_trend_line,
    assignee_workload, reporter_bar, resolution_bar, aging_histogram,
    effort_by_project, project_issue_count, severity_heatmap,
)


def _safe_pdf_import():
    try:
        from utils.pdf_export import generate_pdf_report
        return generate_pdf_report
    except Exception:
        return None


def _chart(fig):
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)


def _build_report_sections(df: pd.DataFrame, caps) -> list[dict]:
    total = len(df)
    sections = []

    # Executive Summary
    exec_parts = [f"This report covers **{total}** QA issues"]
    if caps.supports_project:
        exec_parts.append(f"across {caps.project_count} project(s)")
    if caps.supports_status:
        open_c  = open_issue_count(df)
        close_c = closed_issue_count(df)
        rate    = closure_rate(df)
        exec_parts.append(f"with {open_c} open and {close_c} closed issues (closure rate: {rate}%)")
    if caps.supports_severity:
        crit = critical_issue_count(df)
        high = high_issue_count(df)
        exec_parts.append(f"including {crit} critical and {high} high-severity defects requiring immediate attention")

    sections.append({
        "heading": "Executive Summary",
        "summary": ". ".join(exec_parts) + ".",
        "table_rows": None,
        "interpretation": (
            "The figures above represent the current state of QA across all tracked work. "
            "Particular attention should be paid to open critical/high issues as they "
            "directly impact release readiness."
            if caps.supports_severity else
            "Review open issues to assess release readiness."
        ),
        "recommendations": (
            "Prioritise resolution of critical and high-severity issues before the next release. "
            "Establish a daily triage for any new critical defects."
            if caps.supports_severity else
            "Review and prioritise open issues based on business impact."
        ),
    })

    # Project Comparison
    if caps.supports_project and caps.has_multi_project:
        proj_counts = df["project_name"].value_counts().reset_index()
        proj_counts.columns = ["Project", "Issue Count"]
        proj_counts["% of Total"] = (proj_counts["Issue Count"] / total * 100).round(1).astype(str) + "%"
        if caps.supports_status:
            open_per_proj = df[df["status"].isin(
                ["Open", "In Progress", "Reopened", "To Do", "In Review", "Active"]
            )]["project_name"].value_counts()
            proj_counts["Open Issues"] = proj_counts["Project"].map(open_per_proj).fillna(0).astype(int)
        sections.append({
            "heading": "Project Comparison",
            "summary": f"Issue distribution across {caps.project_count} active projects.",
            "table_rows": proj_counts.to_dict("records"),
            "interpretation": "Projects with a high proportion of open or critical issues represent the greatest delivery risk.",
            "recommendations": "Allocate additional QA resources to the project with the highest open critical issue count.",
        })

    # Status Analysis
    if caps.supports_status:
        status_counts = df["status"].value_counts().reset_index()
        status_counts.columns = ["Status", "Count"]
        status_counts["% of Total"] = (status_counts["Count"] / total * 100).round(1).astype(str) + "%"
        sections.append({
            "heading": "Issue Status Analysis",
            "summary": f"Closure rate is {closure_rate(df)}%. {open_issue_count(df)} issues remain open.",
            "table_rows": status_counts.to_dict("records"),
            "interpretation": "A high proportion of 'Open' or 'In Progress' issues signals a QA bottleneck.",
            "recommendations": "Investigate stale open issues older than 7 days and assign clear owners for resolution.",
        })

    # Severity Analysis
    if caps.supports_severity:
        sev_counts = df["severity"].value_counts().reset_index()
        sev_counts.columns = ["Severity", "Count"]
        sev_counts["% of Total"] = (sev_counts["Count"] / total * 100).round(1).astype(str) + "%"
        crit = critical_issue_count(df)
        high = high_issue_count(df)
        pct = round((crit + high) / total * 100, 1) if total > 0 else 0
        sections.append({
            "heading": "Severity Analysis",
            "summary": f"{crit} critical and {high} high-severity issues identified ({pct}% of total).",
            "table_rows": sev_counts.to_dict("records"),
            "interpretation": "Critical and High issues directly impact release quality and customer experience.",
            "recommendations": "All Critical issues should be resolved or mitigated before any production deployment.",
        })

    # Phase Analysis (only if phase column exists)
    if caps.supports_phase:
        phase_counts = df["phase"].value_counts().reset_index()
        phase_counts.columns = ["Phase", "Count"]
        phase_counts["% of Total"] = (phase_counts["Count"] / total * 100).round(1).astype(str) + "%"
        sections.append({
            "heading": "Phase Analysis",
            "summary": "Issue distribution across testing phases (SIT, UAT, PROD, DEV etc.).",
            "table_rows": phase_counts.to_dict("records"),
            "interpretation": "Issues found in PROD are significantly more expensive to fix than those found in SIT/UAT.",
            "recommendations": "Shift testing left — improve SIT coverage to catch more defects before UAT and PROD.",
        })

    # Module Analysis
    if caps.supports_module:
        mod_counts = df["module"].value_counts().head(10).reset_index()
        mod_counts.columns = ["Module", "Count"]
        top_module = mod_counts.iloc[0]["Module"] if not mod_counts.empty else "N/A"
        sections.append({
            "heading": "Module Analysis",
            "summary": f"Top 10 modules by issue count. '{top_module}' has the highest defect density.",
            "table_rows": mod_counts.to_dict("records"),
            "interpretation": "Modules with consistently high issue counts may have structural code or specification problems.",
            "recommendations": f"Schedule a targeted code review for the '{top_module}' module.",
        })

    # Resolution Analysis
    if caps.supports_resolution:
        # Truncate long resolution text
        res_series = df["resolution"].astype(str).str.slice(0, 50)
        res_counts = res_series.value_counts().head(15).reset_index()
        res_counts.columns = ["Resolution", "Count"]
        sections.append({
            "heading": "Resolution Analysis",
            "summary": "Breakdown of how issues were resolved or closed.",
            "table_rows": res_counts.to_dict("records"),
            "interpretation": "A high number of 'Won't Fix' or 'Invalid' resolutions may indicate unclear requirements.",
            "recommendations": "Review 'Won't Fix' issues with product owners to ensure they are correctly prioritised.",
        })

    # Issue Aging
    if caps.supports_aging:
        avg_days = avg_resolution_days(df)
        sub = df.dropna(subset=["created_time", "closed_time"]).copy()
        sub["age_days"] = (sub["closed_time"] - sub["created_time"]).dt.days
        sub = sub[sub["age_days"] >= 0]
        age_summary = []
        if not sub.empty:
            age_summary = [
                {"Metric": "Average Resolution Time", "Value": f"{sub['age_days'].mean():.1f} days"},
                {"Metric": "Median Resolution Time",  "Value": f"{sub['age_days'].median():.1f} days"},
                {"Metric": "Fastest Resolution",      "Value": f"{sub['age_days'].min():.0f} days"},
                {"Metric": "Slowest Resolution",      "Value": f"{sub['age_days'].max():.0f} days"},
                {"Metric": "Issues with Age Data",    "Value": str(len(sub))},
            ]
        sections.append({
            "heading": "Issue Aging",
            "summary": f"Average resolution time is {avg_days} days." if avg_days else "Aging data available.",
            "table_rows": age_summary if age_summary else None,
            "interpretation": "Long resolution times signal resourcing gaps or overly complex issues.",
            "recommendations": "Set SLA targets per severity and track breaches weekly.",
        })

    # People
    if caps.supports_reporter:
        rep_counts = df["reporter"].value_counts().head(10).reset_index()
        rep_counts.columns = ["Reporter", "Issues Reported"]
        sections.append({
            "heading": "Reporter Analysis",
            "summary": "Top 10 issue reporters by volume.",
            "table_rows": rep_counts.to_dict("records"),
            "interpretation": "High-volume reporters often indicate active testing areas or recurring defect hotspots.",
            "recommendations": "Recognise high-contributing testers and leverage their knowledge in targeted reviews.",
        })

    if caps.supports_assignee:
        asgn_counts = df["assignee"].value_counts().head(10).reset_index()
        asgn_counts.columns = ["Assignee", "Issues Assigned"]
        sections.append({
            "heading": "Assignee Analysis",
            "summary": "Top 10 assignees by issue count (workload indicator).",
            "table_rows": asgn_counts.to_dict("records"),
            "interpretation": "Uneven workload distribution can lead to burnout and quality risk.",
            "recommendations": "Review assignee load and rebalance if any single developer holds more than 30% of open issues.",
        })

    # Monthly Trend
    if caps.supports_created_dates:
        sub = df.dropna(subset=["created_time"]).copy()
        sub["month"] = sub["created_time"].dt.to_period("M").astype(str)
        monthly = sub["month"].value_counts().sort_index().tail(6).reset_index()
        monthly.columns = ["Month", "Issues Created"]
        sections.append({
            "heading": "Monthly Issue Trend",
            "summary": "Issue creation volume over the last 6 months.",
            "table_rows": monthly.to_dict("records"),
            "interpretation": "Spikes in issue creation may correlate with major feature releases or regression events.",
            "recommendations": "Correlate issue spikes with release events to identify systemic quality problems.",
        })

    # Effort
    if caps.supports_effort:
        effort_rows = []
        if "total_log_hours" in df.columns and caps.supports_project:
            from utils.kpis import _parse_hours
            df2 = df.copy()
            df2["_hours_float"] = _parse_hours(df2["total_log_hours"])
            effort_by_proj = df2.groupby("project_name")["_hours_float"].sum().reset_index()
            effort_by_proj.columns = ["Project", "Total Log Hours"]
            effort_by_proj["Total Log Hours"] = effort_by_proj["Total Log Hours"].round(1)
            effort_rows = effort_by_proj.to_dict("records")
        sections.append({
            "heading": "Effort Analysis",
            "summary": f"Total logged hours: {total_log_hours(df)}.",
            "table_rows": effort_rows if effort_rows else None,
            "interpretation": "High non-billable hours may indicate rework or inefficiency.",
            "recommendations": "Track billable-to-non-billable ratio and aim to reduce rework through better requirements.",
        })

    # Top Risks
    risks = []
    if caps.supports_severity and critical_issue_count(df) > 0:
        risks.append({"Risk": "Critical Issues Open", "Details": f"{critical_issue_count(df)} critical issues unresolved"})
    if caps.supports_aging:
        avg_d = avg_resolution_days(df)
        if avg_d and avg_d > 10:
            risks.append({"Risk": "High Avg Resolution Time", "Details": f"{avg_d} days average — exceeds recommended SLA"})
    if risks:
        sections.append({
            "heading": "Top Risks",
            "summary": "Key risk items requiring management attention.",
            "table_rows": risks,
            "interpretation": "These risks have the highest potential to impact release timelines or product quality.",
            "recommendations": "Assign a risk owner to each item and review status in the next management meeting.",
        })

    return sections


def render():
    provider = get_provider()
    st.title("📄 Weekly Reports")
    st.markdown("Generate a professional QA executive report. Sections adapt automatically to your dataset.")

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

    # ── Week selector ─────────────────────────────────────────────────────────
    st.markdown("#### Report Period")

    # Default: last full Mon–Sun week
    today = date.today()
    last_monday = today - timedelta(days=today.weekday() + 7)
    last_sunday = last_monday + timedelta(days=6)

    col_w1, col_w2, col_w3 = st.columns([2, 2, 2])
    with col_w1:
        week_start = st.date_input("Week start (Monday)", value=last_monday)
    with col_w2:
        week_end = st.date_input("Week end (Sunday)", value=last_sunday)
    with col_w3:
        st.markdown("<br>", unsafe_allow_html=True)
        use_week_filter = st.checkbox("Filter data to this week", value=False,
            help="When checked, only issues created/updated within the selected week are included. "
                 "Uncheck to report on the full dataset.")

    if use_week_filter and caps.supports_created_dates:
        df = df[
            df["created_time"].dt.date.between(week_start, week_end)
        ]
        if df.empty:
            st.warning(f"No issues found between {week_start} and {week_end}. Uncheck the filter or pick a different week.")
            return
        st.caption(f"📅 Filtered to **{len(df)}** issues created between **{week_start}** and **{week_end}**.")
    elif use_week_filter and not caps.supports_created_dates:
        st.warning("Date filtering is unavailable — this dataset has no created-date column.")

    week_label = f"{week_start.strftime('%d %b')} – {week_end.strftime('%d %b %Y')}"

    st.markdown("---")

    # Controls
    generate = st.button("📄 Generate Report", type="primary", use_container_width=False)

    if "report_sections" not in st.session_state:
        st.session_state.report_sections = None
    if "report_pdf_bytes" not in st.session_state:
        st.session_state.report_pdf_bytes = None

    if generate:
        with st.spinner("Building report..."):
            st.session_state.report_sections = _build_report_sections(df, caps)
            st.session_state.report_week_label = week_label
            # Generate PDF immediately after sections are built
            try:
                generate_pdf_report = _safe_pdf_import()
                if generate_pdf_report:
                    from core.context_builder import build_kpi_summary
                    kpis = build_kpi_summary(df, caps)
                    # Sanitize: convert all values to plain strings/ints/floats
                    kpi_display = {}
                    for k, v in kpis.items():
                        label = k.replace("_", " ").title()
                        if v is None:
                            kpi_display[label] = "N/A"
                        else:
                            kpi_display[label] = str(v)
                    st.session_state.report_pdf_bytes = generate_pdf_report(
                        report_sections=st.session_state.report_sections,
                        kpis=kpi_display,
                        title="QA Weekly Report",
                        project_scope=selected,
                        source_label=provider.source_label,
                        week_label=week_label,
                        df=df,
                        caps=caps,
                    )
            except Exception as e:
                st.session_state.report_pdf_bytes = None
                st.warning(f"PDF generation failed: {e}")

    sections = st.session_state.report_sections

    # Export buttons (only once report is generated)
    if sections:
        col_pdf, col_md = st.columns([1, 1])

        with col_pdf:
            pdf_bytes = st.session_state.get("report_pdf_bytes")
            if pdf_bytes:
                st.download_button(
                    label="⬇ Download PDF",
                    data=pdf_bytes,
                    file_name=f"QA_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            else:
                st.caption("PDF unavailable — install reportlab")

        with col_md:
            md_lines = [f"# QA Weekly Report\n", f"**Scope:** {selected}  |  **Generated:** {datetime.now().strftime('%d %b %Y %H:%M')}\n\n---\n"]
            for sec in sections:
                md_lines.append(f"## {sec['heading']}\n\n{sec['summary']}\n")
                if sec.get("table_rows"):
                    rows = sec["table_rows"]
                    headers = list(rows[0].keys())
                    md_lines.append("| " + " | ".join(headers) + " |")
                    md_lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
                    for row in rows:
                        md_lines.append("| " + " | ".join(str(v) for v in row.values()) + " |")
                    md_lines.append("")
                if sec.get("interpretation"):
                    md_lines.append(f"**Interpretation:** {sec['interpretation']}\n")
                if sec.get("recommendations"):
                    md_lines.append(f"**Recommendations:** {sec['recommendations']}\n")
                md_lines.append("---\n")
            md_content = "\n".join(md_lines)
            st.download_button(
                label="⬇ Export Markdown",
                data=md_content.encode(),
                file_name=f"QA_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
                mime="text/markdown",
                use_container_width=True,
            )

    if not sections:
        st.info("Click **Generate Report** to build the QA report for the current dataset and project filter.")
        return

    st.markdown("---")
    report_week = st.session_state.get("report_week_label", week_label)
    st.markdown(
        f"## QA Weekly Report\n"
        f"**Week:** {report_week}  ·  "
        f"**Scope:** {selected}  ·  "
        f"**Source:** {provider.source_label}  ·  "
        f"**Generated:** {datetime.now().strftime('%d %B %Y, %H:%M')}"
    )
    st.markdown("---")

    section_charts = {
        "Issue Status Analysis":  status_pie,
        "Severity Analysis":      severity_pie,
        "Phase Analysis":         phase_pie,
        "Module Analysis":        module_bar,
        "Monthly Issue Trend":    monthly_trend_line,
        "Assignee Analysis":      assignee_workload,
        "Reporter Analysis":      reporter_bar,
        "Resolution Analysis":    resolution_bar,
        "Issue Aging":            aging_histogram,
        "Effort Analysis":        effort_by_project,
        "Project Comparison":     project_issue_count,
    }

    for sec in sections:
        heading = sec["heading"]
        st.subheader(heading)
        st.write(sec["summary"])

        chart_fn = section_charts.get(heading)
        if chart_fn:
            try:
                fig = chart_fn(df)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
            except Exception:
                pass

        if sec.get("table_rows"):
            tdf = pd.DataFrame(sec["table_rows"])
            st.dataframe(tdf, use_container_width=True, hide_index=True)

        if sec.get("interpretation"):
            with st.expander("📝 Interpretation & Recommendations"):
                st.markdown(f"**Interpretation:** {sec['interpretation']}")
                if sec.get("recommendations"):
                    st.markdown(f"**Recommendations:** {sec['recommendations']}")

        st.markdown("---")