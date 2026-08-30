"""
Global page-chrome styling only (background, fonts, buttons, tabs,
sliders). Individual panels (timeline.py, graph_view.py, decision.py,
eval_summary.py) already define their own matching color constants for
their own charts/badges - this file doesn't touch those, only the
Streamlit UI chrome around them, to avoid re-touching already-tested
panel code this late.
"""

BG_COLOR = "#000000"
PANEL_BG = "#0a0a0a"
BORDER_COLOR = "#1a1a1a"
TEXT_COLOR = "#e0e0e0"
MUTED_COLOR = "#888888"
ACCENT_CYAN = "#00F0FF"
FONT_FAMILY = "'JetBrains Mono', 'Consolas', monospace"

TERMINAL_CSS = f"""
<style>
.stApp {{
    background-color: {BG_COLOR};
}}
html, body, [class*="css"] {{
    font-family: {FONT_FAMILY} !important;
}}
h1, h2, h3, h4, h5 {{
    color: {ACCENT_CYAN} !important;
    letter-spacing: 0.5px;
}}
[data-testid="stMetricValue"] {{
    color: {ACCENT_CYAN} !important;
    font-family: {FONT_FAMILY} !important;
}}
[data-testid="stMetricLabel"] {{
    color: {MUTED_COLOR} !important;
}}
.stButton > button {{
    background-color: {BG_COLOR};
    color: {ACCENT_CYAN};
    border: 1px solid {ACCENT_CYAN};
    border-radius: 3px;
    font-family: {FONT_FAMILY};
}}
.stButton > button:hover {{
    background-color: {ACCENT_CYAN};
    color: {BG_COLOR};
}}
.stTabs [data-baseweb="tab-list"] {{
    border-bottom: 1px solid {BORDER_COLOR};
}}
.stTabs [aria-selected="true"] {{
    color: {ACCENT_CYAN} !important;
}}
[data-testid="stExpander"] {{
    background-color: {PANEL_BG};
    border: 1px solid {BORDER_COLOR};
}}
.stSlider [data-baseweb="slider"] div div div {{
    background-color: {ACCENT_CYAN} !important;
}}
[data-testid="stTable"] {{
    font-family: {FONT_FAMILY};
}}
</style>
"""


def inject_terminal_theme(st_module) -> None:
    st_module.markdown(TERMINAL_CSS, unsafe_allow_html=True)