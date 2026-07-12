import streamlit as st
from utils import apply_css, render_sidebar, render_caveat, load_listings_df, render_metric_card

from api_client import ApiError, fetch_energy

st.set_page_config(page_title="Energy / ESG · Valuation Copilot", page_icon="🏠", layout="wide")
apply_css()

df = load_listings_df()
render_sidebar(df)

st.title("Energy / ESG")
st.caption("Marian Garabana · MBDS Student at IE University")
render_caveat()
st.divider()

st.info(
    "No clean Madrid EPC dataset exists in this repo. The band below is a rule-based "
    "proxy from building age and condition, never a certificate."
)

default_id = st.session_state.get("value_estimator_subject", {}).get("asset_id") or df.sort_values("asset_id")["asset_id"].iloc[0]
asset_id = st.text_input("Subject asset_id", value=default_id)

if st.button("Assess energy profile", type="primary"):
    try:
        result = fetch_energy(asset_id)
        st.session_state["energy_state"] = result
    except ApiError as exc:
        st.error(str(exc))
        st.session_state["energy_state"] = None

result = st.session_state.get("energy_state")
if result is None:
    st.info("Enter an asset_id and assess its energy profile.")
    st.stop()

col1, col2 = st.columns(2)
with col1:
    render_metric_card("EPC proxy band", result["band"])
with col2:
    render_metric_card("Energy risk flag", "Yes" if result["flag"] else "No")

if result["band"] == "unknown":
    st.warning("No EPC proxy band could be derived: the build year is missing or invalid.")
else:
    year_part = f"built {result['effective_year']}" if result["effective_year"] is not None else "new-build condition"
    st.write(f"Band derived from building age and condition ({year_part}), not a certificate.")

if result["flag"]:
    st.warning(
        "Pre-1980 stock, built before the first Spanish insulation code (NBE-CT-79). "
        "Carries EU renovation-regulation exposure."
    )

st.subheader("Observed value impact")
impact = result.get("impact")
if impact is None:
    st.info("No comparable age-band segments (at least 20 listings each) are available to estimate a gap.")
else:
    direction = "lower" if impact["gap_eur_m2"] < 0 else "higher"
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        render_metric_card(f"Pre-1980 median (n={impact['n_old']})", f"EUR {impact['median_old_eur_m2']:,.0f}/m2")
    with col_b:
        render_metric_card(f"Post-2006 median (n={impact['n_new']})", f"EUR {impact['median_new_eur_m2']:,.0f}/m2")
    with col_c:
        render_metric_card("Applied to this property", f"EUR {abs(impact['subject_gap_eur']):,.0f} {direction}")
    st.caption(
        f"Scope: {impact['scope']}. Post-2006 stock lists {direction} than pre-1980 stock "
        f"by this gap, applied to the property's {impact['subject_area_m2']} m2."
    )
    st.warning(result["energy_disclaimer"])
