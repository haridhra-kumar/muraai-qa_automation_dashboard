"""
AI Assistant — ChatGPT-style interface.
Fix: store chart figures in separate session_state list, not inside messages dict,
     to avoid "Object of type Figure is not JSON serializable" error.
"""

import os
import streamlit as st
from core.data_provider import get_provider
from core.capabilities import get_capabilities
from core.context_builder import build_ai_context
from utils.kpis import filter_by_project
from utils.charts import detect_chart_intent


SYSTEM_PROMPT = """You are a senior QA analyst and data expert with deep expertise in software quality.
You analyse QA datasets and provide clear, actionable insights to engineering managers and QA leads.

Your role:
- Answer questions about QA data with precision and brevity
- Identify risks, bottlenecks, and improvement opportunities
- Compare projects and highlight the highest-risk areas
- Provide executive-level summaries when asked
- Give specific, data-driven recommendations

Rules:
- Base every answer strictly on the provided dataset context
- If a metric or field is not in the context, clearly state it is unavailable
- Never fabricate numbers or invent data
- Keep responses concise unless asked for detail
- Use bullet points for lists, plain prose for summaries
"""

SUGGESTED_PROMPTS = [
    "Give me an executive summary of the current QA status",
    "Which project has the highest risk right now?",
    "Compare all projects by issue count and severity",
    "What are the top 5 defect hotspots by module?",
    "Analyse the severity distribution and highlight concerns",
    "What is the average issue resolution time?",
    "Who has the highest workload on the team?",
    "Show me the monthly issue trend and identify any spikes",
    "What are the main root causes of critical issues?",
    "What should management prioritise this week?",
]


def _get_groq_client():
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key or api_key == "your_groq_api_key_here":
        return None, "Groq API key not configured. Add GROQ_API_KEY to your .env file."
    try:
        from groq import Groq
        return Groq(api_key=api_key), None
    except ImportError:
        return None, "groq package not installed. Run: pip install groq"
    except Exception as e:
        return None, str(e)


def _build_messages(context: str, conversation: list[dict]) -> list[dict]:
    """Build message list: system + context + conversation (text only, no figures)."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Here is the current QA dataset context. Use this for all answers:\n\n{context}",
        },
        {
            "role": "assistant",
            "content": "Understood. I have reviewed the QA dataset context. Ask me anything about your QA data.",
        },
    ]
    # Only pass role + content to API — never chart_fig
    for msg in conversation[-20:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    return messages


def render():
    provider = get_provider()

    st.title("🤖 AI Assistant")
    st.markdown("Ask anything about your QA data. The assistant uses your dataset — no hallucinated numbers.")

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

    # Session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    # Separate list for chart figures — indexed by message position
    # Key: message index (int), value: go.Figure
    if "message_charts" not in st.session_state:
        st.session_state.message_charts = {}
    if "ai_context_key" not in st.session_state:
        st.session_state.ai_context_key = None

    # Rebuild context if project selection changed
    context_key = f"{selected}_{len(df)}"
    if st.session_state.ai_context_key != context_key:
        st.session_state.ai_context_key = context_key
        st.session_state.ai_context = build_ai_context(df, caps, selected)

    context = st.session_state.get("ai_context", "")

    # Top controls
    col_status, col_clear = st.columns([4, 1])
    with col_status:
        client, err = _get_groq_client()
        if err:
            st.warning(f"⚠ {err}")
        else:
            st.caption(f"✅ Connected · Model: llama-3.3-70b-versatile · Scope: **{selected}** · {len(df)} issues")
    with col_clear:
        if st.button("🗑 Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.message_charts = {}
            st.rerun()

    st.markdown("---")

    # Suggested prompts (only when chat is empty)
    if not st.session_state.messages:
        st.markdown("**Suggested questions:**")
        cols = st.columns(2)
        for i, prompt in enumerate(SUGGESTED_PROMPTS):
            with cols[i % 2]:
                if st.button(prompt, key=f"sugg_{i}", use_container_width=True):
                    st.session_state["_pending_prompt"] = prompt
                    st.rerun()

    # Chat history
    for i, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"], avatar="🧑" if msg["role"] == "user" else "🤖"):
            st.markdown(msg["content"])
            # Show chart if one was generated for this message (stored separately)
            chart_fig = st.session_state.message_charts.get(i)
            if chart_fig is not None:
                try:
                    st.plotly_chart(chart_fig, use_container_width=True)
                except Exception:
                    pass

    # Input
    user_input = st.chat_input("Ask about your QA data...")

    # Handle suggested prompt click
    if "_pending_prompt" in st.session_state:
        user_input = st.session_state.pop("_pending_prompt")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})

        # Render the user bubble immediately so it appears before the streaming response
        with st.chat_message("user", avatar="🧑"):
            st.markdown(user_input)

        if client is None:
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"Cannot connect to Groq API: {err}",
            })
            st.rerun()
            return

        # Build messages for API (text only)
        api_messages = _build_messages(
            context,
            st.session_state.messages[:-1] + [{"role": "user", "content": user_input}]
        )

        with st.chat_message("assistant", avatar="🤖"):
            response_placeholder = st.empty()
            full_response = ""
            error_occurred = False

            try:
                stream = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=api_messages,
                    max_tokens=1024,
                    temperature=0.4,
                    stream=True,
                )
                for chunk in stream:
                    delta = chunk.choices[0].delta.content or ""
                    full_response += delta
                    response_placeholder.markdown(full_response + "▌")
                response_placeholder.markdown(full_response)

            except Exception as e:
                full_response = f"Error communicating with Groq API: {str(e)}"
                response_placeholder.error(full_response)
                error_occurred = True

            # Auto-generate chart — store in message_charts, NOT in messages
            chart_fig = None
            if not error_occurred and full_response:
                try:
                    chart_fig = detect_chart_intent(full_response + " " + user_input, df)
                    if chart_fig is not None:
                        st.plotly_chart(chart_fig, use_container_width=True)
                except Exception:
                    chart_fig = None

        # Store message (text only — no figure in the dict)
        assistant_msg_index = len(st.session_state.messages)
        st.session_state.messages.append({
            "role": "assistant",
            "content": full_response,
        })
        # Store chart figure separately by message index
        if chart_fig is not None:
            st.session_state.message_charts[assistant_msg_index] = chart_fig

    # Capabilities panel
    with st.expander("📊 Dataset capabilities visible to the AI"):
        cap_dict = caps.to_dict()
        bool_caps = {k: ("✅" if v else "❌") for k, v in cap_dict.items() if isinstance(v, bool)}
        num_caps  = {k: v for k, v in cap_dict.items() if isinstance(v, (int, float))}
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Feature flags:**")
            for k, v in bool_caps.items():
                st.markdown(f"{v} `{k}`")
        with col2:
            st.markdown("**Counts:**")
            for k, v in num_caps.items():
                st.markdown(f"**{k}:** {v}")