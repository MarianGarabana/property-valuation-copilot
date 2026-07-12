import sys
from pathlib import Path

import polars as pl
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[1]
for _p in (
    str(REPO_ROOT),
    str(REPO_ROOT / "models" / "explain"),
    str(REPO_ROOT / "models" / "tabular"),
):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from etl.schema import PROCESSED_PARQUET_PATH, DATA_LABEL  # noqa: E402

CAVEAT_TEXT = (
    "Data is idealista18: 2018 Madrid asking-price listings. This is a historical "
    "prototype, not a live market feed."
)

_CSS = """
<style>
:root {
    --accent: #B72683;
    --accent-hover: #93195F;
    --accent-on-dark: #E8659F;
    --ink: #24262B;
    --ink-soft: #5B5D63;
    --bg: #F6F5F3;
    --surface: #FFFFFF;
    --border: #E4E1DC;
    --sidebar-bg: #22222A;
    --sidebar-item-bg: #2C2C36;
    --sidebar-text: #ECEAE6;
    --sidebar-text-soft: #A9A6A0;
    --caveat-bg: #FBF1DC;
    --caveat-text: #24262B;
    --font-sans: -apple-system, "Segoe UI", "Source Sans Pro", Roboto, Helvetica, Arial, sans-serif;
    --space-1: 4px;
    --space-2: 8px;
    --space-3: 12px;
    --space-4: 16px;
    --space-5: 24px;
    --space-6: 32px;
}

.stApp { background-color: var(--bg); font-family: var(--font-sans); }

/* Sidebar: restrained dark panel, one accent color reused everywhere */
[data-testid="stSidebar"] {
    background-color: var(--sidebar-bg);
}
[data-testid="stSidebar"] * {
    color: var(--sidebar-text) !important;
    font-family: var(--font-sans);
}
[data-testid="stSidebarNav"] {
    display: none;
}
[data-testid="stPageLink"] {
    background-color: var(--sidebar-item-bg);
    border-radius: 6px;
    margin-bottom: var(--space-1);
    padding: var(--space-2) var(--space-3);
    transition: background-color 160ms ease-out;
}
[data-testid="stPageLink"]:hover {
    background-color: var(--accent);
}
[data-testid="stPageLink"] p {
    font-size: 0.86rem;
    font-weight: 500;
}

/* Headings and body copy: one ink color, one soft-ink color, everywhere */
h1, h2, h3 { color: var(--ink); font-family: var(--font-sans); font-weight: 700; }
h1 { letter-spacing: -0.01em; }
p, span, label, div { font-family: var(--font-sans); }
hr { border-color: var(--border); margin: var(--space-4) 0; }

/* Buttons: single accent, consistent press feedback */
.stButton > button {
    background-color: var(--accent);
    color: #FFFFFF;
    border-radius: 8px;
    border: none;
    font-weight: 600;
    transition: background-color 160ms ease-out, transform 120ms ease-out;
}
.stButton > button:hover {
    background-color: var(--accent-hover);
    color: #FFFFFF;
}
.stButton > button:active {
    transform: scale(0.97);
}

[data-testid="stExpander"] {
    background-color: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
}

/* Caveat banner: the 2018-prototype notice, same visual language on every page */
.caveat-banner {
    background-color: var(--caveat-bg);
    border-left: 4px solid var(--accent);
    border-radius: 8px;
    padding: var(--space-3) var(--space-4);
    margin-bottom: var(--space-5);
    color: var(--caveat-text);
    font-size: 0.88rem;
    line-height: 1.5;
}
.caveat-banner .caveat-eyebrow {
    display: block;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--accent);
    margin-bottom: 2px;
}

/* Metric cards: the one card style used for every figure in the app */
.wrap-metric {
    background-color: var(--surface);
    border: 1px solid var(--border);
    border-left: 4px solid var(--accent);
    border-radius: 8px;
    padding: var(--space-3) var(--space-4);
    margin-bottom: var(--space-2);
}
.wrap-metric .wrap-metric-label {
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.02em;
    text-transform: uppercase;
    color: var(--ink-soft);
}
.wrap-metric .wrap-metric-value {
    font-size: 1.4rem;
    font-weight: 700;
    color: var(--ink);
    white-space: normal;
    overflow-wrap: break-word;
    word-break: break-word;
    line-height: 1.3;
    margin-top: 2px;
}
.wrap-metric .wrap-metric-delta {
    font-size: 0.8rem;
    color: var(--ink-soft);
    white-space: normal;
    overflow-wrap: break-word;
    margin-top: 2px;
}

.chart-header-title {
    font-weight: 600;
    font-size: 1.05rem;
    color: var(--ink);
}
.chart-header-info {
    font-size: 0.8rem;
    color: var(--accent);
    cursor: help;
}

/* Streamlit alert boxes (st.info / st.warning) share the caveat's visual
   language, so every disclaimer on every page reads as one family. */
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentWarning"]) {
    background-color: var(--caveat-bg) !important;
    border-left: 4px solid var(--accent) !important;
    border-radius: 8px;
}
[data-testid="stAlertContentWarning"] * {
    color: var(--caveat-text) !important;
}
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentInfo"]) {
    background-color: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-left: 4px solid var(--ink-soft) !important;
    border-radius: 8px;
}
[data-testid="stAlertContentInfo"] * {
    color: var(--ink) !important;
}
</style>
"""


def apply_css():
    st.markdown(_CSS, unsafe_allow_html=True)


def render_sidebar(df):
    with st.sidebar:
        st.markdown(
            """
            <div style='text-align:center; padding:12px 0 8px 0;'>
                <span style='font-size:2.2rem;'>🏠</span>
                <h2 style='margin:4px 0 0 0; color:#E8659F; font-size:1.0rem; font-weight:700;'>
                    Property Valuation Copilot
                </h2>
                <p style='font-size:0.73rem; color:#A9A6A0; margin:2px 0 0 0;'>
                    IE University · MBDS · 2026
                </p>
            </div>
            <hr style='border-color:#A9A6A0; opacity:0.25; margin:8px 0 16px 0;'>
            """,
            unsafe_allow_html=True,
        )

        st.page_link("Home.py", label="Home")
        st.page_link("pages/1_Market_Explorer.py", label="Market Explorer")
        st.page_link("pages/2_Value_Estimator.py", label="Value Estimator")
        st.page_link("pages/3_Comparables_Map.py", label="Comparables Map")
        st.page_link("pages/4_Energy_ESG.py", label="Energy / ESG")
        st.page_link("pages/5_Copilot_Report.py", label="Copilot Report")
        st.page_link("pages/6_CNN_Demo.py", label="CNN Demo (dropped feature)")

        st.markdown(
            f"""
            <hr style='border-color:#A9A6A0; opacity:0.25; margin:16px 0 8px 0;'>
            <p style='font-size:0.70rem; color:#A9A6A0; text-align:center; line-height:1.6;'>
                Dataset: idealista18<br>
                n = {len(df):,} listings<br>
                Built with Streamlit · LightGBM · SHAP · LangGraph
            </p>
            """,
            unsafe_allow_html=True,
        )


def render_caveat():
    st.markdown(
        f'<div class="caveat-banner">'
        f'<span class="caveat-eyebrow">2018 prototype</span>'
        f"{CAVEAT_TEXT}"
        f"</div>",
        unsafe_allow_html=True,
    )


def chart_header(title, description):
    desc_esc = description.replace('"', "&quot;")
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">'
        f'<span class="chart-header-title">{title}</span>'
        f'<span class="chart-header-info" title="{desc_esc}">&#9432;</span>'
        f"</div>",
        unsafe_allow_html=True,
    )


def render_metric_card(label, value, delta=None):
    delta_html = f'<div class="wrap-metric-delta">{delta}</div>' if delta else ""
    st.markdown(
        f'<div class="wrap-metric">'
        f'<div class="wrap-metric-label">{label}</div>'
        f'<div class="wrap-metric-value">{value}</div>'
        f"{delta_html}"
        f"</div>",
        unsafe_allow_html=True,
    )


@st.cache_data
def load_listings_df():
    return pl.read_parquet(PROCESSED_PARQUET_PATH).to_pandas()


def get_data_label():
    return DATA_LABEL
