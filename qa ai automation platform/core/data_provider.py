"""
Data Provider — single abstraction layer between the data source and the rest of the app.
To add Zoho Projects API support later: implement _load_from_zoho_api() and switch
the mode flag in get_dataframe(). Nothing else in the app changes.
"""

import pandas as pd
import streamlit as st
from pathlib import Path
from datetime import datetime
from typing import Optional

# ── Canonical column name mapping ────────────────────────────────────────────
# Maps every known alias (lowercased, stripped) → canonical snake_case name.
COLUMN_MAP: dict[str, str] = {
    "issue prefix":           "issue_prefix",
    "issue name":             "issue_name",
    "reporter":               "reporter",
    "created time":           "created_time",
    "last closed time":       "closed_time",
    "status":                 "status",
    "severity":               "severity",
    "module":                 "module",
    "classification":         "classification",
    "project name":           "project_name",
    "resolution":             "resolution",
    "assignee":               "assignee",
    "tags":                   "tags",
    "release milestone":      "release_milestone",
    "affected milestone":     "affected_milestone",
    "escalation level":       "escalation_level",
    "billable hours":         "billable_hours",
    "non billable hours":     "non_billable_hours",
    "total log hours":        "total_log_hours",
    "phase":                  "phase",
    # common alternate spellings
    "closed time":            "closed_time",
    "close time":             "closed_time",
    "last closed":            "closed_time",
    "created date":           "created_time",
    "create time":            "created_time",
    "logged hours":           "total_log_hours",
    "log hours":              "total_log_hours",
    "project":                "project_name",
    "bug name":               "issue_name",
    "defect name":            "issue_name",
    "escalation":             "escalation_level",
}

DATE_COLUMNS = {"created_time", "closed_time"}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Lowercase + strip column names, then remap to canonical names."""
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]
    df = df.rename(columns={k: v for k, v in COLUMN_MAP.items() if k in df.columns})
    return df


def _parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Parse known date columns to datetime, coercing errors silently."""
    for col in DATE_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=False)
    return df


def _clean_strings(df: pd.DataFrame) -> pd.DataFrame:
    """Strip whitespace from string columns."""
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].replace({"nan": None, "None": None, "": None})
    return df


def _load_from_excel(source) -> pd.DataFrame:
    """
    Load from either a file path (str/Path) or an UploadedFile object.
    Returns a normalized DataFrame.
    """
    df = pd.read_excel(source, engine="openpyxl")
    df = _normalize_columns(df)
    df = _parse_dates(df)
    df = _clean_strings(df)
    return df


def _load_from_zoho_api() -> pd.DataFrame:
    """
    FUTURE IMPLEMENTATION — Zoho Projects API.
    Replace this stub with real API calls.
    Must return a DataFrame with the same canonical column names as Excel mode.
    """
    raise NotImplementedError(
        "Zoho Projects API integration is not yet implemented. "
        "Configure it in core/data_provider.py → _load_from_zoho_api()."
    )


# ── Public API ────────────────────────────────────────────────────────────────

class DataProvider:
    """
    Singleton-style provider stored in st.session_state.
    Call DataProvider.load_excel(source) or DataProvider.load_from_api().
    Then read .df, .source_label, .loaded_at anywhere in the app.
    """

    def __init__(self):
        self.df: Optional[pd.DataFrame] = None
        self.source_label: str = "No data loaded"
        self.loaded_at: Optional[datetime] = None
        self.raw_filename: Optional[str] = None

    def load_excel(self, source, filename: str = "Excel file") -> "DataProvider":
        self.df = _load_from_excel(source)
        self.source_label = f"Excel — {filename}"
        self.loaded_at = datetime.now()
        self.raw_filename = filename
        return self

    def load_from_api(self) -> "DataProvider":
        self.df = _load_from_zoho_api()
        self.source_label = "Zoho Projects API"
        self.loaded_at = datetime.now()
        self.raw_filename = None
        return self

    def get_dataframe(self) -> Optional[pd.DataFrame]:
        return self.df

    def is_loaded(self) -> bool:
        return self.df is not None and not self.df.empty

    def row_count(self) -> int:
        return len(self.df) if self.is_loaded() else 0

    def project_names(self) -> list[str]:
        if not self.is_loaded() or "project_name" not in self.df.columns:
            return []
        return sorted(self.df["project_name"].dropna().unique().tolist())


def get_provider() -> DataProvider:
    """Return the singleton DataProvider from session state."""
    if "data_provider" not in st.session_state:
        st.session_state.data_provider = DataProvider()
    return st.session_state.data_provider


def try_autoload(path: str = "data/latest_qa.xlsx") -> bool:
    """
    On first run, try to auto-load from the default file path.
    Returns True if successful.
    """
    provider = get_provider()
    if provider.is_loaded():
        return True
    p = Path(path)
    if p.exists():
        try:
            provider.load_excel(str(p), filename=p.name)
            return True
        except Exception:
            return False
    return False
