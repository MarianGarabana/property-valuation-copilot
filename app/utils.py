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
.stApp { background-color: #F4F4F4; }
[data-testid="stSidebar"] {
    background-color: #E2F46E;
}
[data-testid="stSidebar"] * {
    color: #333333 !important;
}
[data-testid="stMetric"] {
    background-color: #FFFFFF;
    border-left: 4px solid #B72683;
    border-radius: 8px;
    padding: 12px 16px;
}
[data-testid="stMetricLabel"],
[data-testid="stMetricValue"],
[data-testid="stMetricDelta"] {
    color: #333333 !important;
}
h1, h2, h3 { color: #333333; }
hr { border-color: #D9D9D9; }
.stButton > button {
    background-color: #B72683;
    color: #FFFFFF;
    border-radius: 8px;
    border: none;
    font-weight: 600;
}
.stButton > button:hover {
    background-color: #9A1F6E;
    color: #FFFFFF;
}
[data-testid="stExpander"] {
    background-color: #FFFFFF;
    border-radius: 8px;
}
[data-testid="stSidebarNav"] {
    display: none;
}
[data-testid="stPageLink"] {
    background-color: #C8DC58;
    border-radius: 6px;
    margin-bottom: 2px;
}
.caveat-banner {
    background-color: #FFF3CD;
    border-left: 4px solid #B72683;
    border-radius: 8px;
    padding: 10px 16px;
    margin-bottom: 18px;
    color: #333333;
    font-size: 0.88rem;
}
.wrap-metric {
    background-color: #FFFFFF;
    border-left: 4px solid #B72683;
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 8px;
}
.wrap-metric .wrap-metric-label {
    font-size: 0.82rem;
    color: #555555;
}
.wrap-metric .wrap-metric-value {
    font-size: 1.4rem;
    font-weight: 600;
    color: #333333;
    white-space: normal;
    overflow-wrap: break-word;
    word-break: break-word;
    line-height: 1.25;
}
.wrap-metric .wrap-metric-delta {
    font-size: 0.8rem;
    color: #555555;
    white-space: normal;
    overflow-wrap: break-word;
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
                <h2 style='margin:4px 0 0 0; color:#B72683; font-size:1.0rem; font-weight:700;'>
                    Property Valuation Copilot
                </h2>
                <p style='font-size:0.73rem; color:#555555; margin:2px 0 0 0;'>
                    IE University · MBDS · 2026
                </p>
            </div>
            <hr style='border-color:#333333; opacity:0.2; margin:8px 0 16px 0;'>
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
            <hr style='border-color:#333333; opacity:0.2; margin:16px 0 8px 0;'>
            <p style='font-size:0.70rem; color:#555555; text-align:center; line-height:1.6;'>
                Dataset: idealista18<br>
                n = {len(df):,} listings<br>
                Built with Streamlit · LightGBM · SHAP · LangGraph
            </p>
            """,
            unsafe_allow_html=True,
        )


def render_caveat():
    st.markdown(
        f'<div class="caveat-banner"><strong>2018 prototype:</strong> {CAVEAT_TEXT}</div>',
        unsafe_allow_html=True,
    )


def chart_header(title, description):
    desc_esc = description.replace('"', "&quot;")
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:2px;">'
        f'<span style="font-weight:600;font-size:1.05rem;">{title}</span>'
        f'<span title="{desc_esc}" style="font-size:0.8rem;color:#B72683;">ⓘ</span>'
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
