"""
Uses Streamlit's own headless AppTest framework to actually run app.py
end-to-end - simulating real button clicks and slider moves - rather than
only testing each panel's data-prep functions in isolation (which the
other test_dashboard_*.py files already do thoroughly).

This is what caught a real methodology trap while building it: with
st.tabs, BOTH tabs' code executes on every script run regardless of which
is visually active, so button indices aren't in visual/tab order - they're
in script execution order. Tests here select buttons by label, not index,
to avoid silently exercising the wrong control (which, for the
"Regenerate eval numbers" button, would mean accidentally triggering a
multi-minute sweep instead of a fast scenario replay).
"""

import pytest
from pathlib import Path
from streamlit.testing.v1 import AppTest

APP_PATH = str(Path(__file__).resolve().parent.parent / "dashboard" / "app.py")


def _get_button(at, label: str):
    matches = [b for b in at.button if b.label == label]
    assert matches, f"no button found with label {label!r}"
    return matches[0]


def test_app_loads_without_exceptions():
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.run()
    assert not at.exception


def test_app_shows_both_tabs():
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.run()
    tab_labels = [t.label for t in at.tabs]
    assert "LIVE MONITOR" in tab_labels
    assert "EVALUATION" in tab_labels


def test_load_and_replay_button_populates_frames():
    at = AppTest.from_file(APP_PATH, default_timeout=60)
    at.run()

    _get_button(at, "Load & Replay").click()
    at.run()

    assert not at.exception
    assert "frames" in at.session_state
    assert len(at.session_state["frames"]) > 0


def test_moving_window_slider_after_replay_has_no_exceptions():
    at = AppTest.from_file(APP_PATH, default_timeout=60)
    at.run()

    _get_button(at, "Load & Replay").click()
    at.run()
    frames = at.session_state["frames"]

    flagged_idx = next(
        (i for i, f in enumerate(frames) if f.pipeline_result["decision"] != "MONITOR"),
        None,
    )
    assert flagged_idx is not None, "expected at least one flagged window in mixed_fraud"

    at.slider(key="window_slider").set_value(flagged_idx)
    at.run()

    assert not at.exception
    assert at.session_state["idx"] == flagged_idx


def test_scenario_selectbox_has_expected_options():
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.run()
    options = at.selectbox[0].options
    assert set(options) == {"mixed_fraud", "normal_day", "flash_sale", "random"}


def test_eval_summary_panel_renders_without_regenerating():
    """The eval tab's content executes even when LIVE MONITOR is the
    'active' tab visually (Streamlit runs both tab bodies every script
    run). This confirms it renders using cached data - fast - without the
    Regenerate button ever being clicked."""
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.run()

    assert not at.exception
    regenerate_button = _get_button(at, "Regenerate eval numbers (takes ~2-3 min)")
    assert regenerate_button is not None  # exists but was never clicked
    assert "eval_detection" in at.session_state
    assert "eval_pnl" in at.session_state