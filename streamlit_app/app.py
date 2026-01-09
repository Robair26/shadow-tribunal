import streamlit as st
import html
import json
import time
from core.logic import run_shadow_tribunal_session

# =========================
# Page + Sidebar
# =========================
st.set_page_config(page_title="Shadow Tribunal", page_icon="🕶️", layout="centered")

st.sidebar.title("Controls")

model = st.sidebar.selectbox(
    "Model",
    ["llama3.2:3b", "llama3.1:8b", "mistral:7b"],
    index=0,
)

show_meta = st.sidebar.toggle("Show meta", value=False)

if st.sidebar.button("Reset session"):
    st.session_state.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("Example inputs")

examples = {
    "Avoidance loop": (
        "I keep delaying hard conversations. I overthink, stay polite, then resent people later. "
        "I act calm, but I replay everything at night and imagine what I should have said."
    ),
    "Perfection trap": (
        "If I can’t do something perfectly, I avoid starting. I tell myself I’m being strategic, "
        "but I’m really scared of being seen failing."
    ),
    "Control + fatigue": (
        "I feel like I have to manage everything. When people help, I don’t trust it. "
        "I get exhausted, then I shut down and isolate."
    ),
}

pick = st.sidebar.selectbox("Load an example", ["(none)"] + list(examples.keys()), index=0)
if pick != "(none)":
    st.session_state["user_text"] = examples[pick]

# =========================
# Minimal BitShadow CSS
# =========================
st.markdown(
    """
    <style>
      .block-container { max-width: 900px; padding-top: 2.5rem; }
      h1 { letter-spacing: 0.5px; }
      .muted { color: rgba(255,255,255,0.65); font-size: 0.95rem; }
      .card {
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 14px;
        padding: 16px 18px;
        background: rgba(255,255,255,0.03);
        margin-bottom: 12px;
      }
      .pill {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 999px;
        border: 1px solid rgba(255,255,255,0.12);
        background: rgba(255,255,255,0.04);
        margin-right: 8px;
        margin-bottom: 6px;
        font-size: 0.88rem;
        color: rgba(255,255,255,0.85);
      }
      .speaker { font-weight: 700; }
      .divider { height: 1px; background: rgba(255,255,255,0.10); margin: 18px 0; }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================
# Header
# =========================
st.title("Shadow Tribunal")
st.markdown(
    '<div class="muted">Prototype v0 — architecture first. The monster comes later.</div>',
    unsafe_allow_html=True,
)
st.info(
    "Local-only by default (Ollama on your machine). "
    "No occult/spiritual content. No diagnosis. "
    "Reflective analysis only — not therapy."
)
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# =========================
# Input
# =========================
user_text = st.text_area(
    "Describe a recent decision, conflict, or pattern (5–10 sentences)",
    key="user_text",
    placeholder="Write honestly. Private testing only.",
    height=220,
)

col1, col2 = st.columns([1, 1])
with col1:
    summon = st.button("Summon the Tribunal", type="primary")
with col2:
    compact = st.toggle("Compact mode", value=False)

# =========================
# Helpers
# =========================
def pills(items):
    return "".join([f'<span class="pill">{html.escape(str(item))}</span>' for item in items])


def render_raw_output(text: str):
    safe = html.escape(text).replace("\n", "<br>")
    st.subheader("Shadow Tribunal Output")
    st.markdown(f"<div class='card'>{safe}</div>", unsafe_allow_html=True)


def render_structured(data: dict):
    # ---- PROFILE ----
    st.subheader("Psychological Profile")
    prof = data["profile"]
    st.markdown(
        f"""
        <div class="card">
          <div><span class="speaker">Archetype:</span> {html.escape(prof.get("archetype",""))}</div>
          <div style="margin-top:10px"><span class="speaker">Traits:</span></div>
          <div>{pills(prof.get("traits", []))}</div>
          <div style="margin-top:10px"><span class="speaker">Motivations:</span></div>
          <div>{pills(prof.get("motivations", []))}</div>
          <div style="margin-top:10px"><span class="speaker">Blind Spots:</span></div>
          <div>{pills(prof.get("blind_spots", []))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---- SHADOW ----
    st.subheader("Shadow Persona")
    sh = data["shadow"]
    st.markdown(
        f"""
        <div class="card">
          <div><span class="speaker">{html.escape(sh.get("name",""))}</span> —
          <span class="muted">{html.escape(sh.get("title",""))}</span></div>
          <div style="margin-top:10px">{html.escape(sh.get("description",""))}</div>
          <div style="margin-top:12px"><span class="speaker">Dominant fear:</span>
          {html.escape(sh.get("dominant_fear",""))}</div>
          <div style="margin-top:12px"><span class="speaker">Self-sabotage pattern:</span></div>
          <ul>
            {''.join([f"<li>{html.escape(str(x))}</li>" for x in sh.get("self_sabotage_pattern", [])])}
          </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---- TRIBUNAL ----
    st.subheader("The Tribunal Speaks")
    st.markdown('<div class="card">', unsafe_allow_html=True)
    for line in data.get("tribunal", []):
        speaker = html.escape(str(line.get("speaker", "")))
        text = html.escape(str(line.get("text", "")))
        if compact:
            st.markdown(f"**{speaker}:** {text}")
        else:
            st.markdown(
                f"<div style='margin-bottom:10px'><span class='speaker'>{speaker}:</span> {text}</div>",
                unsafe_allow_html=True,
            )
    st.markdown("</div>", unsafe_allow_html=True)

    # ---- TRAJECTORY ----
    st.subheader("Trajectory Snapshot (If Nothing Changes)")
    st.markdown('<div class="card">', unsafe_allow_html=True)
    for b in data.get("trajectory", {}).get("bullets", []):
        st.markdown(f"- {html.escape(str(b))}")
    st.markdown("</div>", unsafe_allow_html=True)

    # ---- REFLECTION ----
    st.subheader("Reflection")
    st.markdown(
        f"""
        <div class="card">
          {html.escape(str(data.get("reflection", {}).get("text", "")))}
        </div>
        """,
        unsafe_allow_html=True,
    )

# =========================
# Action
# =========================
if summon:
    if not user_text.strip():
        st.warning("Give the Tribunal something to analyze.")
        st.stop()

    # Cooldown / rate limit
    now = time.time()
    last = st.session_state.get("last_run_ts", 0.0)
    if now - last < 8:
        st.warning("Slow down. Give it a moment before summoning again.")
        st.stop()
    st.session_state["last_run_ts"] = now

    with st.spinner("Assembling the tribunal..."):
        data = run_shadow_tribunal_session(user_text, model=model)

    st.session_state["last_result"] = data

    if show_meta and isinstance(data, dict) and "meta" in data:
        st.sidebar.json(data["meta"])

    if isinstance(data, dict) and "raw_output" in data:
        render_raw_output(data["raw_output"])
    else:
        render_structured(data)

    # Export tools
    st.markdown("---")
    colA, colB = st.columns([1, 1])
    with colA:
        st.download_button(
            "Download JSON",
            data=json.dumps(st.session_state.get("last_result", {}), indent=2),
            file_name="shadow_tribunal_result.json",
            mime="application/json",
        )
    with colB:
        st.code("Tip: Switch models in the sidebar, then compare outputs.", language="text")

