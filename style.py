import base64
from functools import lru_cache
from pathlib import Path
from textwrap import dedent
from urllib.parse import quote

import streamlit as st


def _render_html(markup: str):
    """Render HTML safely without Markdown code-block parsing."""
    markup = dedent(markup).strip()
    html_renderer = getattr(st, "html", None)
    if html_renderer is not None:
        html_renderer(markup)
    else:
        st.markdown(markup, unsafe_allow_html=True)


# ============================================================
# BRAND ASSETS
# ============================================================

ASSETS_DIR = Path(__file__).resolve().parent / "assets"


@lru_cache(maxsize=None)
def asset_data_uri(filename: str) -> str:
    """Return an asset image as a base64 data URI ("" if it is missing)."""
    try:
        data = (ASSETS_DIR / filename).read_bytes()
    except OSError:
        return ""
    return "data:image/png;base64," + base64.b64encode(data).decode("ascii")


def _brand_logo_html(kind: str = "full") -> str:
    """Logo element (CSS background based so the image is embedded once)."""
    if kind == "mark":
        return '<span class="inaiba-logo-mark" role="img" aria-label="INAIBA"></span>'
    return '<span class="inaiba-logo-full" role="img" aria-label="INAIBA"></span>'


# Flowing gradient wave used as the hero artwork (matches the reference).
_WAVE_SVG = """<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 900 420' preserveAspectRatio='xMaxYMid slice'>
<defs>
<linearGradient id='a' x1='0' y1='1' x2='1' y2='0'>
<stop offset='0' stop-color='#6D28D9' stop-opacity='.0'/>
<stop offset='.35' stop-color='#7C3AED' stop-opacity='.85'/>
<stop offset='.7' stop-color='#3B82F6' stop-opacity='.9'/>
<stop offset='1' stop-color='#22D3EE' stop-opacity='.95'/>
</linearGradient>
<linearGradient id='b' x1='0' y1='1' x2='1' y2='0'>
<stop offset='0' stop-color='#4C1D95' stop-opacity='0'/>
<stop offset='.5' stop-color='#A855F7' stop-opacity='.55'/>
<stop offset='1' stop-color='#38BDF8' stop-opacity='.6'/>
</linearGradient>
<linearGradient id='c' x1='0' y1='0' x2='1' y2='1'>
<stop offset='0' stop-color='#22D3EE' stop-opacity='.0'/>
<stop offset='.6' stop-color='#22D3EE' stop-opacity='.75'/>
<stop offset='1' stop-color='#C084FC' stop-opacity='.2'/>
</linearGradient>
<filter id='f' x='-20%' y='-20%' width='140%' height='140%'><feGaussianBlur stdDeviation='9'/></filter>
<filter id='g'><feGaussianBlur stdDeviation='1.1'/></filter>
</defs>
<g filter='url(#f)'>
<path d='M330 420 C 470 330, 520 150, 650 150 C 760 150, 790 60, 900 0 L 900 420 Z' fill='url(#a)' opacity='.55'/>
</g>
<path d='M300 420 C 440 340, 500 180, 640 170 C 750 162, 800 80, 900 40 L 900 420 Z' fill='url(#b)' opacity='.55'/>
<g fill='none' stroke-linecap='round'>
<path d='M290 420 C 440 330, 500 170, 640 160 C 760 152, 810 70, 900 30' stroke='url(#c)' stroke-width='2.2' filter='url(#g)'/>
<path d='M330 420 C 470 350, 530 200, 660 190 C 770 182, 820 110, 900 82' stroke='url(#c)' stroke-width='1.6' opacity='.8'/>
<path d='M380 420 C 500 360, 560 230, 680 222 C 780 214, 830 150, 900 128' stroke='url(#c)' stroke-width='1.3' opacity='.6'/>
<path d='M430 420 C 540 372, 590 260, 700 252 C 790 246, 840 196, 900 176' stroke='url(#c)' stroke-width='1' opacity='.45'/>
<path d='M480 420 C 580 380, 620 290, 720 282 C 800 276, 850 240, 900 222' stroke='url(#c)' stroke-width='.9' opacity='.35'/>
</g>
</svg>"""

WAVE_DATA_URI = "data:image/svg+xml;utf8," + quote(_WAVE_SVG.replace("\n", ""))


# ============================================================
# COLORS  (INAIBA dark premium palette)
# Legacy key names are preserved so every module keeps working;
# only the values changed.
# ============================================================

COLORS = {

    # Brand
    "PRIMARY": "#4F8CFF",
    "PRIMARY_DARK": "#8FB4FF",
    "PRIMARY_DEEP": "#1E3A8A",
    "PRIMARY_LIGHT": "#13224F",
    "SECONDARY": "#7C3AED",
    "ACCENT": "#22D3EE",
    "VIOLET": "#A78BFA",

    # Semantic
    "SUCCESS": "#34D399",
    "SUCCESS_LIGHT": "rgba(52,211,153,.12)",
    "DANGER": "#F87171",
    "DANGER_LIGHT": "rgba(248,113,113,.12)",
    "WARNING": "#FBBF24",
    "WARNING_LIGHT": "rgba(251,191,36,.12)",
    "INFO": "#5EA1FF",
    "INFO_LIGHT": "rgba(94,161,255,.12)",

    # Typography
    "TEXT_DARK": "#F1F5FF",
    "TEXT_BODY": "#C7D2EC",
    "TEXT_SECONDARY": "#A3B1D1",
    "MUTED": "#8190B5",
    "MUTED_LIGHT": "#64729A",

    # Surfaces
    "WHITE": "#FFFFFF",
    "PAGE_BG": "#070B24",
    "CARD_BG": "#0C1738",
    "CARD_BG_2": "#0F1C45",
    "SOFT_BG": "#101B42",
    "PURPLE_SOFT": "#13224F",

    # Borders
    "BORDER": "rgba(132,160,255,.16)",
    "BORDER_LIGHT": "rgba(132,160,255,.09)",
    "BORDER_STRONG": "rgba(132,160,255,.30)",

    # Sidebar
    "SIDEBAR_BG": "#091129",
    "SIDEBAR_TEXT": "#C7D2EC",
    "SIDEBAR_MUTED": "#8190B5",
    "SIDEBAR_ACTIVE": "rgba(34,211,238,.10)",
    "SIDEBAR_ACTIVE_TEXT": "#FFFFFF",
}


FONT_STACK = (
    '"Inter", "Segoe UI", "Helvetica Neue", Arial, '
    '"Roboto", sans-serif'
)


CHART_PALETTE = [
    "#4F8CFF",
    "#22D3EE",
    "#A78BFA",
    "#34D399",
    "#FBBF24",
    "#F472B6",
    "#60A5FA",
    "#818CF8",
    "#2DD4BF",
    "#FB923C",
]


SEVERITY_COLORS = {
    "Critical": COLORS["DANGER"],
    "Moderate": COLORS["WARNING"],
    "Watch": COLORS["INFO"],
}


# ============================================================
# PAGE CONFIGURATION
# ============================================================

def _page_icon():
    try:
        from PIL import Image
        return Image.open(ASSETS_DIR / "favicon.png")
    except Exception:
        return "I"


def configure_page():

    st.set_page_config(
        page_title="INAIBA | Sales Intelligence",
        page_icon=_page_icon(),
        layout="wide",
        initial_sidebar_state="expanded",
    )


# ============================================================
# GLOBAL THEME CSS
# ============================================================

_THEME_CSS = r"""
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --ia-bg: #070B24;
    --ia-bg-2: #0A1130;
    --ia-sidebar: #091129;
    --ia-card: rgba(14, 25, 62, .78);
    --ia-card-solid: #0C1738;
    --ia-card-2: #101D47;
    --ia-line: rgba(132, 160, 255, .16);
    --ia-line-soft: rgba(132, 160, 255, .09);
    --ia-line-strong: rgba(132, 160, 255, .32);
    --ia-text: #F1F5FF;
    --ia-body: #C7D2EC;
    --ia-sub: #A3B1D1;
    --ia-muted: #8190B5;
    --ia-dim: #64729A;
    --ia-blue: #4F8CFF;
    --ia-cyan: #22D3EE;
    --ia-violet: #A78BFA;
    --ia-green: #34D399;
    --ia-amber: #FBBF24;
    --ia-red: #F87171;
    --ia-grad: linear-gradient(135deg, #22D3EE 0%, #4F8CFF 50%, #8B5CF6 100%);
    --ia-radius: 16px;
    --ia-shadow: 0 14px 40px rgba(0, 0, 0, .34), inset 0 1px 0 rgba(255, 255, 255, .04);
    --ia-font: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", Arial, sans-serif;
}

/* =========================================================
   BASE
   ========================================================= */
html, body, [data-testid="stAppViewContainer"], section[data-testid="stSidebar"],
.stApp, .stApp p, .stApp label, .stApp input, .stApp textarea, .stApp button, .stApp select {
    font-family: var(--ia-font);
}

.stApp,
[data-testid="stApp"],
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
.main {
    color: var(--ia-body);
    background:
        radial-gradient(900px 420px at 88% -6%, rgba(99, 102, 241, .20), transparent 62%),
        radial-gradient(760px 380px at 8% 108%, rgba(34, 211, 238, .08), transparent 60%),
        var(--ia-bg) !important;
}

[data-testid="stHeader"] {
    background: transparent !important;
    box-shadow: none !important;
}
[data-testid="stToolbar"] { opacity: .7; }
[data-testid="stDecoration"] { display: none !important; }

[data-testid="stMainBlockContainer"],
.block-container {
    max-width: 1440px !important;
    padding: 18px clamp(18px, 3vw, 44px) 48px !important;
    overflow-x: hidden;
}

h1, h2, h3, h4, h5, h6 {
    font-family: var(--ia-font) !important;
    color: var(--ia-text) !important;
    letter-spacing: -.02em;
}
h1 { font-size: 27px !important; font-weight: 750 !important; }
h2 { font-size: 22px !important; font-weight: 720 !important; }
h3 { font-size: 18px !important; font-weight: 700 !important; }
h4, h5, h6 { font-weight: 700 !important; }

p, li { color: var(--ia-body); }
a { color: var(--ia-cyan); }
hr { border-color: var(--ia-line-soft) !important; margin: 18px 0; }

.stCaption, [data-testid="stCaptionContainer"] {
    color: var(--ia-muted) !important;
    font-size: 12.5px !important;
}

::selection { background: rgba(79, 140, 255, .35); color: #fff; }

/* thin dark scrollbars */
* { scrollbar-width: thin; scrollbar-color: rgba(132,160,255,.28) transparent; }
::-webkit-scrollbar { width: 9px; height: 9px; }
::-webkit-scrollbar-thumb { background: rgba(132,160,255,.25); border-radius: 8px; }
::-webkit-scrollbar-track { background: transparent; }

/* =========================================================
   MATERIAL ICON SAFETY (keep icon ligature fonts intact)
   ========================================================= */
.material-icons, .material-icons-outlined,
.material-symbols-rounded, .material-symbols-outlined,
[data-testid="stIconMaterial"] {
    font-family: "Material Symbols Rounded", "Material Symbols Outlined",
                 "Material Icons", "Material Icons Outlined" !important;
    font-feature-settings: "liga" !important;
    -webkit-font-feature-settings: "liga" !important;
    -webkit-font-smoothing: antialiased !important;
    letter-spacing: normal !important;
    white-space: nowrap;
}

/* =========================================================
   BRAND LOGO
   ========================================================= */
.inaiba-logo-full, .inaiba-logo-mark {
    display: inline-block;
    flex: none;
    background-repeat: no-repeat;
    background-position: center;
    background-size: contain;
}
.inaiba-logo-full { width: 112px; height: 42px; background-image: url("__LOGO__"); }
.inaiba-logo-mark { width: 38px; height: 33px; background-image: url("__MARK__"); }

/* =========================================================
   SIDEBAR  (icon rail)
   ========================================================= */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0A1333 0%, #070E26 100%) !important;
    border-right: 1px solid var(--ia-line) !important;
    min-width: 76px !important;
    max-width: 76px !important;
    width: 76px !important;
    box-shadow: 8px 0 30px rgba(0, 0, 0, .28) !important;
    z-index: 1000 !important;
}
[data-testid="stSidebar"] > div:first-child { background: transparent !important; padding: 0 !important; }
[data-testid="stSidebarContent"] { padding: 12px 10px 14px !important; overflow-x: hidden !important; }
[data-testid="stSidebarUserContent"] { padding: 0 !important; }

.inaiba-sidebar-brand {
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    gap: 6px; padding: 4px 0 12px; text-align: center;
}
.inaiba-sidebar-brand .inaiba-logo-mark { width: 40px; height: 35px; filter: drop-shadow(0 4px 14px rgba(79,140,255,.45)); }
.inaiba-sidebar-subtitle {
    margin: 0; color: var(--ia-sub); font-size: 8px; font-weight: 800;
    letter-spacing: .18em; text-transform: uppercase;
}
.inaiba-sidebar-rule { height: 1px; margin: 0 6px 10px; background: var(--ia-line); }
.inaiba-sidebar-spacer { height: 8px; }
.inaiba-sidebar-section-label { display: none !important; }

[data-testid="stSidebar"] .stButton { margin: 0 0 5px !important; width: 100% !important; }
[data-testid="stSidebar"] .stButton > button {
    position: relative !important;
    display: flex !important; align-items: center !important; justify-content: center !important;
    width: 100% !important; min-width: 0 !important;
    height: 44px !important; min-height: 44px !important; padding: 0 !important;
    border: 1px solid transparent !important; border-radius: 12px !important;
    background: transparent !important; color: var(--ia-sub) !important;
    box-shadow: none !important;
    transition: background .18s ease, border-color .18s ease, color .18s ease, box-shadow .18s ease !important;
}
/* icon-only rail: labels stay available as tooltips (help=) */
[data-testid="stSidebar"] .stButton > button p,
[data-testid="stSidebar"] .stButton > button [data-testid="stMarkdownContainer"] { display: none !important; }
[data-testid="stSidebar"] .stButton > button [data-testid="stIconMaterial"],
[data-testid="stSidebar"] .stButton > button svg {
    font-size: 21px !important; width: 21px !important; height: 21px !important;
    margin: 0 !important; color: inherit !important;
}
[data-testid="stSidebar"] .stButton > button:hover:not(:disabled) {
    background: rgba(79, 140, 255, .12) !important;
    border-color: var(--ia-line) !important; color: #fff !important;
}
[data-testid="stSidebar"] .stButton > button:disabled { opacity: .38 !important; background: transparent !important; }
[data-testid="stSidebar"] [data-testid="stBaseButton-primary"] {
    background: linear-gradient(135deg, rgba(34,211,238,.16), rgba(79,140,255,.18)) !important;
    border-color: rgba(34, 211, 238, .55) !important;
    color: #fff !important;
    box-shadow: 0 0 0 1px rgba(34,211,238,.10), 0 0 22px rgba(34, 211, 238, .22) !important;
}
[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] button,
[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] button svg { color: var(--ia-sub) !important; }

/* =========================================================
   SHELL HEADER
   ========================================================= */
.inaiba-shell-header {
    display: flex; align-items: center; justify-content: space-between; gap: 22px;
    min-height: 58px; margin: 0 0 24px; padding: 0 0 16px;
    border-bottom: 1px solid var(--ia-line);
}
.inaiba-shell-brand { display: flex; align-items: center; gap: 16px; min-width: 0; }
.inaiba-shell-brand .inaiba-logo-full { width: 104px; height: 40px; }
.inaiba-shell-context { min-width: 0; padding-left: 16px; border-left: 1px solid var(--ia-line); }
.inaiba-shell-eyebrow { color: var(--ia-text); font-size: 11px; font-weight: 800; letter-spacing: .14em; }
.inaiba-shell-product { margin-top: 5px; color: var(--ia-muted); font-size: 11.5px; font-weight: 500; }
.inaiba-shell-meta { display: flex; align-items: center; justify-content: flex-end; gap: 0; min-width: 0; }
.inaiba-meta-item { display: flex; flex-direction: column; min-width: 90px; max-width: 240px; padding: 0 20px; border-left: 1px solid var(--ia-line-soft); }
.inaiba-meta-item:first-child { border-left: 0; }
.inaiba-meta-item span { color: var(--ia-dim); font-size: 9px; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; }
.inaiba-meta-item strong {
    overflow: hidden; margin-top: 4px; color: var(--ia-body); font-size: 11.5px; font-weight: 650;
    text-overflow: ellipsis; white-space: nowrap;
}
.inaiba-status-pill {
    display: inline-flex; align-items: center; gap: 8px; margin-left: 6px; padding: 8px 13px;
    border: 1px solid rgba(52, 211, 153, .45); border-radius: 999px;
    background: rgba(52, 211, 153, .08); color: #6EE7B7;
    font-size: 10.5px; font-weight: 700; white-space: nowrap;
    box-shadow: 0 0 18px rgba(52, 211, 153, .12);
}
.inaiba-status-pill i {
    width: 7px; height: 7px; border-radius: 50%; background: var(--ia-green);
    box-shadow: 0 0 0 3px rgba(52, 211, 153, .18), 0 0 10px rgba(52, 211, 153, .8);
}

/* legacy header (style.render_header) */
.inaiba-header {
    display: flex; justify-content: space-between; align-items: center;
    padding: 17px 22px; margin-bottom: 24px;
    background: var(--ia-card); border: 1px solid var(--ia-line); border-radius: var(--ia-radius);
    box-shadow: var(--ia-shadow);
}
.inaiba-header-title { font-size: 24px; line-height: 1.1; font-weight: 750; color: var(--ia-text); }
.inaiba-header-sub { font-size: 13px; color: var(--ia-muted); margin-top: 5px; }
.inaiba-header-meta { font-size: 12.5px; line-height: 1.5; color: var(--ia-sub); text-align: right; }
.inaiba-status-dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: var(--ia-green); margin-right: 6px; }

/* =========================================================
   PAGE / SECTION HEADINGS
   ========================================================= */
.inaiba-page-hero { margin: 0 0 22px; }
.inaiba-page-kicker {
    display: flex; align-items: center; gap: 9px; margin-bottom: 8px;
    color: var(--ia-cyan); font-size: 10px; font-weight: 800; letter-spacing: .18em; text-transform: uppercase;
}
.inaiba-page-kicker:before { content: ""; width: 20px; height: 2px; border-radius: 99px; background: var(--ia-grad); }
.inaiba-page-heading-row h1 {
    margin: 0 !important; color: var(--ia-text) !important;
    font-size: clamp(26px, 2.6vw, 34px) !important; font-weight: 780 !important;
    letter-spacing: -.035em !important; line-height: 1.12 !important;
}
.inaiba-page-heading-row p {
    max-width: 780px; margin: 8px 0 0 !important; color: var(--ia-sub) !important;
    font-size: 13.5px !important; line-height: 1.6 !important;
}
.inaiba-page-title { font-size: 27px; line-height: 1.2; font-weight: 750; color: var(--ia-text); margin: 0 0 5px; }
.inaiba-page-desc { font-size: 14px; line-height: 1.55; color: var(--ia-sub); margin: 0 0 23px; max-width: 1100px; }

.inaiba-section-heading {
    display: flex; align-items: center; gap: 10px; margin: 28px 0 12px;
    color: var(--ia-text); font-size: 17px; font-weight: 740; letter-spacing: -.015em;
}
.inaiba-section-heading:before { content: ""; width: 4px; height: 18px; border-radius: 8px; background: var(--ia-grad); }
.inaiba-section-title { margin: 26px 0 12px; color: var(--ia-text); font-size: 17px; line-height: 1.3; font-weight: 740; letter-spacing: -.015em; }

/* =========================================================
   FILTER TOOLBAR + FORMS
   ========================================================= */
.inaiba-filter-header {
    display: flex; align-items: center; justify-content: space-between; gap: 15px;
    min-height: 54px; margin: 4px 0 0; padding: 11px 16px;
    border: 1px solid var(--ia-line); border-bottom: 0; border-radius: 14px 14px 0 0;
    background: linear-gradient(180deg, rgba(18, 32, 78, .9), rgba(13, 24, 60, .9));
}
.inaiba-filter-header > div { display: flex; align-items: baseline; gap: 11px; }
.inaiba-filter-kicker { color: var(--ia-cyan); font-size: 9.5px; font-weight: 800; letter-spacing: .16em; }
.inaiba-filter-header strong { color: var(--ia-text); font-size: 12.5px; font-weight: 650; }
.inaiba-filter-count {
    padding: 5px 10px; border: 1px solid var(--ia-line); border-radius: 999px;
    background: rgba(79, 140, 255, .10); color: var(--ia-sub); font-size: 10px; font-weight: 700; white-space: nowrap;
}
[data-testid="stForm"] {
    border: 1px solid var(--ia-line) !important; border-radius: 0 0 14px 14px !important;
    background: rgba(11, 21, 54, .85) !important; padding: 14px 16px 13px !important;
    box-shadow: var(--ia-shadow) !important;
}
[data-testid="stForm"] label, [data-testid="stForm"] [data-testid="stWidgetLabel"] {
    color: var(--ia-sub) !important; font-size: 11px !important; font-weight: 650 !important;
}

/* =========================================================
   INPUT CONTROLS
   ========================================================= */
label, [data-testid="stWidgetLabel"] { color: var(--ia-sub) !important; }
[data-testid="stWidgetLabel"] p { color: var(--ia-sub) !important; font-size: 12.5px; font-weight: 600; }

div[data-baseweb="select"] > div,
[data-testid="stDateInput"] [data-baseweb="input"],
[data-testid="stNumberInput"] [data-baseweb="input"],
[data-testid="stTextInput"] [data-baseweb="input"],
[data-testid="stTextArea"] [data-baseweb="textarea"] {
    min-height: 40px !important;
    background: rgba(8, 15, 42, .92) !important;
    border: 1px solid var(--ia-line) !important;
    border-radius: 10px !important;
    box-shadow: none !important;
    color: var(--ia-text) !important;
}
div[data-baseweb="select"] > div:hover,
[data-testid="stDateInput"] [data-baseweb="input"]:hover,
[data-testid="stNumberInput"] [data-baseweb="input"]:hover,
[data-testid="stTextInput"] [data-baseweb="input"]:hover { border-color: var(--ia-line-strong) !important; }
div[data-baseweb="select"] > div:focus-within,
[data-testid="stDateInput"] [data-baseweb="input"]:focus-within,
[data-testid="stNumberInput"] [data-baseweb="input"]:focus-within,
[data-testid="stTextInput"] [data-baseweb="input"]:focus-within,
[data-testid="stTextArea"] [data-baseweb="textarea"]:focus-within {
    border-color: var(--ia-cyan) !important;
    box-shadow: 0 0 0 3px rgba(34, 211, 238, .14) !important;
}
div[data-baseweb="select"] span, div[data-baseweb="select"] div { color: var(--ia-text) !important; }
div[data-baseweb="select"] input,
[data-testid="stDateInput"] input, [data-testid="stNumberInput"] input,
[data-testid="stTextInput"] input, textarea {
    color: var(--ia-text) !important; background: transparent !important; font-size: 12.5px !important;
}
div[data-baseweb="select"] input, [data-testid="stDateInput"] input { font-size: 12.5px !important; }
div[data-baseweb="select"] svg, [data-testid="stNumberInput"] svg { color: var(--ia-sub) !important; fill: var(--ia-sub) !important; }
[data-testid="stNumberInput"] button { background: rgba(79, 140, 255, .08) !important; color: var(--ia-sub) !important; border-color: var(--ia-line) !important; }

[data-baseweb="tag"] {
    background: rgba(79, 140, 255, .18) !important; color: #DCE7FF !important;
    border-radius: 7px !important; border: 1px solid rgba(79,140,255,.35) !important;
}
[data-baseweb="tag"] span { color: #DCE7FF !important; }

/* dropdown menus / calendars / tooltips */
[data-baseweb="popover"], [data-baseweb="popover"] > div { background: transparent !important; z-index: 999999 !important; }
[data-baseweb="popover"] [data-baseweb="menu"],
[data-baseweb="popover"] ul,
[data-baseweb="calendar"] {
    background: #0E1A45 !important; border: 1px solid var(--ia-line-strong) !important;
    border-radius: 12px !important; box-shadow: 0 18px 50px rgba(0, 0, 0, .55) !important;
}
[data-baseweb="popover"] [role="option"] { color: var(--ia-body) !important; background: transparent !important; font-size: 12.5px; }
[data-baseweb="popover"] [role="option"]:hover,
[data-baseweb="popover"] [aria-selected="true"] { background: rgba(79, 140, 255, .16) !important; color: #fff !important; }
[data-baseweb="calendar"] * { color: var(--ia-body); }
[data-baseweb="tooltip"] [role="tooltip"], [data-testid="stTooltipContent"] {
    background: #0E1A45 !important; color: var(--ia-text) !important;
    border: 1px solid var(--ia-line-strong) !important; border-radius: 8px !important;
}

/* checkbox / radio / toggle / slider */
.stCheckbox label span, .stRadio label span { color: var(--ia-body); }
[data-baseweb="checkbox"] > div:first-child, [data-baseweb="radio"] > div:first-child { border-color: var(--ia-line-strong) !important; background-color: rgba(8,15,42,.9) !important; }
.stCheckbox [aria-checked="true"] + div, [data-baseweb="checkbox"] [aria-checked="true"] { background-color: var(--ia-blue) !important; border-color: var(--ia-blue) !important; }
.stSlider [data-baseweb="slider"] > div > div { background: rgba(132, 160, 255, .22); }
.stSlider [role="slider"] {
    background-color: var(--ia-cyan) !important; border-color: var(--ia-cyan) !important;
    box-shadow: 0 0 0 4px rgba(34, 211, 238, .18) !important;
}
.stProgress > div > div > div > div { background: var(--ia-grad) !important; }
.stSpinner > div { border-top-color: var(--ia-cyan) !important; }

/* =========================================================
   BUTTONS
   ========================================================= */
.stButton > button,
.stFormSubmitButton > button,
[data-testid="stDownloadButton"] > button,
.stDownloadButton > button {
    min-height: 40px !important; padding: 7px 18px;
    border-radius: 10px !important;
    border: 1px solid var(--ia-line-strong) !important;
    background: rgba(79, 140, 255, .08) !important;
    color: var(--ia-text) !important;
    font-size: 12.5px !important; font-weight: 650 !important;
    box-shadow: none !important;
    transition: all .16s ease !important;
}
.stButton > button:hover,
.stFormSubmitButton > button:hover,
[data-testid="stDownloadButton"] > button:hover,
.stDownloadButton > button:hover {
    border-color: rgba(34, 211, 238, .6) !important;
    background: rgba(34, 211, 238, .10) !important;
    color: #fff !important;
    box-shadow: 0 0 20px rgba(34, 211, 238, .14) !important;
}
.stButton > button[data-testid="stBaseButton-primary"],
.stFormSubmitButton > button[data-testid="stBaseButton-primary"],
[data-testid="stDownloadButton"] > button[data-testid="stBaseButton-primary"] {
    border: 1px solid rgba(139, 180, 255, .45) !important;
    background: linear-gradient(135deg, #2563EB 0%, #4F46E5 55%, #7C3AED 100%) !important;
    color: #fff !important;
    box-shadow: 0 8px 22px rgba(79, 70, 229, .35) !important;
}
.stButton > button[data-testid="stBaseButton-primary"]:hover,
.stFormSubmitButton > button[data-testid="stBaseButton-primary"]:hover {
    filter: brightness(1.12);
    box-shadow: 0 10px 28px rgba(79, 70, 229, .5) !important;
}
.stButton > button:disabled, .stDownloadButton > button:disabled,
[data-testid="stDownloadButton"] > button:disabled {
    background: rgba(132,160,255,.05) !important; color: var(--ia-dim) !important;
    border-color: var(--ia-line-soft) !important; box-shadow: none !important; cursor: not-allowed;
}
.stButton > button::before, .stButton > button::after { content: none !important; }

/* =========================================================
   FILE UPLOADER
   ========================================================= */
[data-testid="stFileUploader"] { margin: 0 !important; }
[data-testid="stFileUploaderDropzone"] {
    min-height: 150px !important; box-sizing: border-box !important;
    border: 1.5px dashed rgba(34, 211, 238, .38) !important; border-radius: 16px !important;
    background:
        radial-gradient(420px 160px at 50% 0%, rgba(79, 140, 255, .12), transparent 70%),
        rgba(8, 15, 42, .75) !important;
    transition: all .2s ease !important;
}
[data-testid="stFileUploaderDropzone"]:hover {
    border-color: var(--ia-cyan) !important;
    box-shadow: 0 0 34px rgba(34, 211, 238, .14) !important;
}
[data-testid="stFileUploaderDropzoneInstructions"] { color: var(--ia-sub) !important; }
[data-testid="stFileUploaderDropzoneInstructions"] > div:first-child { color: var(--ia-text) !important; font-weight: 650 !important; }
[data-testid="stFileUploaderDropzoneInstructions"] small, [data-testid="stFileUploader"] small { color: var(--ia-muted) !important; }
[data-testid="stFileUploaderDropzone"] button { border-radius: 9px !important; }
[data-testid="stFileUploaderDropzone"] svg { color: var(--ia-cyan) !important; }
[data-testid="stFileUploaderFile"], [data-testid="stFileUploaderFileName"] { color: var(--ia-text) !important; }

/* =========================================================
   KPI CARDS
   ========================================================= */
.inaiba-kpi-card, .inaiba-kpi {
    position: relative; overflow: hidden; box-sizing: border-box;
    min-height: 118px; padding: 18px 19px 16px;
    border: 1px solid var(--ia-line); border-radius: var(--ia-radius);
    background: linear-gradient(160deg, rgba(20, 35, 84, .88) 0%, rgba(11, 21, 55, .92) 100%);
    box-shadow: var(--ia-shadow);
    transition: border-color .18s ease, transform .18s ease, box-shadow .18s ease;
    white-space: normal; overflow-wrap: anywhere;
}
.inaiba-kpi-card:before, .inaiba-kpi:before {
    content: ""; position: absolute; left: 0; right: 0; top: 0; height: 2px;
    background: var(--ia-grad); opacity: .75;
}
.inaiba-kpi:before { width: auto; bottom: auto; }
.inaiba-kpi-card:hover, .inaiba-kpi:hover {
    border-color: rgba(34, 211, 238, .4); transform: translateY(-2px);
    box-shadow: 0 18px 44px rgba(0, 0, 0, .42), 0 0 28px rgba(34, 211, 238, .08);
}
.inaiba-kpi-label {
    color: var(--ia-muted); font-size: 10px; font-weight: 800; line-height: 1.3;
    letter-spacing: .12em; text-transform: uppercase; margin-bottom: 8px;
}
.inaiba-kpi-value {
    margin-top: 7px; color: var(--ia-text); font-size: clamp(22px, 2.2vw, 30px);
    font-weight: 780; letter-spacing: -.035em; line-height: 1.12;
    overflow-wrap: anywhere; white-space: normal;
}
.inaiba-kpi-delta { display: flex; align-items: center; flex-wrap: wrap; gap: 5px; margin-top: 9px; font-size: 11px; font-weight: 700; }
.inaiba-kpi-delta span { font-size: 12px; }
.inaiba-kpi-delta small { margin-left: 2px; color: var(--ia-dim); font-size: 9.5px; font-weight: 550; }
.delta-up, .inaiba-kpi-delta-up { color: var(--ia-green); }
.delta-down, .inaiba-kpi-delta-down { color: var(--ia-red); }
.delta-flat, .inaiba-kpi-delta-flat { color: var(--ia-muted); }
.inaiba-kpi-delta-up, .inaiba-kpi-delta-down, .inaiba-kpi-delta-flat { margin-top: 8px; font-size: 12px; font-weight: 700; }
.inaiba-kpi-success:before { background: var(--ia-green); }
.inaiba-kpi-warning:before { background: var(--ia-amber); }
.inaiba-kpi-danger:before { background: var(--ia-red); }
.inaiba-kpi-info:before { background: var(--ia-blue); }

/* =========================================================
   GENERIC CARDS / INSIGHTS / ALERTS / BADGES
   ========================================================= */
.inaiba-card {
    min-height: 100%; box-sizing: border-box; padding: 26px;
    border: 1px solid var(--ia-line); border-radius: 18px;
    background: linear-gradient(165deg, rgba(18, 31, 76, .88) 0%, rgba(10, 19, 50, .92) 100%);
    box-shadow: var(--ia-shadow);
}
.inaiba-card-blue {
    background:
        radial-gradient(360px 220px at 100% 100%, rgba(139, 92, 246, .22), transparent 70%),
        linear-gradient(165deg, rgba(18, 31, 76, .9) 0%, rgba(10, 19, 50, .94) 100%);
}
.inaiba-label { margin-bottom: 8px; color: var(--ia-cyan); font-size: 10px; font-weight: 800; letter-spacing: .16em; text-transform: uppercase; }
.inaiba-card h2 { margin: 0; color: var(--ia-text) !important; font-size: 24px !important; line-height: 1.2; font-weight: 750 !important; letter-spacing: -.025em; }
.inaiba-card p { margin: 9px 0 18px; color: var(--ia-sub); font-size: 13px; line-height: 1.6; }
.inaiba-card-title { font-size: 16px; line-height: 1.3; font-weight: 700; color: var(--ia-text); margin-bottom: 11px; }

.inaiba-insight {
    padding: 15px 17px; margin-bottom: 10px;
    background: linear-gradient(160deg, rgba(18, 31, 76, .85), rgba(11, 21, 55, .9));
    border: 1px solid var(--ia-line); border-left: 3px solid var(--ia-cyan); border-radius: 12px;
    box-shadow: var(--ia-shadow);
}
.inaiba-insight-obs { font-weight: 700; color: var(--ia-text); font-size: 14px; line-height: 1.45; }
.inaiba-insight-data { color: var(--ia-body); font-size: 13px; line-height: 1.55; margin-top: 5px; }
.inaiba-insight-impl { color: var(--ia-muted); font-size: 12.5px; line-height: 1.5; margin-top: 5px; }

.inaiba-alert { border-radius: 10px; padding: 12px 15px; margin-bottom: 9px; font-size: 13px; line-height: 1.5; border: 1px solid transparent; border-left: 3px solid; }
.inaiba-alert-critical { background: rgba(248, 113, 113, .10); border-color: rgba(248,113,113,.28); border-left-color: var(--ia-red); color: #FECACA; }
.inaiba-alert-moderate { background: rgba(251, 191, 36, .09); border-color: rgba(251,191,36,.26); border-left-color: var(--ia-amber); color: #FDE68A; }
.inaiba-alert-watch    { background: rgba(94, 161, 255, .10); border-color: rgba(94,161,255,.28); border-left-color: var(--ia-blue); color: #BFDBFE; }
.inaiba-alert-good     { background: rgba(52, 211, 153, .09); border-color: rgba(52,211,153,.26); border-left-color: var(--ia-green); color: #A7F3D0; }

.inaiba-badge { display: inline-block; padding: 4px 9px; border-radius: 999px; font-size: 11px; font-weight: 700; letter-spacing: .15px; border: 1px solid rgba(132,160,255,.2); }

/* data quality + forecast */
.inaiba-quality-card, .inaiba-forecast-card {
    padding: 17px 19px; margin-bottom: 12px;
    background: linear-gradient(160deg, rgba(18, 31, 76, .85), rgba(11, 21, 55, .92));
    border: 1px solid var(--ia-line); border-radius: var(--ia-radius); box-shadow: var(--ia-shadow);
}
.inaiba-forecast-card { border-left: 3px solid var(--ia-blue); }
.inaiba-quality-score-label { font-size: 10.5px; font-weight: 800; color: var(--ia-muted); text-transform: uppercase; letter-spacing: .12em; margin-bottom: 6px; }
.inaiba-quality-score-value, .inaiba-forecast-value { font-size: 26px; font-weight: 760; color: var(--ia-text); letter-spacing: -.02em; }
.inaiba-quality-badge { display: inline-block; font-size: 11px; font-weight: 700; padding: 4px 11px; border-radius: 999px; border: 1px solid transparent; }
.inaiba-quality-ready { background: rgba(52,211,153,.12); color: #6EE7B7; border-color: rgba(52,211,153,.45); }
.inaiba-quality-attention { background: rgba(251,191,36,.12); color: #FCD34D; border-color: rgba(251,191,36,.45); }
.inaiba-quality-not-ready { background: rgba(248,113,113,.12); color: #FCA5A5; border-color: rgba(248,113,113,.45); }
.inaiba-quality-issue-count { font-size: 12.5px; color: var(--ia-sub); margin-top: 6px; }
.inaiba-forecast-model {
    display: inline-block; font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 999px;
    background: rgba(79,140,255,.16); color: #BBD2FF; border: 1px solid rgba(79,140,255,.3); margin-bottom: 8px;
}
.inaiba-forecast-accuracy { font-size: 12.5px; font-weight: 600; color: var(--ia-sub); margin-top: 6px; }
.inaiba-forecast-bounds { font-size: 12px; color: var(--ia-muted); margin-top: 4px; }
.inaiba-forecast-status-ok { color: var(--ia-green) !important; }
.inaiba-forecast-status-watch { color: var(--ia-amber) !important; }
.inaiba-forecast-status-risk { color: var(--ia-red) !important; }

.inaiba-dashboard-note { color: var(--ia-muted); font-size: 12.5px; line-height: 1.5; margin-top: 4px; }
.inaiba-footer {
    display: flex; align-items: center; justify-content: center; gap: 10px;
    font-size: 12px; color: var(--ia-muted); text-align: center;
    padding: 18px 0 6px; margin-top: 28px; border-top: 1px solid var(--ia-line-soft);
}
.inaiba-footer .inaiba-logo-mark { width: 22px; height: 19px; opacity: .9; }

/* =========================================================
   NATIVE STREAMLIT SURFACES
   ========================================================= */
[data-testid="stMetric"] {
    background: linear-gradient(160deg, rgba(18, 31, 76, .85), rgba(11, 21, 55, .92));
    border: 1px solid var(--ia-line); border-radius: 14px; padding: 16px 18px; box-shadow: var(--ia-shadow);
}
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] p { color: var(--ia-muted) !important; font-size: 11.5px !important; font-weight: 700 !important; }
[data-testid="stMetricValue"] { color: var(--ia-text) !important; font-size: 26px !important; font-weight: 750 !important; letter-spacing: -.02em; }
[data-testid="stMetricDelta"] { font-size: 12px !important; font-weight: 700 !important; }

[data-testid="stVerticalBlockBorderWrapper"] {
    background: linear-gradient(165deg, rgba(16, 29, 71, .82), rgba(10, 19, 50, .9)) !important;
    border: 1px solid var(--ia-line) !important;
    border-radius: 16px !important;
    box-shadow: var(--ia-shadow) !important;
}
/* nested bordered wrappers should not double up */
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlockBorderWrapper"] { box-shadow: none !important; }

[data-testid="stPlotlyChart"] { overflow: hidden; border-radius: 12px; }

[data-testid="stDataFrame"], [data-testid="stDataEditor"] {
    border: 1px solid var(--ia-line) !important; border-radius: 12px !important;
    overflow: hidden !important; background: rgba(8, 15, 42, .8) !important;
    box-shadow: var(--ia-shadow);
}

[data-testid="stExpander"] {
    border: 1px solid var(--ia-line) !important; border-radius: 14px !important;
    background: rgba(12, 22, 58, .75) !important;
}
[data-testid="stExpander"] summary { color: var(--ia-text) !important; font-weight: 650 !important; }
[data-testid="stExpander"] summary:hover { color: #fff !important; }

[data-testid="stAlert"] {
    border-radius: 12px; font-size: 13px;
    border: 1px solid var(--ia-line);
    background: rgba(79, 140, 255, .09);
}
[data-testid="stAlert"] p, [data-testid="stAlert"] div { color: var(--ia-text) !important; }

.stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: 1px solid var(--ia-line); }
.stTabs [data-baseweb="tab"] { color: var(--ia-muted); font-size: 13.5px; font-weight: 600; padding: 9px 16px; background: transparent; }
.stTabs [data-baseweb="tab"]:hover { color: #fff; }
.stTabs [aria-selected="true"] { color: #fff !important; font-weight: 700; }
.stTabs [data-baseweb="tab-highlight"] { background: var(--ia-grad) !important; height: 2px !important; }
.stTabs [data-baseweb="tab-border"] { background: transparent !important; }

code, pre { background: rgba(8, 15, 42, .9) !important; color: #BBD2FF !important; border-radius: 8px; }

/* =========================================================
   LAYOUT HELPERS
   ========================================================= */
[data-testid="stVerticalBlock"] { gap: .8rem; }
[data-testid="stHorizontalBlock"] { gap: .9rem; align-items: stretch; flex-wrap: wrap !important; }
[data-testid="column"], [data-testid="stColumn"] { background: transparent; min-width: 0; flex: 1 1 240px; }
[data-testid="stAppViewContainer"] { overflow-x: hidden; }

/* =========================================================
   LANDING PAGE
   ========================================================= */
.inaiba-home { max-width: 1240px; margin: 0 auto; padding: 4px 0 42px; }

.inaiba-hero {
    position: relative; overflow: hidden; isolation: isolate;
    padding: 46px 52px 42px; min-height: 300px;
    border: 1px solid rgba(132, 160, 255, .24); border-radius: 24px;
    background:
        url("__WAVE__") right center / auto 118% no-repeat,
        radial-gradient(620px 300px at 12% 0%, rgba(34, 211, 238, .08), transparent 70%),
        linear-gradient(120deg, #03061A 0%, #060B26 48%, #121647 100%);
    box-shadow: 0 24px 70px rgba(0, 0, 0, .5), 0 0 0 1px rgba(34, 211, 238, .05), inset 0 1px 0 rgba(255,255,255,.05);
}
.inaiba-hero:before {
    content: ""; position: absolute; inset: 0; z-index: -1;
    background:
        linear-gradient(90deg, rgba(3, 6, 26, .92) 0%, rgba(3, 6, 26, .62) 46%, rgba(3, 6, 26, 0) 78%);
}

.inaiba-kicker {
    display: inline-flex; align-items: center; gap: 10px; margin-bottom: 14px;
    color: var(--ia-cyan); font-size: 11px; font-weight: 800; line-height: 1.2; letter-spacing: .18em;
}
.inaiba-kicker:before { content: ""; width: 24px; height: 2px; border-radius: 99px; background: var(--ia-cyan); box-shadow: 0 0 10px rgba(34,211,238,.8); }

.inaiba-hero h1 {
    max-width: 900px; margin: 0; color: #fff !important;
    font-size: clamp(34px, 4.4vw, 56px) !important; line-height: 1.04 !important;
    font-weight: 800 !important; letter-spacing: -.045em !important;
}
.inaiba-hero h1 span {
    background: linear-gradient(90deg, #22D3EE 0%, #4F8CFF 60%, #8B5CF6 100%);
    -webkit-background-clip: text; background-clip: text;
    -webkit-text-fill-color: transparent; color: transparent;
}
.inaiba-hero-copy { max-width: 600px; margin: 18px 0 24px; color: var(--ia-sub); font-size: 15px; line-height: 1.7; }
.inaiba-pills { display: flex; flex-wrap: wrap; gap: 9px; }
.inaiba-pill {
    padding: 8px 14px; border: 1px solid rgba(132, 160, 255, .28); border-radius: 999px;
    background: rgba(10, 19, 50, .7); color: var(--ia-body);
    font-size: 11.5px; font-weight: 600; line-height: 1.2; backdrop-filter: blur(6px);
}
.inaiba-upload-section { margin-top: 18px; }
.inaiba-format { margin-top: 10px; color: var(--ia-muted); font-size: 11.5px; line-height: 1.4; }

.inaiba-benefits { display: grid; gap: 14px; margin-top: 22px; }
.inaiba-benefit { display: grid; grid-template-columns: 36px 1fr; gap: 12px; align-items: start; }
.inaiba-benefit-icon {
    display: flex; align-items: center; justify-content: center; width: 36px; height: 36px; border-radius: 10px;
    background: rgba(79, 140, 255, .14); border: 1px solid rgba(79, 140, 255, .32);
    color: #9FC0FF; font-size: 12px; font-weight: 800;
}
.inaiba-benefit b { display: block; color: var(--ia-text); font-size: 13px; line-height: 1.35; font-weight: 700; }
.inaiba-benefit span { display: block; margin-top: 2px; color: var(--ia-muted); font-size: 11.5px; line-height: 1.45; }

.inaiba-feature {
    padding: 18px; height: 100%; box-sizing: border-box;
    border: 1px solid var(--ia-line); border-radius: 16px;
    background: linear-gradient(165deg, rgba(18, 31, 76, .85), rgba(10, 19, 50, .9));
    box-shadow: var(--ia-shadow); transition: transform .2s ease, border-color .2s ease, box-shadow .2s ease;
}
.inaiba-feature:hover { transform: translateY(-3px); border-color: rgba(34, 211, 238, .4); box-shadow: 0 18px 44px rgba(0,0,0,.42), 0 0 28px rgba(34,211,238,.08); }
.inaiba-feature-mark {
    width: 32px; height: 32px; margin-bottom: 12px; display: flex; align-items: center; justify-content: center;
    border-radius: 9px; background: rgba(34, 211, 238, .12); border: 1px solid rgba(34,211,238,.3);
    color: var(--ia-cyan); font-size: 13px; font-weight: 800;
}
.inaiba-feature b { display: block; color: var(--ia-text); font-size: 13px; line-height: 1.35; font-weight: 700; }
.inaiba-feature span { display: block; margin-top: 5px; color: var(--ia-muted); font-size: 11.5px; line-height: 1.5; }

.inaiba-bottom {
    display: flex; justify-content: space-between; align-items: center; gap: 15px; margin-top: 18px;
    padding: 17px 20px; border: 1px solid var(--ia-line); border-radius: 16px;
    background: linear-gradient(90deg, rgba(16, 29, 71, .85), rgba(10, 19, 50, .85));
}
.inaiba-bottom-lead { display: flex; align-items: center; gap: 14px; min-width: 0; }
.inaiba-bottom-lead .inaiba-logo-mark { width: 30px; height: 26px; }
.inaiba-bottom b { color: var(--ia-text); font-size: 13px; line-height: 1.35; font-weight: 700; }
.inaiba-bottom span { display: block; margin-top: 3px; color: var(--ia-muted); font-size: 11.5px; line-height: 1.4; }
.inaiba-ready {
    padding: 8px 12px; border: 1px solid rgba(34, 211, 238, .45); border-radius: 999px;
    background: rgba(34, 211, 238, .08); color: var(--ia-cyan);
    font-size: 10px; font-weight: 800; letter-spacing: .08em; line-height: 1; white-space: nowrap;
}

/* =========================================================
   RESPONSIVE
   ========================================================= */
@media (max-width: 1100px) {
    [data-testid="column"], [data-testid="stColumn"] { flex: 1 1 45%; }
    .inaiba-shell-header { flex-direction: column; align-items: flex-start; gap: 14px; }
    .inaiba-shell-meta { width: 100%; justify-content: flex-start; flex-wrap: wrap; row-gap: 10px; }
    .inaiba-meta-item:first-child { padding-left: 0; }
    .inaiba-header { flex-direction: column; align-items: flex-start; gap: 10px; }
    .inaiba-header-meta { text-align: left; }
    .inaiba-kpi-card, .inaiba-kpi { min-height: auto; }
}
@media (max-width: 900px) {
    .inaiba-hero { padding: 34px 28px; background-size: auto 100%; }
    .inaiba-hero:before { background: linear-gradient(90deg, rgba(3,6,26,.92) 0%, rgba(3,6,26,.7) 70%, rgba(3,6,26,.45) 100%); }
}
@media (max-width: 760px) {
    [data-testid="stMainBlockContainer"], .block-container { padding: 14px 14px 34px !important; }
    .inaiba-shell-header { margin-bottom: 18px; }
    .inaiba-shell-brand { flex-wrap: wrap; gap: 10px; }
    .inaiba-shell-context { padding-left: 0; border-left: 0; }
    .inaiba-meta-item { min-width: 70px; padding: 0 14px; }
    .inaiba-page-heading-row h1 { font-size: 25px !important; }
    .inaiba-filter-header { align-items: flex-start; flex-direction: column; }
    .inaiba-filter-header > div { flex-direction: column; gap: 3px; }
    [data-testid="stForm"] { padding: 12px !important; }
    .inaiba-bottom { align-items: flex-start; flex-direction: column; }
}
@media (max-width: 640px) {
    [data-testid="column"], [data-testid="stColumn"] { flex: 1 1 100%; }
    .inaiba-hero { padding: 26px 20px; border-radius: 19px; }
    .inaiba-hero h1 { font-size: 36px !important; }
    .inaiba-card { padding: 21px; }
}
@media (max-width: 560px) {
    .inaiba-kpi-card { min-height: 104px; }
    .inaiba-meta-item:nth-child(3) { display: none; }
    .inaiba-status-pill { margin-left: 0; }
}

"""


def _theme_css() -> str:
    return (
        _THEME_CSS
        .replace("__LOGO__", asset_data_uri("inaiba_logo.png"))
        .replace("__MARK__", asset_data_uri("inaiba_mark.png"))
        .replace("__WAVE__", WAVE_DATA_URI)
    )


def inject_global_css():
    """Inject the complete INAIBA dark premium theme (single source of truth)."""
    _render_html("<style>" + _theme_css() + "</style>")


# ============================================================
# HEADER
# ============================================================

def render_header(
    dataset_name: str = None,
    period_label: str = None,
    status: str = None,
):

    left, right = st.columns([3.5, 1.5])

    with left:

        _render_html(
            '<div class="inaiba-header-title">INAIBA</div>',
            )

        _render_html(
            '<div class="inaiba-header-sub">'
            'Enterprise Sales Intelligence & Forecasting'
            '</div>',
            )

    with right:

        if period_label:

            status_html = ""

            if status:

                status_html = (
                    f'<span class="inaiba-status-dot"></span>'
                    f'{status}'
                )

            _render_html(
                f"""
                <div class="inaiba-header-meta">

                    <b>Reporting Period</b><br>

                    {period_label}

                    {f"<br>{status_html}" if status_html else ""}

                </div>
                """,
            )

        elif dataset_name:

            _render_html(
                f"""
                <div class="inaiba-header-meta">

                    <b>Dataset</b><br>

                    {dataset_name}

                </div>
                """,
            )


# ============================================================
# PAGE TITLE
# ============================================================

def render_page_title(
    title: str,
    description: str = "",
):

    _render_html(
        f'<div class="inaiba-page-title">{title}</div>',
    )

    if description:

        _render_html(
            f'<div class="inaiba-page-desc">'
            f'{description}'
            f'</div>',
            )


# ============================================================
# PROFESSIONAL KPI CARD
# ============================================================

def kpi_card(
    label: str,
    value: str,
    delta: str = None,
    delta_direction: str = "flat",
):

    delta_class = {

        "up":
            "inaiba-kpi-delta-up",

        "down":
            "inaiba-kpi-delta-down",

        "flat":
            "inaiba-kpi-delta-flat",

    }.get(
        delta_direction,
        "inaiba-kpi-delta-flat",
    )

    delta_html = ""

    if delta:

        delta_html = (
            f'<div class="{delta_class}">'
            f'{delta}'
            f'</div>'
        )

    _render_html(
        f"""
        <div class="inaiba-kpi">

            <div class="inaiba-kpi-label">
                {label}
            </div>

            <div class="inaiba-kpi-value">
                {value}
            </div>

            {delta_html}

        </div>
        """,
    )


# ============================================================
# SECTION TITLE
# ============================================================

def section_title(text: str):

    _render_html(
        f'<div class="inaiba-section-title">'
        f'{text}'
        f'</div>',
    )


# ============================================================
# ALERT BOX
# ============================================================

def alert_box(
    message: str,
    level: str = "watch",
):

    allowed_levels = {
        "critical",
        "moderate",
        "watch",
        "good",
    }

    if level not in allowed_levels:

        level = "watch"

    _render_html(
        f"""
        <div class="inaiba-alert inaiba-alert-{level}">
            {message}
        </div>
        """,
    )


# ============================================================
# INSIGHT BLOCK
# ============================================================

def insight_block(
    observation: str,
    supporting_data: str,
    implication: str,
):

    _render_html(
        f"""
        <div class="inaiba-insight">

            <div class="inaiba-insight-obs">
                {observation}
            </div>

            <div class="inaiba-insight-data">
                {supporting_data}
            </div>

            <div class="inaiba-insight-impl">
                {implication}
            </div>

        </div>
        """,
    )


# ============================================================
# PLOTLY DEFAULTS
# ============================================================

PLOTLY_LAYOUT_DEFAULTS = dict(

    font=dict(
        family="Inter, Segoe UI, Helvetica Neue, Arial, Roboto, sans-serif",
        color=COLORS["TEXT_BODY"],
        size=12,
    ),

    title=dict(
        font=dict(
            family="Inter, Segoe UI, Helvetica Neue, Arial, Roboto, sans-serif",
            size=18,
            color=COLORS["PRIMARY_DARK"],
        ),

        x=0.01,

        xanchor="left",
    ),

    plot_bgcolor="rgba(0,0,0,0)",

    paper_bgcolor="rgba(0,0,0,0)",

    colorway=CHART_PALETTE,

    margin=dict(
        l=52,
        r=28,
        t=58,
        b=46,
    ),

    legend=dict(
        orientation="h",

        yanchor="bottom",
        y=1.02,

        xanchor="right",
        x=1,

        font=dict(
            family="Inter, Segoe UI, Helvetica Neue, Arial, Roboto, sans-serif",
            size=11,
            color=COLORS["TEXT_BODY"],
        ),
    ),

    hoverlabel=dict(
        bgcolor="#0E1A45",

        font_family="Inter, Segoe UI, Helvetica Neue, Arial, Roboto, sans-serif",

        font_size=12,

        font_color=COLORS["TEXT_DARK"],

        bordercolor=COLORS["BORDER"],
    ),
)


# ============================================================
# PLOTLY FIGURE STYLING
# ============================================================

def style_fig(
    fig,
    title=None,
):

    fig.update_layout(
        **PLOTLY_LAYOUT_DEFAULTS
    )

    if title:

        fig.update_layout(
            title=dict(
                text=title,

                font=dict(
                    family="Inter, Segoe UI, Helvetica Neue, Arial, Roboto, sans-serif",

                    size=18,

                    color=COLORS["PRIMARY_DARK"],
                ),

                x=0.01,

                xanchor="left",
            )
        )

    fig.update_xaxes(

        showgrid=False,

        showline=True,

        linecolor=COLORS["BORDER_STRONG"],

        tickfont=dict(
            family="Inter, Segoe UI, Helvetica Neue, Arial, Roboto, sans-serif",

            size=11,

            color=COLORS["TEXT_SECONDARY"],
        ),

        title_font=dict(
            family="Inter, Segoe UI, Helvetica Neue, Arial, Roboto, sans-serif",

            size=11,

            color=COLORS["TEXT_SECONDARY"],
        ),

    )

    fig.update_yaxes(

        showgrid=True,

        gridcolor=COLORS["BORDER_LIGHT"],

        gridwidth=1,

        zeroline=False,

        showline=False,

        tickfont=dict(
            family="Inter, Segoe UI, Helvetica Neue, Arial, Roboto, sans-serif",

            size=11,

            color=COLORS["TEXT_SECONDARY"],
        ),

        title_font=dict(
            family="Inter, Segoe UI, Helvetica Neue, Arial, Roboto, sans-serif",

            size=11,

            color=COLORS["TEXT_SECONDARY"],
        ),

    )

    return fig


# ============================================================
# DASHBOARD BADGE
# ============================================================

def dashboard_badge(
    label: str,
    level: str = "info",
):
    """
    Small pill-style status badge for use in dashboard
    headers, tables, and cards.

    level: "success" | "warning" | "danger" | "info"
    """

    level_class = {
        "success": (
            "background:" + COLORS["SUCCESS_LIGHT"] + ";"
            "color:" + COLORS["SUCCESS"] + ";"
        ),
        "warning": (
            "background:" + COLORS["WARNING_LIGHT"] + ";"
            "color:" + COLORS["WARNING"] + ";"
        ),
        "danger": (
            "background:" + COLORS["DANGER_LIGHT"] + ";"
            "color:" + COLORS["DANGER"] + ";"
        ),
        "info": (
            "background:" + COLORS["INFO_LIGHT"] + ";"
            "color:" + COLORS["INFO"] + ";"
        ),
    }.get(level, None)

    if level_class is None:
        level_class = (
            "background:" + COLORS["INFO_LIGHT"] + ";"
            "color:" + COLORS["INFO"] + ";"
        )

    _render_html(
        f'<span class="inaiba-badge" style="{level_class}">'
        f'{label}'
        f'</span>',
    )


# ============================================================
# DASHBOARD NOTE
# ============================================================

def dashboard_note(text: str):
    """
    Small muted helper/footnote text for use under charts,
    tables, and KPI groups.
    """

    _render_html(
        f'<div class="inaiba-dashboard-note">{text}</div>',
    )


# ============================================================
# DATA QUALITY HELPERS
# ============================================================

def quality_score_card(
    score,
    status: str = "ready",
    issue_count: int = 0,
):
    """
    status: "ready" | "attention" | "not-ready"
    """

    status_map = {
        "ready": (
            "inaiba-quality-ready",
            "Ready",
        ),
        "attention": (
            "inaiba-quality-attention",
            "Needs Attention",
        ),
        "not-ready": (
            "inaiba-quality-not-ready",
            "Not Ready",
        ),
    }

    badge_class, badge_label = status_map.get(
        status,
        status_map["attention"],
    )

    issue_html = ""

    if issue_count:

        issue_html = (
            f'<div class="inaiba-quality-issue-count">'
            f'{issue_count} issue'
            f'{"s" if issue_count != 1 else ""} found'
            f'</div>'
        )

    _render_html(
        f"""
        <div class="inaiba-quality-card">

            <div class="inaiba-quality-score-label">
                Data Quality Score
            </div>

            <div class="inaiba-quality-score-value">
                {score}
            </div>

            <div style="margin-top:10px;">
                <span class="inaiba-quality-badge {badge_class}">
                    {badge_label}
                </span>
            </div>

            {issue_html}

        </div>
        """,
    )


def quality_badge(status: str = "ready"):
    """
    Standalone badge version of the data-quality status,
    for use inline in tables or alongside other elements.
    """

    status_map = {
        "ready": (
            "inaiba-quality-ready",
            "Ready",
        ),
        "attention": (
            "inaiba-quality-attention",
            "Needs Attention",
        ),
        "not-ready": (
            "inaiba-quality-not-ready",
            "Not Ready",
        ),
    }

    badge_class, badge_label = status_map.get(
        status,
        status_map["attention"],
    )

    _render_html(
        f'<span class="inaiba-quality-badge {badge_class}">'
        f'{badge_label}'
        f'</span>',
    )


# ============================================================
# FORECAST HELPERS
# ============================================================

def forecast_card(
    model_name: str,
    value: str,
    accuracy: str = None,
    bounds: str = None,
    status: str = "ok",
):
    """
    status: "ok" | "watch" | "risk"
    """

    status_class = {
        "ok": "inaiba-forecast-status-ok",
        "watch": "inaiba-forecast-status-watch",
        "risk": "inaiba-forecast-status-risk",
    }.get(status, "inaiba-forecast-status-ok")

    accuracy_html = ""

    if accuracy:

        accuracy_html = (
            f'<div class="inaiba-forecast-accuracy {status_class}">'
            f'{accuracy}'
            f'</div>'
        )

    bounds_html = ""

    if bounds:

        bounds_html = (
            f'<div class="inaiba-forecast-bounds">'
            f'{bounds}'
            f'</div>'
        )

    _render_html(
        f"""
        <div class="inaiba-forecast-card">

            <div class="inaiba-forecast-model">
                {model_name}
            </div>

            <div class="inaiba-forecast-value">
                {value}
            </div>

            {accuracy_html}

            {bounds_html}

        </div>
        """,
    )


# ============================================================
# FOOTER
# ============================================================

def show_footer(text: str = None):

    footer_text = text or (
        "INAIBA | Enterprise Sales Intelligence & Forecasting"
    )

    _render_html(
        f'<div class="inaiba-footer">{_brand_logo_html("mark")}<span>{footer_text}</span></div>',
    )


apply_style = inject_global_css
show_header = render_header


# ============================================================
# ENTERPRISE OVERRIDES
# ============================================================

def inject_enterprise_overrides():
    """Final visual layer. The whole theme now lives in inject_global_css();
    this hook is kept so existing call sites keep working unchanged."""
    c = COLORS
    _render_html(
        f"""
        <style>
        :root {{
            --inaiba-navy: {c["PRIMARY_DEEP"]};
            --inaiba-blue: {c["PRIMARY"]};
            --inaiba-border: {c["BORDER"]};
            --inaiba-text: {c["TEXT_DARK"]};
        }}

        /* Sidebar: readable labels when expanded; native toggle collapses to icons. */
        [data-testid="stSidebar"][aria-expanded="false"] {{
            min-width: 0 !important;
            max-width: 0 !important;
            width: 0 !important;
            border-right: 0 !important;
            overflow: hidden !important;
        }}
        [data-testid="stSidebar"][aria-expanded="true"] {{
            min-width: 244px !important;
            max-width: 244px !important;
            width: 244px !important;
        }}
        [data-testid="stSidebar"] {{
            min-width: 244px !important;
            max-width: 244px !important;
            width: 244px !important;
            transition: width .22s ease, min-width .22s ease, max-width .22s ease;
        }}
        [data-testid="stSidebar"] [data-testid="stSidebarContent"] {{
            padding: 16px 13px 18px !important;
            overflow-x: hidden !important;
        }}
        [data-testid="stSidebar"] .stButton > button {{
            display: flex !important;
            flex-direction: row !important;
            justify-content: flex-start !important;
            align-items: center !important;
            gap: 11px !important;
            width: 100% !important;
            min-height: 43px !important;
            height: auto !important;
            padding: 10px 12px !important;
            border: 1px solid transparent !important;
            border-radius: 11px !important;
            text-align: left !important;
            white-space: normal !important;
            overflow: visible !important;
            background: transparent !important;
            color: #C7D2EC !important;
            box-shadow: none !important;
        }}
        [data-testid="stSidebar"] .stButton > button p,
        [data-testid="stSidebar"] .stButton > button [data-testid="stMarkdownContainer"] {{
            display: block !important;
            width: auto !important;
            white-space: normal !important;
            overflow-wrap: anywhere !important;
            word-break: normal !important;
            line-height: 1.35 !important;
            text-align: left !important;
            margin: 0 !important;
        }}
        [data-testid="stSidebar"] .stButton > button [data-testid="stIconMaterial"] {{
            flex: 0 0 20px !important;
            width: 20px !important;
            height: 20px !important;
            font-size: 20px !important;
            margin: 0 !important;
        }}
        [data-testid="stSidebar"] .stButton > button:hover:not(:disabled) {{
            background: linear-gradient(100deg, rgba(34,211,238,.12), rgba(79,140,255,.10)) !important;
            border-color: rgba(79,140,255,.24) !important;
            color: #FFFFFF !important;
        }}
        [data-testid="stSidebar"] [data-testid="stBaseButton-primary"] {{
            background: linear-gradient(105deg, rgba(34,211,238,.17), rgba(79,140,255,.20)) !important;
            border-color: rgba(34,211,238,.38) !important;
            color: #FFFFFF !important;
            box-shadow: inset 3px 0 0 #22D3EE, 0 6px 18px rgba(0,0,0,.12) !important;
        }}
        .inaiba-sidebar-brand {{
            min-height: 76px !important;
            flex-direction: row !important;
            justify-content: flex-start !important;
            gap: 12px !important;
            padding: 12px 11px 17px !important;
            margin: 0 0 12px !important;
            border: 1px solid rgba(132,160,255,.17) !important;
            border-radius: 16px !important;
            background: linear-gradient(135deg, rgba(20,37,82,.96), rgba(10,17,43,.94)) !important;
            box-shadow: 0 10px 28px rgba(0,0,0,.2), inset 0 1px 0 rgba(255,255,255,.05) !important;
        }}
        .inaiba-sidebar-brand .inaiba-logo-mark {{
            width: 48px !important;
            height: 42px !important;
            padding: 4px !important;
            border-radius: 12px !important;
            background-color: rgba(255,255,255,.045) !important;
            filter: drop-shadow(0 3px 10px rgba(79,140,255,.35)) !important;
        }}
        .inaiba-sidebar-subtitle {{
            color: #F1F5FF !important;
            font-size: 10px !important;
            letter-spacing: .2em !important;
        }}
        .inaiba-sidebar-rule {{
            margin: 0 5px 13px !important;
            background: linear-gradient(90deg, rgba(34,211,238,.48), rgba(132,160,255,.08)) !important;
        }}
        .inaiba-shell-brand .inaiba-logo-full {{
            width: 112px !important;
            height: 48px !important;
            padding: 7px 10px !important;
            border: 1px solid rgba(132,160,255,.20) !important;
            border-radius: 14px !important;
            background-color: rgba(18,31,69,.75) !important;
            box-shadow: 0 8px 24px rgba(0,0,0,.16), inset 0 1px 0 rgba(255,255,255,.05) !important;
        }}
        @media (max-width: 760px) {{
            [data-testid="stSidebar"] {{ min-width: 230px !important; max-width: 230px !important; width: 230px !important; }}
            .inaiba-shell-header {{ flex-wrap: wrap !important; gap: 12px !important; }}
            .inaiba-shell-meta {{ flex-wrap: wrap !important; justify-content: flex-start !important; }}
            .inaiba-meta-item {{ padding: 6px 10px !important; }}
        }}

        /* Strict icon-only sidebar: labels never appear or wrap into letters. */
        [data-testid="stSidebar"],
        [data-testid="stSidebar"][aria-expanded="false"],
        [data-testid="stSidebar"][aria-expanded="true"],
        [data-testid="stSidebar"]:hover,
        [data-testid="stSidebar"][aria-expanded="false"]:hover,
        [data-testid="stSidebar"][aria-expanded="true"]:hover {{
            width: 76px !important;
            min-width: 76px !important;
            max-width: 76px !important;
            overflow-x: hidden !important;
            transition: none !important;
        }}
        [data-testid="stSidebar"] [data-testid="stSidebarContent"] {{
            overflow-x: hidden !important;
            padding: 14px 10px 18px !important;
        }}
        [data-testid="stSidebar"] .stButton {{
            width: 100% !important;
            margin: 0 0 5px !important;
        }}
        [data-testid="stSidebar"] .stButton > button {{
            display: flex !important;
            flex-direction: row !important;
            align-items: center !important;
            justify-content: center !important;
            gap: 0 !important;
            width: 100% !important;
            min-width: 0 !important;
            min-height: 44px !important;
            height: 44px !important;
            padding: 0 !important;
            white-space: nowrap !important;
            overflow: hidden !important;
        }}
        [data-testid="stSidebar"] .stButton > button p,
        [data-testid="stSidebar"] .stButton > button [data-testid="stMarkdownContainer"],
        [data-testid="stSidebar"] .stButton > button span:not([data-testid="stIconMaterial"]),
        [data-testid="stSidebar"] .stButton > button [data-testid="stTooltipContent"] {{
            display: none !important;
            visibility: hidden !important;
            width: 0 !important;
            max-width: 0 !important;
            overflow: hidden !important;
        }}
        [data-testid="stSidebar"] .stButton > button [data-testid="stIconMaterial"],
        [data-testid="stSidebar"] .stButton > button svg {{
            display: inline-flex !important;
            flex: 0 0 21px !important;
            width: 21px !important;
            min-width: 21px !important;
            height: 21px !important;
            font-size: 21px !important;
            margin: 0 !important;
        }}
        .inaiba-sidebar-brand {{
            min-height: 62px !important;
            flex-direction: column !important;
            align-items: center !important;
            justify-content: center !important;
            gap: 6px !important;
            padding: 8px 0 12px !important;
            margin: 0 0 10px !important;
        }}
        .inaiba-sidebar-brand .inaiba-logo-mark {{
            width: 42px !important;
            height: 36px !important;
            padding: 2px !important;
        }}
        .inaiba-sidebar-subtitle {{ display: none !important; visibility: hidden !important; }}
        [data-testid="stSidebar"]:hover {{ box-shadow: 8px 0 30px rgba(0,0,0,.28) !important; }}
        @media (max-width: 760px) {{
            [data-testid="stSidebar"],
            [data-testid="stSidebar"]:hover {{
                width: 76px !important;
                min-width: 76px !important;
                max-width: 76px !important;
            }}
        }}
        /* Final shell update: replace the sidebar with a premium horizontal nav. */
        [data-testid="stSidebar"],
        [data-testid="stSidebarCollapsedControl"],
        [data-testid="stSidebarCollapseButton"],
        button[kind="header"] {{
            display: none !important;
            visibility: hidden !important;
            width: 0 !important;
            min-width: 0 !important;
            max-width: 0 !important;
        }}
        [data-testid="stAppViewContainer"] > .main,
        [data-testid="stMain"] {{
            margin-left: 0 !important;
            width: 100% !important;
        }}
        [data-testid="stMainBlockContainer"], .block-container {{
            max-width: 1720px !important;
            padding-left: clamp(18px, 2.5vw, 46px) !important;
            padding-right: clamp(18px, 2.5vw, 46px) !important;
        }}
        [class*="st-key-inaiba-horizontal-nav"] {{
            position: relative !important;
            margin: -7px 0 23px !important;
            padding: 10px !important;
            border: 1px solid rgba(132,160,255,.20) !important;
            border-radius: 17px !important;
            background: linear-gradient(110deg, rgba(13,25,60,.96), rgba(16,28,69,.88)) !important;
            box-shadow: 0 12px 30px rgba(0,0,0,.18), inset 0 1px 0 rgba(255,255,255,.035) !important;
        }}
        [class*="st-key-inaiba-horizontal-nav"] [data-testid="stHorizontalBlock"] {{
            gap: 9px !important;
        }}
        [class*="st-key-inaiba-horizontal-nav"] .stButton {{
            width: 100% !important;
            margin: 0 !important;
        }}
        [class*="st-key-inaiba-horizontal-nav"] .stButton > button {{
            min-height: 43px !important;
            height: auto !important;
            padding: 9px 11px !important;
            justify-content: center !important;
            gap: 7px !important;
            white-space: nowrap !important;
            border: 1px solid rgba(132,160,255,.17) !important;
            border-radius: 11px !important;
            background: rgba(7,14,39,.62) !important;
            color: #B9C8E8 !important;
            font-size: 11px !important;
            font-weight: 650 !important;
            box-shadow: none !important;
            transition: all .18s ease !important;
        }}
        [class*="st-key-inaiba-horizontal-nav"] .stButton > button:hover:not(:disabled) {{
            background: linear-gradient(105deg, rgba(34,211,238,.12), rgba(79,140,255,.16)) !important;
            border-color: rgba(34,211,238,.42) !important;
            color: #FFFFFF !important;
            transform: translateY(-1px) !important;
        }}
        [class*="st-key-inaiba-horizontal-nav"] [data-testid="stBaseButton-primary"] {{
            background: linear-gradient(110deg, rgba(34,211,238,.18), rgba(79,140,255,.22)) !important;
            border-color: rgba(34,211,238,.48) !important;
            color: #FFFFFF !important;
            box-shadow: 0 5px 16px rgba(34,211,238,.08), inset 0 1px 0 rgba(255,255,255,.07) !important;
        }}
        [class*="st-key-inaiba-horizontal-nav"] .stButton > button:disabled {{
            opacity: .72 !important;
            cursor: default !important;
        }}
        [class*="st-key-inaiba-horizontal-nav-actions"] {{ margin: -11px 0 18px !important; }}
        [class*="st-key-inaiba-horizontal-nav-actions"] .stButton > button {{
            min-height: 37px !important; border-radius: 10px !important;
            background: rgba(16,29,71,.78) !important; border: 1px solid rgba(132,160,255,.20) !important;
            color: #C7D2EC !important; font-size: 11px !important;
        }}
        @media (max-width: 900px) {{
            [class*="st-key-inaiba-horizontal-nav"] {{ padding: 8px !important; }}
            [class*="st-key-inaiba-horizontal-nav"] .stButton > button {{
                white-space: normal !important; line-height: 1.25 !important; padding: 8px 5px !important;
                font-size: 10px !important;
            }}
        }}
        </style>
        """
    )
