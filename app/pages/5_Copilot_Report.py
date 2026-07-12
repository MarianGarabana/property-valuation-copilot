import pandas as pd
import streamlit as st
from utils import apply_css, render_sidebar, render_caveat, load_listings_df, render_metric_card

from api_client import ApiError, fetch_comparables, fetch_copilot, fetch_energy, fetch_estimate

st.set_page_config(page_title="Copilot Report · Valuation Copilot", page_icon="🏠", layout="wide")
apply_css()

df = load_listings_df()
render_sidebar(df)

st.title("Copilot Report")
st.caption("Marian Garabana · MBDS Student at IE University")
render_caveat()
st.divider()

default_id = st.session_state.get("value_estimator_subject", {}).get("asset_id") or df.sort_values("asset_id")["asset_id"].iloc[0]
asset_id = st.text_input("Subject asset_id", value=default_id)

if st.button("Generate report", type="primary"):
    try:
        with st.spinner("Requesting the valuation narrative from the copilot API..."):
            copilot = fetch_copilot(asset_id)
        st.session_state["copilot_state"] = {"asset_id": asset_id, "copilot": copilot}
    except ApiError as exc:
        st.error(str(exc))
        st.session_state["copilot_state"] = None

state = st.session_state.get("copilot_state")
if state is None:
    st.info("Enter an asset_id and generate the copilot report.")
    st.stop()

asset_id = state["asset_id"]
copilot = state["copilot"]

if not copilot.get("text"):
    st.error("No narrative was produced: the valuation node failed, so no report is shown.")
    if copilot.get("errors"):
        st.write(copilot["errors"])
    st.stop()

source_label = {
    "template": "labeled template (no LLM backend reachable)",
}.get(copilot["narrative_source"], copilot["narrative_source"])
if copilot["narrative_source"].startswith("llm:"):
    source_label = f"LLM backend: {copilot['narrative_source'].split(':', 1)[1]}"

st.caption(f"Narrative source: {source_label}")
st.subheader("Valuation narrative")
st.write(copilot["text"])

if copilot.get("errors"):
    st.subheader("Errors and fallbacks")
    for err in copilot["errors"]:
        st.warning(err)

st.subheader("Valuation facts")
try:
    valuation = fetch_estimate(asset_id)
    nominal_pct = valuation["interval_coverage"] * 100
    measured_pct = valuation["interval_test_coverage"] * 100
    col1, col2 = st.columns(2)
    with col1:
        render_metric_card("Estimated market value", f"EUR {valuation['estimate']:,.0f}")
    with col2:
        render_metric_card("Confidence range", f"EUR {valuation['low']:,.0f} to EUR {valuation['high']:,.0f}")
    st.caption(f"{nominal_pct:.0f}% nominal interval, covered {measured_pct:.1f}% of held-out test properties when measured.")
    st.write(valuation["driver_text"])
except ApiError as exc:
    st.warning(f"Valuation facts are unavailable: {exc}")

st.subheader("Comparables")
try:
    comparables = fetch_comparables(asset_id)
    comp_table = pd.DataFrame(comparables["comps"])[["asset_id", "price", "area_m2", "rooms", "distance_km", "why"]]
    st.dataframe(comp_table, use_container_width=True)
except ApiError as exc:
    st.warning(f"Comparables are unavailable: {exc}")

st.subheader("Energy proxy")
try:
    energy = fetch_energy(asset_id)
    st.write(f"Band: {energy['band']} (proxy, not a certificate). Energy risk flag: {'yes' if energy['flag'] else 'no'}.")
except ApiError as exc:
    st.warning(f"Energy proxy is unavailable: {exc}")

with st.expander("Facts fed to the narrative"):
    st.text(copilot.get("facts") or "")
