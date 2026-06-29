"""
Context Builder — computes all KPIs, aggregates and summaries from Python,
then packages them into a structured dict / string for Groq.
Python does the math. Groq does the reasoning. No raw rows ever sent to AI.
"""

import pandas as pd
from datetime import datetime
from typing import Optional
from core.capabilities import Capabilities


def _safe_value_counts(series: pd.Series, top_n: int = 10) -> dict:
    return series.dropna().value_counts().head(top_n).to_dict()


def _pct(part: int, total: int) -> str:
    if total == 0:
        return "0%"
    return f"{round(part / total * 100, 1)}%"


def build_ai_context(
    df: pd.DataFrame,
    caps: Capabilities,
    selected_project: Optional[str] = None,
) -> str:
    """
    Build a structured plain-text context block for Groq.
    Filters by project if selected_project is not None / 'All Projects'.
    """
    if selected_project and selected_project != "All Projects":
        df = df[df["project_name"] == selected_project].copy()
        scope_label = f"Project: {selected_project}"
    else:
        scope_label = "All Projects"

    total = len(df)
    if total == 0:
        return f"No data available for {scope_label}."

    lines = [
        "=== QA DATASET CONTEXT ===",
        f"Scope: {scope_label}",
        f"Total Issues: {total}",
        f"Data as of: {datetime.now().strftime('%Y-%m-%d')}",
        "",
    ]

    # ── Projects ──────────────────────────────────────────────────────────────
    if caps.supports_project:
        proj_counts = _safe_value_counts(df["project_name"])
        lines.append("PROJECTS:")
        for proj, cnt in proj_counts.items():
            lines.append(f"  {proj}: {cnt} issues ({_pct(cnt, total)})")
        lines.append("")

    # ── Status ────────────────────────────────────────────────────────────────
    if caps.supports_status:
        status_counts = _safe_value_counts(df["status"])
        lines.append("STATUS BREAKDOWN:")
        for s, cnt in status_counts.items():
            lines.append(f"  {s}: {cnt} ({_pct(cnt, total)})")
        lines.append("")

    # ── Severity ──────────────────────────────────────────────────────────────
    if caps.supports_severity:
        sev_counts = _safe_value_counts(df["severity"])
        lines.append("SEVERITY BREAKDOWN:")
        for s, cnt in sev_counts.items():
            lines.append(f"  {s}: {cnt} ({_pct(cnt, total)})")
        # Critical / High issues
        critical_high = df[df["severity"].isin(["Critical", "High", "Blocker", "P1", "P2"])]["severity"].count()
        lines.append(f"  High-priority (Critical/High/Blocker): {critical_high} ({_pct(critical_high, total)})")
        lines.append("")

    # ── Resolution ───────────────────────────────────────────────────────────
    if caps.supports_resolution:
        res_counts = _safe_value_counts(df["resolution"])
        lines.append("RESOLUTION BREAKDOWN:")
        for r, cnt in res_counts.items():
            lines.append(f"  {r}: {cnt} ({_pct(cnt, total)})")
        lines.append("")

    # ── Phase ────────────────────────────────────────────────────────────────
    if caps.supports_phase:
        phase_counts = _safe_value_counts(df["phase"])
        lines.append("PHASE BREAKDOWN:")
        for p, cnt in phase_counts.items():
            lines.append(f"  {p}: {cnt} ({_pct(cnt, total)})")
        lines.append("")

    # ── Module ───────────────────────────────────────────────────────────────
    if caps.supports_module:
        mod_counts = _safe_value_counts(df["module"], top_n=15)
        lines.append("TOP MODULES BY ISSUE COUNT:")
        for m, cnt in mod_counts.items():
            lines.append(f"  {m}: {cnt}")
        lines.append("")

    # ── Classification ───────────────────────────────────────────────────────
    if caps.supports_classification:
        cls_counts = _safe_value_counts(df["classification"])
        lines.append("CLASSIFICATION BREAKDOWN:")
        for c, cnt in cls_counts.items():
            lines.append(f"  {c}: {cnt} ({_pct(cnt, total)})")
        lines.append("")

    # ── Escalation ───────────────────────────────────────────────────────────
    if caps.supports_escalation:
        esc_counts = _safe_value_counts(df["escalation_level"])
        lines.append("ESCALATION LEVELS:")
        for e, cnt in esc_counts.items():
            lines.append(f"  {e}: {cnt} ({_pct(cnt, total)})")
        lines.append("")

    # ── People ───────────────────────────────────────────────────────────────
    if caps.supports_reporter:
        rep_counts = _safe_value_counts(df["reporter"], top_n=10)
        lines.append("TOP REPORTERS:")
        for r, cnt in rep_counts.items():
            lines.append(f"  {r}: {cnt} issues")
        lines.append("")

    if caps.supports_assignee:
        asgn_counts = _safe_value_counts(df["assignee"], top_n=10)
        lines.append("TOP ASSIGNEES (WORKLOAD):")
        for a, cnt in asgn_counts.items():
            lines.append(f"  {a}: {cnt} issues")
        lines.append("")

    # ── Dates & Aging ────────────────────────────────────────────────────────
    if caps.supports_created_dates:
        min_date = df["created_time"].dropna().min()
        max_date = df["created_time"].dropna().max()
        lines.append(f"DATE RANGE: {min_date.strftime('%Y-%m-%d') if pd.notna(min_date) else 'N/A'} "
                     f"to {max_date.strftime('%Y-%m-%d') if pd.notna(max_date) else 'N/A'}")

        # Monthly trend
        df_dated = df.dropna(subset=["created_time"]).copy()
        df_dated["month"] = df_dated["created_time"].dt.to_period("M").astype(str)
        monthly = df_dated["month"].value_counts().sort_index()
        if not monthly.empty:
            lines.append("MONTHLY ISSUE CREATION TREND (last 6 months):")
            for month, cnt in monthly.tail(6).items():
                lines.append(f"  {month}: {cnt} issues")
        lines.append("")

    if caps.supports_aging:
        df_aged = df.dropna(subset=["created_time", "closed_time"]).copy()
        if not df_aged.empty:
            df_aged["age_days"] = (df_aged["closed_time"] - df_aged["created_time"]).dt.days
            df_aged = df_aged[df_aged["age_days"] >= 0]
            if not df_aged.empty:
                avg_age = df_aged["age_days"].mean()
                max_age = df_aged["age_days"].max()
                lines.append(f"ISSUE AGING: Avg resolution time = {avg_age:.1f} days, Max = {max_age:.0f} days")
                lines.append("")

    # ── Effort ───────────────────────────────────────────────────────────────
    if caps.supports_effort:
        lines.append("EFFORT SUMMARY:")
        if caps.supports_log_hours:
            total_hours = pd.to_numeric(
                df["total_log_hours"], errors="coerce"
            ).sum()
            lines.append(f"  Total Log Hours: {total_hours:.1f}")

        if caps.supports_billable_hours:
            bill = pd.to_numeric(
                df["billable_hours"], errors="coerce"
            ).sum()

            non_bill = (
                pd.to_numeric(
                    df["non_billable_hours"], errors="coerce"
                ).sum()
                if "non_billable_hours" in df.columns
                else 0
            )

            lines.append(
                f"  Billable: {bill:.1f}  Non-Billable: {non_bill:.1f}"
            )
        lines.append("")

    # ── Milestones ───────────────────────────────────────────────────────────
    if caps.supports_release_milestones:
        ms_counts = _safe_value_counts(df["release_milestone"], top_n=8)
        lines.append("RELEASE MILESTONES:")
        for m, cnt in ms_counts.items():
            lines.append(f"  {m}: {cnt} issues")
        lines.append("")

    # ── Per-project breakdown (multi-project only) ────────────────────────────
    if caps.has_multi_project and caps.supports_project:
        lines.append("PER-PROJECT BREAKDOWN:")
        for proj in df["project_name"].dropna().unique():
            sub = df[df["project_name"] == proj]
            lines.append(f"\n  [{proj}]  Total: {len(sub)}")
            if caps.supports_status:
                open_issues = sub[sub["status"].isin(
                    ["Open", "In Progress", "Reopened", "To Do", "In Review"]
                )]
                lines.append(f"    Open/Active: {len(open_issues)}")
            if caps.supports_severity:
                critical = sub[sub["severity"].isin(["Critical", "Blocker", "High"])]
                lines.append(f"    Critical/High: {len(critical)}")
            if caps.supports_phase:
                phase_dist = sub["phase"].value_counts().head(3).to_dict()
                lines.append(f"    Phase dist: {phase_dist}")
        lines.append("")

    lines.append("=== END CONTEXT ===")
    return "\n".join(lines)


def build_kpi_summary(df: pd.DataFrame, caps: Capabilities) -> dict:
    """
    Return a flat dict of key metrics for the Dashboard KPI cards.
    Only includes metrics that are genuinely supported.
    """
    kpis = {"total_issues": len(df)}

    if caps.supports_status:
        open_statuses = ["Open", "In Progress", "Reopened", "To Do", "In Review", "Active"]
        closed_statuses = ["Closed", "Fixed", "Resolved", "Done", "Completed", "Won't Fix"]
        kpis["open_issues"] = int(df[df["status"].isin(open_statuses)]["status"].count())
        kpis["closed_issues"] = int(df[df["status"].isin(closed_statuses)]["status"].count())

    if caps.supports_severity:
        kpis["critical_issues"] = int(df[df["severity"].isin(["Critical", "Blocker"])]["severity"].count())
        kpis["high_issues"] = int(df[df["severity"] == "High"]["severity"].count())

    if caps.supports_aging:
        df_aged = df.dropna(subset=["created_time", "closed_time"]).copy()
        if not df_aged.empty:
            df_aged["age_days"] = (df_aged["closed_time"] - df_aged["created_time"]).dt.days
            df_aged = df_aged[df_aged["age_days"] >= 0]
            if not df_aged.empty:
                kpis["avg_resolution_days"] = round(df_aged["age_days"].mean(), 1)

    if caps.supports_escalation:
        escalated = df[df["escalation_level"].notna() & (df["escalation_level"] != "None")]
        kpis["escalated_issues"] = len(escalated)

    if caps.supports_project:
        kpis["project_count"] = caps.project_count

    if caps.supports_log_hours:
        hours = pd.to_numeric(
            df["total_log_hours"],
            errors="coerce"
        )
        kpis["total_log_hours"] = round(hours.sum(), 1)

    return kpis
