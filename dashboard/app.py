"""
Assembles all five panels (timeline, graph, decision, audit, eval summary)
into one Streamlit app with a terminal theme, a scenario selector, and a
step-by-step (optionally auto-playing) replay control.

Two tabs:
  LIVE MONITOR — pick a scenario, replay it window by window, watch the
    system detect (or correctly ignore) what's happening in real time.
  EVALUATION — the closing beat: detection curve, confusion matrix, ₹ P&L,
    pulled from Day 6's real numbers.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from dashboard.theme import inject_terminal_theme
from dashboard.replay import load_scenario, replay_scenario, get_audit_logger
from dashboard.panels.timeline import render_timeline_panel
from dashboard.panels.graph_view import render_graph_panel
from dashboard.panels.decision import render_decision_panel, render_audit_panel
from dashboard.panels.eval_summary import render_eval_summary_panel

st.set_page_config(page_title="Breakpoint", layout="wide", page_icon="◆")
inject_terminal_theme(st)

st.markdown("# BREAKPOINT")
st.caption("Regime-aware fraud detection — changepoint detection · graph ring linkage · EVT/CVaR exposure · cost-sensitive decisions")

tab_monitor, tab_eval = st.tabs(["LIVE MONITOR", "EVALUATION"])

with tab_monitor:
    with st.sidebar:
        st.markdown("### SCENARIO")
        scenario = st.selectbox(
            "Scenario", ["mixed_fraud", "normal_day", "flash_sale", "random"]
        )
        seed = None
        if scenario == "random":
            seed = st.number_input("Seed", value=4242, step=1)

        if st.button("Load & Replay", width="stretch"):
            with st.spinner("Replaying scenario through the pipeline..."):
                txs = load_scenario(scenario, seed=seed)
                frames = replay_scenario(txs)
            st.session_state["frames"] = frames
            st.session_state["idx"] = 0
            st.session_state["playing"] = False

        if "frames" in st.session_state:
            st.markdown("---")
            st.markdown("### PLAYBACK")
            playing = st.checkbox("Auto-play", value=st.session_state.get("playing", False))
            st.session_state["playing"] = playing
            speed = st.slider("Speed (sec/window)", 0.1, 2.0, 0.5, step=0.1)

    if "frames" not in st.session_state:
        st.info("Pick a scenario in the sidebar and click 'Load & Replay' to begin.")
    else:
        frames = st.session_state["frames"]
        max_idx = len(frames) - 1

        render_timeline_panel(frames)

        st.markdown("---")
        idx = st.slider("Window", 0, max_idx, st.session_state.get("idx", 0), key="window_slider")
        st.session_state["idx"] = idx

        frame = frames[idx]
        st.markdown(f"**{frame.window_label}**  ·  window {idx + 1}/{len(frames)}")

        col1, col2 = st.columns([1, 1])
        with col1:
            render_graph_panel(frame)
        with col2:
            render_decision_panel(frame)

        st.markdown("---")
        audit_logger = get_audit_logger()
        render_audit_panel(audit_logger)

        # Auto-play: advance one window, then trigger a rerun after a short
        # delay. Stops itself at the last window rather than looping.
        if st.session_state.get("playing", False):
            if idx < max_idx:
                time.sleep(speed)
                st.session_state["idx"] = idx + 1
                st.rerun()
            else:
                st.session_state["playing"] = False

with tab_eval:
    render_eval_summary_panel()