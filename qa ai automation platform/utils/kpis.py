"""
KPI helpers — pure calculation functions, no Streamlit imports.
All functions accept a DataFrame and return plain Python values.
"""

import pandas as pd
from typing import Optional


OPEN_STATUSES   = {"Open", "In Progress", "Reopened", "To Do", "In Review", "Active", "Re-Opened"}
CLOSED_STATUSES = {"Closed", "Fixed", "Resolved", "Done", "Completed", "Won't Fix", "Wont Fix", "Invalid"}
CRITICAL_SEVE   = {"Critical", "Blocker"}
HIGH_SEVE       = {"High"}


def filter_by_project(df: pd.DataFrame, project: Optional[str]) -> pd.DataFrame:
    """Return df filtered to a single project, or unfiltered if 'All Projects'."""
    if project and project != "All Projects" and "project_name" in df.columns:
        return df[df["project_name"] == project].copy()
    return df


def open_issue_count(df: pd.DataFrame) -> int:
    if "status" not in df.columns:
        return 0
    return int(df["status"].isin(OPEN_STATUSES).sum())


def closed_issue_count(df: pd.DataFrame) -> int:
    if "status" not in df.columns:
        return 0
    return int(df["status"].isin(CLOSED_STATUSES).sum())


def critical_issue_count(df: pd.DataFrame) -> int:
    if "severity" not in df.columns:
        return 0
    return int(df["severity"].isin(CRITICAL_SEVE).sum())


def high_issue_count(df: pd.DataFrame) -> int:
    if "severity" not in df.columns:
        return 0
    return int(df["severity"].isin(HIGH_SEVE).sum())


def avg_resolution_days(df: pd.DataFrame) -> Optional[float]:
    if "created_time" not in df.columns or "closed_time" not in df.columns:
        return None
    sub = df.dropna(subset=["created_time", "closed_time"]).copy()
    if sub.empty:
        return None
    sub["age"] = (sub["closed_time"] - sub["created_time"]).dt.days
    sub = sub[sub["age"] >= 0]
    return round(sub["age"].mean(), 1) if not sub.empty else None


def escalated_count(df: pd.DataFrame) -> int:
    if "escalation_level" not in df.columns:
        return 0
    return int(df["escalation_level"].notna().sum())


def _parse_hours(series: pd.Series) -> pd.Series:
    """Convert values to float hours. Handles H:MM:SS strings and plain numbers."""
    def _to_float(v):
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return 0.0
        s = str(v).strip()
        # Time string format H:MM or H:MM:SS
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

def total_log_hours(df: pd.DataFrame) -> float:
    if "total_log_hours" not in df.columns:
        return 0.0
    return round(_parse_hours(df["total_log_hours"].dropna()).sum(), 1)


def closure_rate(df: pd.DataFrame) -> float:
    total = len(df)
    if total == 0:
        return 0.0
    closed = closed_issue_count(df)
    return round(closed / total * 100, 1)


def defect_distribution_by_project(df: pd.DataFrame) -> pd.DataFrame:
    """Returns a DataFrame with project_name and issue count."""
    if "project_name" not in df.columns:
        return pd.DataFrame()
    return df["project_name"].value_counts().reset_index().rename(
        columns={"index": "project_name", "project_name": "count", "count": "count"}
    )


def monthly_trend(df: pd.DataFrame) -> pd.DataFrame:
    """Returns month-wise issue creation counts."""
    if "created_time" not in df.columns:
        return pd.DataFrame()
    sub = df.dropna(subset=["created_time"]).copy()
    sub["month"] = sub["created_time"].dt.to_period("M").dt.to_timestamp()
    trend = sub.groupby("month").size().reset_index(name="count")
    return trend.sort_values("month")


def aging_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """Returns a DataFrame with resolution age in days per issue."""
    if "created_time" not in df.columns or "closed_time" not in df.columns:
        return pd.DataFrame()
    sub = df.dropna(subset=["created_time", "closed_time"]).copy()
    sub["age_days"] = (sub["closed_time"] - sub["created_time"]).dt.days
    return sub[sub["age_days"] >= 0][["age_days"]].copy()


def top_n_values(df: pd.DataFrame, column: str, n: int = 10) -> pd.Series:
    if column not in df.columns:
        return pd.Series(dtype=int)
    return df[column].dropna().value_counts().head(n)