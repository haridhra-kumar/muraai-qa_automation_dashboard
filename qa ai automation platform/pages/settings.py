"""
Settings — data upload, dataset validation, API configuration placeholders,
and dataset capability inspection.
"""

import os
import streamlit as st
import pandas as pd
from core.data_provider import get_provider
from core.capabilities import get_capabilities, build_capabilities, invalidate_capabilities


def _validate_dataset(df: pd.DataFrame) -> list[dict]:
    """
    Run basic validation checks on the uploaded DataFrame.
    Returns a list of {check, status, detail} dicts.
    """
    results = []

    # Row count
    results.append({
        "Check": "Row count",
        "Status": "✅" if len(df) > 0 else "❌",
        "Detail": f"{len(df)} rows",
    })

    # Column count
    results.append({
        "Check": "Column count",
        "Status": "✅",
        "Detail": f"{len(df.columns)} columns detected",
    })

    # Duplicate rows
    dupes = df.duplicated().sum()
    results.append({
        "Check": "Duplicate rows",
        "Status": "⚠" if dupes > 0 else "✅",
        "Detail": f"{dupes} duplicate rows found",
    })

    # Key columns present
    key_cols = ["issue_name", "project_name", "status", "severity"]
    for col in key_cols:
        present = col in df.columns
        null_pct = round(df[col].isna().mean() * 100, 1) if present else None
        results.append({
            "Check": f"Column: {col}",
            "Status": "✅" if present else "⚠",
            "Detail": (
                f"Present ({null_pct}% null)" if present
                else "Not found in dataset"
            ),
        })

    # Date columns parseable
    for date_col in ["created_time", "closed_time"]:
        if date_col in df.columns:
            non_null = df[date_col].dropna()
            valid_dates = pd.to_datetime(non_null, errors="coerce").notna().sum()
            results.append({
                "Check": f"Date parse: {date_col}",
                "Status": "✅" if valid_dates == len(non_null) else "⚠",
                "Detail": f"{valid_dates}/{len(non_null)} dates valid",
            })

    return results


def render():
    st.title("⚙ Settings")
    st.markdown("Configure your data source, upload Excel files, and inspect dataset capabilities.")

    provider = get_provider()

    # ── Section 1: Upload ─────────────────────────────────────────────────────
    st.subheader("📂 Upload Dataset")
    st.markdown(
        "Upload a Zoho Projects Excel export. "
        "The platform automatically detects available columns and adapts its features."
    )

    uploaded_file = st.file_uploader(
        "Choose an Excel file (.xlsx)",
        type=["xlsx"],
        help="Upload your weekly Zoho Bug Tracker export.",
    )

    col_upload, col_validate = st.columns([2, 1])
    with col_upload:
        if uploaded_file and st.button("⬆ Load Dataset", type="primary", use_container_width=True):
            with st.spinner("Loading and normalizing dataset..."):
                try:
                    invalidate_capabilities()
                    provider.load_excel(uploaded_file, filename=uploaded_file.name)
                    df = provider.get_dataframe()
                    st.session_state.capabilities = build_capabilities(df)
                    st.session_state.messages = []  # Reset AI chat
                    st.session_state.dashboard_ai_summary = None
                    st.session_state.report_sections = None
                    st.success(f"✅ Loaded **{len(df)}** rows from **{uploaded_file.name}**")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to load file: {e}")

    with col_validate:
        if provider.is_loaded() and st.button("🔍 Validate Dataset", use_container_width=True):
            df = provider.get_dataframe()
            validation_results = _validate_dataset(df)
            st.session_state.validation_results = validation_results

    st.markdown("---")

    # ── Validation results ────────────────────────────────────────────────────
    if "validation_results" in st.session_state and st.session_state.validation_results:
        st.subheader("🔍 Validation Results")
        val_df = pd.DataFrame(st.session_state.validation_results)
        st.dataframe(val_df, use_container_width=True, hide_index=True)
        st.markdown("---")

    # ── Section 2: Current Dataset Info ──────────────────────────────────────
    st.subheader("📦 Current Dataset")

    if not provider.is_loaded():
        st.info("No dataset loaded. Upload an Excel file above, or place it at `data/latest_qa.xlsx` for auto-loading.")
    else:
        df = provider.get_dataframe()
        caps = get_capabilities(df)

        info_cols = st.columns(4)
        info_cols[0].metric("Total Rows", len(df))
        info_cols[1].metric("Columns", len(df.columns))
        info_cols[2].metric("Projects", caps.project_count)
        info_cols[3].metric("Source", provider.source_label.split("—")[0].strip())

        st.caption(f"**File:** {provider.raw_filename or '—'}  ·  "
                   f"**Loaded at:** {provider.loaded_at.strftime('%d %b %Y, %H:%M') if provider.loaded_at else '—'}")

        # Projects
        if caps.supports_project:
            with st.expander(f"📁 Detected Projects ({caps.project_count})"):
                for proj in provider.project_names():
                    count = len(df[df["project_name"] == proj])
                    st.markdown(f"- **{proj}** — {count} issues")

        # Detected columns
        with st.expander(f"🗂 Detected Columns ({len(caps.available_columns)})"):
            col_chunks = [caps.available_columns[i:i+4] for i in range(0, len(caps.available_columns), 4)]
            for chunk in col_chunks:
                c = st.columns(4)
                for col, name in zip(c, chunk):
                    col.code(name)

        # Capabilities
        with st.expander("⚙ Dataset Capabilities"):
            cap_dict = caps.to_dict()
            bool_caps = {k: v for k, v in cap_dict.items() if isinstance(v, bool)}
            num_caps  = {k: v for k, v in cap_dict.items() if isinstance(v, (int, float))}

            st.markdown("**Feature availability:**")
            rows = []
            for k, v in bool_caps.items():
                rows.append({"Capability": k.replace("_", " ").title(), "Available": "✅ Yes" if v else "❌ No"})
            cap_df = pd.DataFrame(rows)
            st.dataframe(cap_df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── Section 3: Groq API Status ────────────────────────────────────────────
    st.subheader("🤖 Groq API Configuration")

    api_key = os.getenv("GROQ_API_KEY", "")
    if api_key and api_key != "your_groq_api_key_here":
        masked = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
        st.success(f"✅ API key configured: `{masked}`")
    else:
        st.error("❌ GROQ_API_KEY not set. Create a `.env` file with: `GROQ_API_KEY=your_key_here`")

    st.markdown(
        "Get your free Groq API key at [console.groq.com](https://console.groq.com). "
        "The platform uses `llama-3.3-70b-versatile` by default."
    )

    col_test, _ = st.columns([1, 3])
    with col_test:
        if st.button("🔌 Test Groq Connection", use_container_width=True):
            if not api_key or api_key == "your_groq_api_key_here":
                st.error("No API key configured.")
            else:
                with st.spinner("Testing connection..."):
                    try:
                        from groq import Groq
                        client = Groq(api_key=api_key)
                        response = client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[{"role": "user", "content": "Reply with: Connection successful"}],
                            max_tokens=20,
                        )
                        st.success(f"✅ {response.choices[0].message.content}")
                    except Exception as e:
                        st.error(f"Connection failed: {e}")

    st.markdown("---")

    # ── Section 4: Future API Integration (Placeholder) ───────────────────────
    st.subheader("🔮 Future Zoho API Integration")
    st.markdown(
        "This section is a placeholder for future Zoho Projects API integration. "
        "When implemented, only `core/data_provider.py` needs to be updated — "
        "no other part of the application changes."
    )

    with st.expander("Configure Zoho API (Placeholder — Not Yet Active)"):
        st.text_input(
            "Zoho Projects API URL",
            value="https://projectsapi.zoho.com/restapi/portal/{portal}/projects/",
            disabled=True,
            help="Future integration — not yet implemented",
        )
        st.text_input(
            "Zoho Analytics API URL",
            value="https://analyticsapi.zoho.com/api/v2/",
            disabled=True,
            help="Future integration — not yet implemented",
        )
        st.text_input("Client ID", value="", placeholder="Zoho OAuth2 Client ID", disabled=True)
        st.text_input("Client Secret", value="", type="password", placeholder="Zoho OAuth2 Client Secret", disabled=True)

        col_a, col_b = st.columns(2)
        with col_a:
            st.button("🔌 Test Connection (Placeholder)", disabled=True, use_container_width=True)
        with col_b:
            st.button("🔄 Refresh From API (Placeholder)", disabled=True, use_container_width=True)

        st.caption(
            "To activate: implement `_load_from_zoho_api()` in `core/data_provider.py` "
            "and set `mode='api'` in `get_dataframe()`. All other modules remain unchanged."
        )
