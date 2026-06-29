"""
Dataset Capability Engine — inspects the loaded DataFrame once and exposes
boolean flags for every optional feature. All pages read from this object;
no page ever checks df.columns directly.
"""

from dataclasses import dataclass, field
from typing import Optional
import pandas as pd


@dataclass
class Capabilities:
    # ── Core identity ─────────────────────────────────────────────────────────
    supports_issue_name:       bool = False
    supports_issue_prefix:     bool = False
    supports_project:          bool = False

    # ── Status & workflow ─────────────────────────────────────────────────────
    supports_status:           bool = False
    supports_resolution:       bool = False
    supports_classification:   bool = False

    # ── Severity & escalation ─────────────────────────────────────────────────
    supports_severity:         bool = False
    supports_escalation:       bool = False

    # ── Organisation ─────────────────────────────────────────────────────────
    supports_module:           bool = False
    supports_phase:            bool = False
    supports_tags:             bool = False

    # ── People ───────────────────────────────────────────────────────────────
    supports_reporter:         bool = False
    supports_assignee:         bool = False

    # ── Dates & aging ────────────────────────────────────────────────────────
    supports_created_dates:    bool = False
    supports_closed_dates:     bool = False
    supports_aging:            bool = False   # requires both created + closed

    # ── Milestones ───────────────────────────────────────────────────────────
    supports_release_milestones:   bool = False
    supports_affected_milestones:  bool = False

    # ── Effort / hours ───────────────────────────────────────────────────────
    supports_log_hours:        bool = False
    supports_billable_hours:   bool = False
    supports_effort:           bool = False   # true if any hours column exists

    # ── Derived / computed ────────────────────────────────────────────────────
    has_multi_project:         bool = False   # more than one distinct project
    project_count:             int  = 0
    total_issues:              int  = 0

    # ── All present columns (canonical names) ─────────────────────────────────
    available_columns: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if k != "available_columns"}


def build_capabilities(df: pd.DataFrame) -> Capabilities:
    """
    Inspect df once and return a populated Capabilities object.
    Call this immediately after loading data; store result in session_state.
    """
    cols = set(df.columns.tolist())

    def has(*names) -> bool:
        """True if ANY of the given canonical column names exist and have non-null data."""
        for name in names:
            if name in cols and df[name].notna().any():
                return True
        return False

    supports_created = has("created_time")
    supports_closed  = has("closed_time")
    supports_effort  = has("total_log_hours", "billable_hours", "non_billable_hours")

    project_count = 0
    if has("project_name"):
        project_count = int(df["project_name"].dropna().nunique())

    caps = Capabilities(
        supports_issue_name       = has("issue_name"),
        supports_issue_prefix     = has("issue_prefix"),
        supports_project          = has("project_name"),

        supports_status           = has("status"),
        supports_resolution       = has("resolution"),
        supports_classification   = has("classification"),

        supports_severity         = has("severity"),
        supports_escalation       = has("escalation_level"),

        supports_module           = has("module"),
        supports_phase            = has("phase"),
        supports_tags             = has("tags"),

        supports_reporter         = has("reporter"),
        supports_assignee         = has("assignee"),

        supports_created_dates    = supports_created,
        supports_closed_dates     = supports_closed,
        supports_aging            = supports_created and supports_closed,

        supports_release_milestones   = has("release_milestone"),
        supports_affected_milestones  = has("affected_milestone"),

        supports_log_hours        = has("total_log_hours"),
        supports_billable_hours   = has("billable_hours"),
        supports_effort           = supports_effort,

        has_multi_project         = project_count > 1,
        project_count             = project_count,
        total_issues              = len(df),

        available_columns         = sorted(cols),
    )

    return caps


def get_capabilities(df: Optional[pd.DataFrame] = None) -> Optional[Capabilities]:
    """
    Return capabilities from session_state.
    If df is supplied and capabilities haven't been built yet, build and cache them.
    """
    import streamlit as st
    if "capabilities" not in st.session_state or st.session_state.capabilities is None:
        if df is not None:
            st.session_state.capabilities = build_capabilities(df)
        else:
            return None
    return st.session_state.capabilities


def invalidate_capabilities():
    """Call this whenever a new dataset is loaded."""
    import streamlit as st
    if "capabilities" in st.session_state:
        del st.session_state["capabilities"]
