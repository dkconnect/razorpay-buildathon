"""
Preview App — temporary
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from dashboard.replay import load_scenario, replay_scenario
from dashboard.panels.timeline import render_timeline_panel
from dashboard.panels.graph_view import render_graph_panel

st.set_page_config(page_title="Breakpoint — Preview", layout="wide")

st.markdown(
    """
    <style>
    .stApp { background-color: #000000; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("BREAKPOINT — Preview (Steps 1-3)")

scenario = st.selectbox(
    "Scenario", ["normal_day", "flash_sale", "mixed_fraud", "random"]
)
seed = None
if scenario == "random":
    seed = st.number_input("Seed", value=4242, step=1)

if st.button("Load & Replay"):
    with st.spinner("Replaying scenario through the pipeline..."):
        txs = load_scenario(scenario, seed=seed)
        frames = replay_scenario(txs)
    st.session_state["frames"] = frames
    st.session_state["idx"] = 0

if "frames" in st.session_state:
    frames = st.session_state["frames"]

    render_timeline_panel(frames)

    st.markdown("---")
    idx = st.slider("Window", 0, len(frames) - 1, st.session_state.get("idx", 0))
    st.session_state["idx"] = idx

    frame = frames[idx]
    col1, col2 = st.columns([1, 1])
    with col1:
        render_graph_panel(frame)
    with col2:
        st.markdown("#### WINDOW DETAIL")
        st.write(f"**{frame.window_label}**")
        st.write(f"Decision: `{frame.pipeline_result['decision']}`")
        st.json(frame.pipeline_result.get("risk_assessment", {}))
else:
    st.info("Pick a scenario and click 'Load & Replay' to begin.")