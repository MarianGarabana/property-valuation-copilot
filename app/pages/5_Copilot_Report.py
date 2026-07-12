import pandas as pd
import streamlit as st
from utils import apply_css, render_sidebar, render_caveat, load_listings_df, render_metric_card

from agents.data import get_subject
from agents.graph import run_copilot

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
        subject = get_subject(asset_id)
        with st.spinner("Running the LangGraph copilot (comparables, valuation, energy, narrative)..."):
            result = run_copilot(subject)
        st.session_state["copilot_state"] = result
    except Exception as exc:
        st.error(f"Copilot run failed: {exc}")
        st.session_state["copilot_state"] = None

result = st.session_state.get("copilot_state")
if result is None:
    st.info("Enter an asset_id and generate the copilot report.")
    st.stop()

if result.get("narrative") is None:
    st.error("No narrative was produced: the valuation node failed, so no report is shown.")
    if result.get("errors"):
        st.write(result["errors"])
    st.stop()

source_label = {
    "template": "labeled template (no LLM backend reachable)",
}.get(result["narrative_source"], result["narrative_source"])
if result["narrative_source"].startswith("llm:"):
    source_label = f"LLM backend: {result['narrative_source'].split(':', 1)[1]}"

st.caption(f"Narrative source: {source_label}")
st.subheader("Valuation narrative")
st.write(result["narrative"])

if result.get("errors"):
    st.subheader("Errors and fallbacks")
    for err in result["errors"]:
        st.warning(err)

valuation = result.get("valuation")
if valuation is not None:
    st.subheader("Valuation facts")
    nominal_pct = valuation["interval_coverage"] * 100
    measured_pct = valuation["interval_test_coverage"] * 100
    col1, col2 = st.columns(2)
    with col1:
        render_metric_card("Estimated market value", f"EUR {valuation['estimate']:,.0f}")
    with col2:
        render_metric_card("Confidence range", f"EUR {valuation['low']:,.0f} to EUR {valuation['high']:,.0f}")
    st.caption(f"{nominal_pct:.0f}% nominal interval, covered {measured_pct:.1f}% of held-out test properties when measured.")
    st.write(valuation["driver_text"])

comps = result.get("comps")
if comps is not None:
    st.subheader("Comparables")
    comp_table = pd.DataFrame(comps["comps"])[["asset_id", "price", "area_m2", "rooms", "distance_km", "why"]]
    st.dataframe(comp_table, use_container_width=True)

energy = result.get("energy")
if energy is not None:
    st.subheader("Energy proxy")
    st.write(f"Band: {energy['band']} (proxy, not a certificate). Energy risk flag: {'yes' if energy['flag'] else 'no'}.")

with st.expander("Facts fed to the narrative"):
    st.text(result.get("narrative_facts") or "")
