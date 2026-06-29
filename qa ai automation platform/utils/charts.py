"""
Chart factory — all Plotly chart creation lives here.
Every function returns go.Figure | None.
Pages call st.plotly_chart() only when the return value is not None.
No Streamlit imports in this file.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional

# ── Shared theme ──────────────────────────────────────────────────────────────
PALETTE = px.colors.qualitative.Set2
LAYOUT_DEFAULTS = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", size=12),
    margin=dict(l=20, r=20, t=40, b=20),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)


def _apply_defaults(fig: go.Figure, title: str = "") -> go.Figure:
    fig.update_layout(title=dict(text=title, font=dict(size=14)), **LAYOUT_DEFAULTS)
    return fig


# ── Status ────────────────────────────────────────────────────────────────────

def status_bar(df: pd.DataFrame, by_project: bool = False) -> Optional[go.Figure]:
    if "status" not in df.columns or df["status"].dropna().empty:
        return None
    if by_project and "project_name" in df.columns:
        counts = df.groupby(["project_name", "status"]).size().reset_index(name="count")
        fig = px.bar(counts, x="project_name", y="count", color="status",
                     color_discrete_sequence=PALETTE, barmode="stack")
        return _apply_defaults(fig, "Issue Status by Project")
    counts = df["status"].value_counts().reset_index()
    counts.columns = ["status", "count"]
    fig = px.bar(counts, x="status", y="count", color="status",
                 color_discrete_sequence=PALETTE)
    fig.update_layout(showlegend=False)
    return _apply_defaults(fig, "Issue Status Distribution")


def status_pie(df: pd.DataFrame) -> Optional[go.Figure]:
    if "status" not in df.columns or df["status"].dropna().empty:
        return None
    counts = df["status"].value_counts()
    fig = px.pie(values=counts.values, names=counts.index,
                 color_discrete_sequence=PALETTE, hole=0.4)
    return _apply_defaults(fig, "Status Breakdown")


# ── Severity ──────────────────────────────────────────────────────────────────

SEVERITY_COLOR_MAP = {
    "Critical": "#d62728",
    "Blocker":  "#d62728",
    "High":     "#ff7f0e",
    "Medium":   "#ffbb78",
    "Low":      "#2ca02c",
    "Trivial":  "#98df8a",
}

def severity_bar(df: pd.DataFrame, by_project: bool = False) -> Optional[go.Figure]:
    if "severity" not in df.columns or df["severity"].dropna().empty:
        return None
    if by_project and "project_name" in df.columns:
        counts = df.groupby(["project_name", "severity"]).size().reset_index(name="count")
        fig = px.bar(counts, x="project_name", y="count", color="severity",
                     color_discrete_map=SEVERITY_COLOR_MAP, barmode="stack")
        return _apply_defaults(fig, "Severity Distribution by Project")
    counts = df["severity"].value_counts().reset_index()
    counts.columns = ["severity", "count"]
    fig = px.bar(counts, x="severity", y="count", color="severity",
                 color_discrete_map=SEVERITY_COLOR_MAP)
    fig.update_layout(showlegend=False)
    return _apply_defaults(fig, "Severity Distribution")


def severity_pie(df: pd.DataFrame) -> Optional[go.Figure]:
    if "severity" not in df.columns or df["severity"].dropna().empty:
        return None
    counts = df["severity"].value_counts()
    colors = [SEVERITY_COLOR_MAP.get(s, "#aec7e8") for s in counts.index]
    fig = px.pie(values=counts.values, names=counts.index,
                 color_discrete_sequence=colors, hole=0.4)
    return _apply_defaults(fig, "Severity Breakdown")


def severity_heatmap(df: pd.DataFrame) -> Optional[go.Figure]:
    if "severity" not in df.columns or "project_name" not in df.columns:
        return None
    pivot = df.groupby(["project_name", "severity"]).size().unstack(fill_value=0)
    if pivot.empty:
        return None
    fig = px.imshow(pivot, color_continuous_scale="Reds", aspect="auto",
                    text_auto=True)
    return _apply_defaults(fig, "Severity Heat Map (Project × Severity)")


# ── Phase ─────────────────────────────────────────────────────────────────────

def phase_bar(df: pd.DataFrame, by_project: bool = False) -> Optional[go.Figure]:
    if "phase" not in df.columns or df["phase"].dropna().empty:
        return None
    if by_project and "project_name" in df.columns:
        counts = df.groupby(["project_name", "phase"]).size().reset_index(name="count")
        fig = px.bar(counts, x="project_name", y="count", color="phase",
                     color_discrete_sequence=PALETTE, barmode="stack")
        return _apply_defaults(fig, "Phase Distribution by Project")
    counts = df["phase"].value_counts().reset_index()
    counts.columns = ["phase", "count"]
    fig = px.bar(counts, x="phase", y="count", color="phase",
                 color_discrete_sequence=PALETTE)
    fig.update_layout(showlegend=False)
    return _apply_defaults(fig, "Phase Distribution")


def phase_pie(df: pd.DataFrame) -> Optional[go.Figure]:
    if "phase" not in df.columns or df["phase"].dropna().empty:
        return None
    counts = df["phase"].value_counts()
    fig = px.pie(values=counts.values, names=counts.index,
                 color_discrete_sequence=PALETTE, hole=0.4)
    return _apply_defaults(fig, "Phase Breakdown")


# ── Module ────────────────────────────────────────────────────────────────────

def module_bar(df: pd.DataFrame, top_n: int = 15) -> Optional[go.Figure]:
    if "module" not in df.columns or df["module"].dropna().empty:
        return None
    counts = df["module"].value_counts().head(top_n).reset_index()
    counts.columns = ["module", "count"]
    fig = px.bar(counts, x="count", y="module", orientation="h",
                 color_discrete_sequence=PALETTE)
    fig.update_layout(yaxis=dict(categoryorder="total ascending"), showlegend=False)
    return _apply_defaults(fig, f"Top {top_n} Modules by Issue Count")


# ── Timeline / Trend ─────────────────────────────────────────────────────────

def monthly_trend_line(df: pd.DataFrame) -> Optional[go.Figure]:
    if "created_time" not in df.columns or df["created_time"].dropna().empty:
        return None
    sub = df.dropna(subset=["created_time"]).copy()
    sub["month"] = sub["created_time"].dt.to_period("M").dt.to_timestamp()
    trend = sub.groupby("month").size().reset_index(name="count")
    if trend.empty:
        return None
    fig = px.line(trend, x="month", y="count", markers=True,
                  color_discrete_sequence=PALETTE)
    fig.update_traces(line=dict(width=2))
    return _apply_defaults(fig, "Monthly Issue Creation Trend")


def monthly_trend_by_project(df: pd.DataFrame) -> Optional[go.Figure]:
    if "created_time" not in df.columns or "project_name" not in df.columns:
        return None
    sub = df.dropna(subset=["created_time"]).copy()
    sub["month"] = sub["created_time"].dt.to_period("M").dt.to_timestamp()
    trend = sub.groupby(["month", "project_name"]).size().reset_index(name="count")
    if trend.empty:
        return None
    fig = px.line(trend, x="month", y="count", color="project_name",
                  markers=True, color_discrete_sequence=PALETTE)
    return _apply_defaults(fig, "Monthly Issue Trend by Project")


# ── Aging ────────────────────────────────────────────────────────────────────

def aging_histogram(df: pd.DataFrame) -> Optional[go.Figure]:
    if "created_time" not in df.columns or "closed_time" not in df.columns:
        return None
    sub = df.dropna(subset=["created_time", "closed_time"]).copy()
    sub["age_days"] = (sub["closed_time"] - sub["created_time"]).dt.days
    sub = sub[sub["age_days"] >= 0]
    if sub.empty:
        return None
    fig = px.histogram(sub, x="age_days", nbins=30, color_discrete_sequence=PALETTE)
    fig.update_layout(xaxis_title="Resolution Age (days)", yaxis_title="Count")
    return _apply_defaults(fig, "Issue Resolution Age Distribution")


def aging_by_project(df: pd.DataFrame) -> Optional[go.Figure]:
    if "created_time" not in df.columns or "closed_time" not in df.columns or "project_name" not in df.columns:
        return None
    sub = df.dropna(subset=["created_time", "closed_time"]).copy()
    sub["age_days"] = (sub["closed_time"] - sub["created_time"]).dt.days
    sub = sub[sub["age_days"] >= 0]
    if sub.empty:
        return None
    fig = px.box(sub, x="project_name", y="age_days", color="project_name",
                 color_discrete_sequence=PALETTE)
    fig.update_layout(showlegend=False, xaxis_title="Project", yaxis_title="Days to Resolve")
    return _apply_defaults(fig, "Issue Aging by Project")


# ── People ────────────────────────────────────────────────────────────────────

def assignee_workload(df: pd.DataFrame, top_n: int = 15) -> Optional[go.Figure]:
    if "assignee" not in df.columns or df["assignee"].dropna().empty:
        return None
    counts = df["assignee"].value_counts().head(top_n).reset_index()
    counts.columns = ["assignee", "count"]
    fig = px.bar(counts, x="count", y="assignee", orientation="h",
                 color_discrete_sequence=PALETTE)
    fig.update_layout(yaxis=dict(categoryorder="total ascending"), showlegend=False)
    return _apply_defaults(fig, f"Top {top_n} Assignees by Issue Count")


def reporter_bar(df: pd.DataFrame, top_n: int = 10) -> Optional[go.Figure]:
    if "reporter" not in df.columns or df["reporter"].dropna().empty:
        return None
    counts = df["reporter"].value_counts().head(top_n).reset_index()
    counts.columns = ["reporter", "count"]
    fig = px.bar(counts, x="count", y="reporter", orientation="h",
                 color_discrete_sequence=PALETTE)
    fig.update_layout(yaxis=dict(categoryorder="total ascending"), showlegend=False)
    return _apply_defaults(fig, f"Top {top_n} Reporters")


# ── Resolution ───────────────────────────────────────────────────────────────

def resolution_bar(df: pd.DataFrame) -> Optional[go.Figure]:
    if "resolution" not in df.columns or df["resolution"].dropna().empty:
        return None
    counts = df["resolution"].value_counts().reset_index()
    counts.columns = ["resolution", "count"]
    # Truncate long resolution text to prevent axis rendering issues
    counts["resolution"] = counts["resolution"].astype(str).str.slice(0, 40)
    counts = counts.head(15)  # top 15 only
    fig = px.bar(counts, x="count", y="resolution", orientation="h",
                 color_discrete_sequence=PALETTE)
    fig.update_layout(showlegend=False, yaxis=dict(categoryorder="total ascending"))
    return _apply_defaults(fig, "Resolution Analysis")


# ── Escalation ───────────────────────────────────────────────────────────────

def escalation_bar(df: pd.DataFrame) -> Optional[go.Figure]:
    if "escalation_level" not in df.columns or df["escalation_level"].dropna().empty:
        return None
    counts = df["escalation_level"].value_counts().reset_index()
    counts.columns = ["escalation_level", "count"]
    fig = px.bar(counts, x="escalation_level", y="count", color="escalation_level",
                 color_discrete_sequence=PALETTE)
    fig.update_layout(showlegend=False)
    return _apply_defaults(fig, "Escalation Level Distribution")


# ── Effort ────────────────────────────────────────────────────────────────────

def _parse_hours_series(series: pd.Series) -> pd.Series:
    """Convert H:MM:SS strings or plain numbers to float hours."""
    def _to_float(v):
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return 0.0
        s = str(v).strip()
        if ":" in s:
            parts = s.split(":")
            try:
                h = float(parts[0]) if parts[0] else 0
                m = float(parts[1]) / 60 if len(parts) > 1 and parts[1] else 0
                return h + m
            except (ValueError, IndexError):
                return 0.0
        try:
            return float(s)
        except (ValueError, TypeError):
            return 0.0
    return series.apply(_to_float)

def effort_by_project(df: pd.DataFrame) -> Optional[go.Figure]:
    if "total_log_hours" not in df.columns or "project_name" not in df.columns:
        return None
    df2 = df.copy()
    df2["_hours_float"] = _parse_hours_series(df2["total_log_hours"])
    effort = df2.groupby("project_name")["_hours_float"].sum().reset_index()
    effort.columns = ["project_name", "total_hours"]
    effort = effort[effort["total_hours"] > 0]
    if effort.empty:
        return None
    fig = px.bar(effort, x="total_hours", y="project_name", orientation="h",
                 color_discrete_sequence=PALETTE)
    fig.update_layout(yaxis=dict(categoryorder="total ascending"), showlegend=False)
    return _apply_defaults(fig, "Total Log Hours by Project")


def billable_vs_nonbillable(df: pd.DataFrame) -> Optional[go.Figure]:
    if "billable_hours" not in df.columns or "non_billable_hours" not in df.columns:
        return None
    b = df["billable_hours"].dropna().sum()
    nb = df["non_billable_hours"].dropna().sum()
    if b == 0 and nb == 0:
        return None
    fig = px.pie(values=[b, nb], names=["Billable", "Non-Billable"],
                 color_discrete_sequence=PALETTE, hole=0.4)
    return _apply_defaults(fig, "Billable vs Non-Billable Hours")


# ── Project overview ──────────────────────────────────────────────────────────

def project_issue_count(df: pd.DataFrame) -> Optional[go.Figure]:
    if "project_name" not in df.columns or df["project_name"].dropna().empty:
        return None
    counts = df["project_name"].value_counts().reset_index()
    counts.columns = ["project_name", "count"]
    fig = px.bar(counts, x="count", y="project_name", orientation="h",
                 color_discrete_sequence=PALETTE)
    fig.update_layout(yaxis=dict(categoryorder="total ascending"), showlegend=False)
    return _apply_defaults(fig, "Total Issues by Project")


def classification_bar(df: pd.DataFrame) -> Optional[go.Figure]:
    if "classification" not in df.columns or df["classification"].dropna().empty:
        return None
    counts = df["classification"].value_counts().reset_index()
    counts.columns = ["classification", "count"]
    fig = px.bar(counts, x="classification", y="count", color="classification",
                 color_discrete_sequence=PALETTE)
    fig.update_layout(showlegend=False)
    return _apply_defaults(fig, "Classification Breakdown")


# ── AI-driven chart selection ─────────────────────────────────────────────────

CHART_INTENT_MAP = {
    "compare":      ["project_issue_count", "severity_bar"],
    "project":      ["project_issue_count", "status_bar"],
    "severity":     ["severity_pie", "severity_bar"],
    "trend":        ["monthly_trend_line"],
    "module":       ["module_bar"],
    "assignee":     ["assignee_workload"],
    "workload":     ["assignee_workload"],
    "reporter":     ["reporter_bar"],
    "phase":        ["phase_bar"],
    "resolution":   ["resolution_bar"],
    "escalation":   ["escalation_bar"],
    "aging":        ["aging_histogram"],
    "effort":       ["effort_by_project"],
    "hours":        ["effort_by_project", "billable_vs_nonbillable"],
    "status":       ["status_pie", "status_bar"],
    "distribution": ["severity_pie", "status_pie"],
    "heat":         ["severity_heatmap"],
    "heatmap":      ["severity_heatmap"],
}

CHART_REGISTRY = {
    "project_issue_count":   project_issue_count,
    "severity_bar":          severity_bar,
    "severity_pie":          severity_pie,
    "severity_heatmap":      severity_heatmap,
    "status_bar":            status_bar,
    "status_pie":            status_pie,
    "phase_bar":             phase_bar,
    "phase_pie":             phase_pie,
    "module_bar":            module_bar,
    "monthly_trend_line":    monthly_trend_line,
    "aging_histogram":       aging_histogram,
    "aging_by_project":      aging_by_project,
    "assignee_workload":     assignee_workload,
    "reporter_bar":          reporter_bar,
    "resolution_bar":        resolution_bar,
    "escalation_bar":        escalation_bar,
    "effort_by_project":     effort_by_project,
    "billable_vs_nonbillable": billable_vs_nonbillable,
    "classification_bar":    classification_bar,
}


def detect_chart_intent(text: str, df: pd.DataFrame) -> Optional[go.Figure]:
    """
    Scan AI response text for chart keywords.
    Return the first matching chart that can be generated from df.
    Returns None if no relevant chart found.
    """
    text_lower = text.lower()
    for keyword, chart_names in CHART_INTENT_MAP.items():
        if keyword in text_lower:
            for chart_name in chart_names:
                fn = CHART_REGISTRY.get(chart_name)
                if fn:
                    try:
                        fig = fn(df)
                        if fig is not None:
                            return fig
                    except Exception:
                        continue
    return None