import streamlit as st
from utils import apply_css, render_sidebar, render_caveat, load_listings_df, get_data_label

st.set_page_config(page_title="Property Valuation Copilot", page_icon="🏠", layout="wide")
apply_css()

df = load_listings_df()
render_sidebar(df)

st.title("Explainable Property Valuation Copilot")
st.caption("Marian Garabana · MBDS Student at IE University · IE University 2026")
render_caveat()
st.divider()

st.markdown(
    f"An explainable Automated Valuation Model for Madrid residential property, built on "
    f"**{len(df):,} processed idealista18 listings**. Every value estimate ships with its "
    "confidence range and SHAP drivers, comparable properties are inspectable on a map, "
    "an energy proxy flag carries its observed value impact, and a LangGraph copilot writes "
    "the valuation narrative from those same figures. Use the sidebar to explore each page."
)

st.markdown("### Pages")

col1, col2 = st.columns(2)

with col1:
    st.markdown(
        """
        <div style="background:#FFFFFF; border-left:4px solid #B72683; border-radius:8px; padding:16px 20px; margin-bottom:12px;">
            <div style="font-weight:700; font-size:1rem; color:#333333;">📈 Market Explorer</div>
            <div style="font-size:0.85rem; color:#555555; margin-top:4px;">
                Browse and filter the processed listings. Price and EUR/m2 distributions, barrio-level views.
            </div>
        </div>
        <div style="background:#FFFFFF; border-left:4px solid #B72683; border-radius:8px; padding:16px 20px; margin-bottom:12px;">
            <div style="font-weight:700; font-size:1rem; color:#333333;">🏷️ Value Estimator</div>
            <div style="font-size:0.85rem; color:#555555; margin-top:4px;">
                Select a listing or enter a property. Estimate, confidence range, and SHAP drivers.
            </div>
        </div>
        <div style="background:#FFFFFF; border-left:4px solid #B72683; border-radius:8px; padding:16px 20px; margin-bottom:12px;">
            <div style="font-weight:700; font-size:1rem; color:#333333;">🗺️ Comparables Map</div>
            <div style="font-size:0.85rem; color:#555555; margin-top:4px;">
                Top 5 comparable listings around the subject, mapped and tabulated.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        """
        <div style="background:#FFFFFF; border-left:4px solid #B72683; border-radius:8px; padding:16px 20px; margin-bottom:12px;">
            <div style="font-weight:700; font-size:1rem; color:#333333;">🔋 Energy / ESG</div>
            <div style="font-size:0.85rem; color:#555555; margin-top:4px;">
                Rule-based EPC proxy band and the observed EUR/m2 age-band gap.
            </div>
        </div>
        <div style="background:#FFFFFF; border-left:4px solid #B72683; border-radius:8px; padding:16px 20px; margin-bottom:12px;">
            <div style="font-weight:700; font-size:1rem; color:#333333;">🤖 Copilot Report</div>
            <div style="font-size:0.85rem; color:#555555; margin-top:4px;">
                Full LangGraph valuation narrative combining estimate, comps, and energy.
            </div>
        </div>
        <div style="background:#FFFFFF; border-left:4px solid #B72683; border-radius:8px; padding:16px 20px; margin-bottom:12px;">
            <div style="font-weight:700; font-size:1rem; color:#333333;">📷 CNN Demo</div>
            <div style="font-size:0.85rem; color:#555555; margin-top:4px;">
                Evaluated and dropped: the aerial-imagery condition probe, told as a capability demo.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.divider()
st.markdown(
    f"**Data:** {get_data_label()}. Never scraped from idealista; the API is partner-only. "
    "Comparables, energy proxy, and drivers are all computed from this same processed table."
)
