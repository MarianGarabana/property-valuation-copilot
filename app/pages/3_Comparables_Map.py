import pandas as pd
import pydeck as pdk
import streamlit as st
from utils import apply_css, render_sidebar, render_caveat, load_listings_df, render_metric_card

from agents import comparables_agent
from agents.data import get_subject

st.set_page_config(page_title="Comparables Map · Valuation Copilot", page_icon="🏠", layout="wide")
apply_css()

df = load_listings_df()
render_sidebar(df)

st.title("Comparables Map")
st.caption("Marian Garabana · MBDS Student at IE University")
render_caveat()
st.divider()

default_id = st.session_state.get("value_estimator_subject", {}).get("asset_id") or df.sort_values("asset_id")["asset_id"].iloc[0]
asset_id = st.text_input("Subject asset_id", value=default_id)

if st.button("Find comparables", type="primary"):
    try:
        subject = get_subject(asset_id)
        result = comparables_agent.run(subject)
        st.session_state["comparables_state"] = {"subject": subject, "result": result}
    except Exception as exc:
        st.error(f"Could not retrieve comparables for this property: {exc}")
        st.session_state["comparables_state"] = None

state = st.session_state.get("comparables_state")
if state is None:
    st.info("Enter an asset_id and find comparables.")
    st.stop()

subject = state["subject"]
result = state["result"]

comps = result["comps"]
st.caption(f"Method: {result['method']}")

col1, col2, col3 = st.columns(3)
with col1:
    render_metric_card("Comparables found", result["n"])
with col2:
    render_metric_card("Price range", f"EUR {result['price_min']:,.0f} to EUR {result['price_max']:,.0f}")
with col3:
    render_metric_card("Farthest comp", f"{result['max_distance_km']:.2f} km")

map_rows = [
    {
        "lat": subject["latitude"],
        "lon": subject["longitude"],
        "label": f"Subject ({subject['asset_id']})",
        "color": [183, 38, 131],
        "radius": 90,
    }
]
for comp in comps:
    comp_row = df[df["asset_id"] == comp["asset_id"]].iloc[0]
    map_rows.append(
        {
            "lat": comp_row["latitude"],
            "lon": comp_row["longitude"],
            "label": f"Comp ({comp['asset_id']}, EUR {comp['price']:,.0f})",
            "color": [212, 162, 76],
            "radius": 60,
        }
    )
map_df = pd.DataFrame(map_rows)

view_state = pdk.ViewState(
    latitude=float(subject["latitude"]), longitude=float(subject["longitude"]), zoom=13
)
layer = pdk.Layer(
    "ScatterplotLayer",
    data=map_df,
    get_position="[lon, lat]",
    get_fill_color="color",
    get_radius="radius",
    pickable=True,
)
st.pydeck_chart(
    pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip={"text": "{label}"},
        map_style=None,
    )
)

st.subheader("Comparable listings")
comp_table = pd.DataFrame(comps)[
    ["asset_id", "price", "area_m2", "rooms", "bathrooms", "property_type", "neighborhood_name", "distance_km", "why"]
]
comp_table = comp_table.rename(
    columns={
        "asset_id": "asset_id",
        "price": "Price (EUR)",
        "area_m2": "Area (m2)",
        "rooms": "Rooms",
        "bathrooms": "Bathrooms",
        "property_type": "Type",
        "neighborhood_name": "Barrio",
        "distance_km": "Distance (km)",
        "why": "Why",
    }
)
st.dataframe(comp_table, use_container_width=True)
