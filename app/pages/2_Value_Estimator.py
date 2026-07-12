import base64

import streamlit as st
from utils import apply_css, render_sidebar, render_caveat, load_listings_df, render_metric_card

from api_client import ApiError, fetch_estimate, fetch_estimate_posted, post_payload_key

st.set_page_config(page_title="Value Estimator · Valuation Copilot", page_icon="🏠", layout="wide")
apply_css()

df = load_listings_df()
render_sidebar(df)

st.title("Value Estimator")
st.caption("Marian Garabana · MBDS Student at IE University")
render_caveat()
st.divider()

NEIGHBORHOOD_DEFAULTS = (
    df.dropna(subset=["neighborhood_id"])
    .groupby(["neighborhood_id", "neighborhood_name"])
    .median(numeric_only=True)
    .reset_index()
)

mode = st.radio("Subject property", ["Existing listing (asset_id)", "Enter a property"], horizontal=True)

request = None

if mode == "Existing listing (asset_id)":
    default_id = df.sort_values("asset_id")["asset_id"].iloc[0]
    asset_id = st.text_input("asset_id", value=default_id)
    if st.button("Look up", type="primary"):
        st.session_state["value_estimator_request"] = {"kind": "asset", "asset_id": asset_id}
        st.session_state["value_estimator_subject"] = {"asset_id": asset_id}
    request = st.session_state.get("value_estimator_request")

else:
    st.write("Unlisted fields (amenities, cadastral, distances) are filled with the barrio median from the dataset.")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        area_m2 = st.number_input("Area (m2)", 20, 500, 80)
        rooms = st.number_input("Rooms", 0, 10, 3)
        bathrooms = st.number_input("Bathrooms", 0, 6, 1)
    with col_b:
        floor = st.number_input("Floor", -1, 25, 2)
        property_type = st.selectbox("Property type", ["flat", "studio", "duplex"])
        condition = st.selectbox("Condition", ["good", "new", "needs_renovation"])
    with col_c:
        construction_year = st.number_input("Construction year", 1900, 2018, 1970)
        barrio_name = st.selectbox(
            "Barrio", sorted(NEIGHBORHOOD_DEFAULTS["neighborhood_name"].unique().tolist())
        )

    if st.button("Estimate", type="primary"):
        barrio_row = NEIGHBORHOOD_DEFAULTS[NEIGHBORHOOD_DEFAULTS["neighborhood_name"] == barrio_name].iloc[0]
        row = barrio_row.to_dict()
        row.update(
            {
                "asset_id": None,
                "area_m2": float(area_m2),
                "rooms": int(rooms),
                "bathrooms": int(bathrooms),
                "floor": float(floor),
                "property_type": property_type,
                "condition": condition,
                "construction_year": int(construction_year),
                "property_age": 2018 - int(construction_year),
                "neighborhood_name": barrio_name,
                "is_duplex": 1 if property_type == "duplex" else 0,
                "is_studio": 1 if property_type == "studio" else 0,
            }
        )
        row.pop("cnn_condition_score", None)
        st.session_state["value_estimator_request"] = {"kind": "custom", "payload_key": post_payload_key(row)}
        st.session_state.pop("value_estimator_subject", None)
    request = st.session_state.get("value_estimator_request")

if request is None:
    st.info("Select an existing listing or enter a property, then estimate its value.")
    st.stop()

with st.spinner("Requesting estimate, range, and SHAP drivers from the valuation API..."):
    try:
        if request["kind"] == "asset":
            estimate = fetch_estimate(request["asset_id"])
        else:
            estimate = fetch_estimate_posted(request["payload_key"])
    except ApiError as exc:
        st.error(str(exc))
        st.stop()

drivers = estimate.get("top_drivers")
low = estimate.get("low")
high = estimate.get("high")

if not drivers or low is None or high is None:
    st.error("No confidence range or SHAP drivers available for this property. No estimate is shown.")
    st.stop()

nominal_pct = estimate["interval_coverage"] * 100
measured_pct = estimate["interval_test_coverage"] * 100

st.subheader("Estimate")
col1, col2 = st.columns(2)
with col1:
    render_metric_card("Estimated market value", f"EUR {estimate['estimate']:,.0f}")
with col2:
    render_metric_card("Confidence range", f"EUR {low:,.0f} to EUR {high:,.0f}")
st.caption(
    f"{nominal_pct:.0f}% nominal interval, covered {measured_pct:.1f}% of held-out test "
    "properties when measured. Estimated market value derived from 2018 asking-price data, "
    "not a closed sale price."
)

st.subheader("SHAP drivers")
st.image(
    base64.b64decode(estimate["shap_plot_png_base64"]),
    caption="Waterfall of the top drivers behind the estimate.",
)
st.write(estimate["driver_text"])

driver_rows = [
    {
        "Feature": d["description"],
        "Effect (EUR)": round(d["shap_eur"]),
        "Direction": "increases" if d["shap_eur"] >= 0 else "decreases",
    }
    for d in drivers
]
st.dataframe(driver_rows, use_container_width=True)
