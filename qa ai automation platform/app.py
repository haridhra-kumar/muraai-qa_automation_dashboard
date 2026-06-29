"""
QA AI Automation Platform — Main Entry Point
Run with: streamlit run app.py
"""

import streamlit as st
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# ── Page config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="QA AI Automation Platform",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Minimal global CSS ────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Tighten sidebar padding */
    section[data-testid="stSidebar"] > div { padding-top: 1rem; }
    /* KPI card metric value size */
    [data-testid="stMetricValue"] { font-size: 1.6rem !important; }
    /* Remove top padding from main content */
    .block-container { padding-top: 1.5rem; }
    /* Chat bubble styling */
    .chat-user { background: #e8f4f8; border-radius: 12px; padding: 10px 14px; margin: 4px 0; }
    .chat-ai   { background: #f0f4f8; border-radius: 12px; padding: 10px 14px; margin: 4px 0; }
    /* Hide the auto-generated multipage navigation list in the sidebar */
    [data-testid="stSidebarNav"] { display: none !important; }
    section[data-testid="stSidebar"] ul[data-testid="stSidebarNavItems"] { display: none !important; }
    nav[data-testid="stSidebarNav"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ── Auto-load data on first run ───────────────────────────────────────────────
from core.data_provider import get_provider, try_autoload
from core.capabilities import get_capabilities, invalidate_capabilities, build_capabilities

if "initialized" not in st.session_state:
    st.session_state.initialized = True
    st.session_state.selected_project = "All Projects"
    st.session_state.messages = []          # AI chat history
    try_autoload("data/latest_qa.xlsx")
    provider = get_provider()
    if provider.is_loaded():
        st.session_state.capabilities = build_capabilities(provider.get_dataframe())

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔍 QA Platform")
    st.markdown("---")

    page = st.radio(
        "Navigate",
        options=["🏠 Dashboard", "📊 Analytics", "📄 Weekly Reports", "🤖 AI Assistant", "⚙ Settings"],
        label_visibility="collapsed",
    )

    st.markdown("---")

    # ── Project filter ────────────────────────────────────────────────────────
    provider = get_provider()
    if provider.is_loaded():
        projects = ["All Projects"] + provider.project_names()
        selected = st.selectbox(
            "📁 Project Filter",
            options=projects,
            index=projects.index(st.session_state.get("selected_project", "All Projects"))
                  if st.session_state.get("selected_project", "All Projects") in projects else 0,
            key="project_selector",
        )
        st.session_state.selected_project = selected

        st.markdown("---")
        caps = st.session_state.get("capabilities")
        if caps:
            st.markdown(f"**📦 {caps.total_issues}** issues loaded")
            st.markdown(f"**🗂 {caps.project_count}** project(s)")
            st.markdown(f"**🕐** {provider.loaded_at.strftime('%H:%M, %d %b') if provider.loaded_at else '—'}")
    else:
        st.info("No data loaded. Go to **⚙ Settings** to upload a file.")

    st.markdown("---")
    st.markdown("<small>QA AI Automation Platform v1.0</small>", unsafe_allow_html=True)

# ── Route to page ─────────────────────────────────────────────────────────────
if page == "🏠 Dashboard":
    from pages.dashboard import render
    render()
elif page == "📊 Analytics":
    from pages.analytics import render
    render()
elif page == "📄 Weekly Reports":
    from pages.reports import render
    render()
elif page == "🤖 AI Assistant":
    from pages.ai_assistant import render
    render()
elif page == "⚙ Settings":
    from pages.settings import render
    render()