import streamlit as st
import plotly.express as px
from utils import apply_css, render_sidebar, render_caveat, chart_header, load_listings_df, render_metric_card, CAVEAT_TEXT

st.set_page_config(page_title="Market Explorer · Valuation Copilot", page_icon="🏠", layout="wide")
apply_css()

df = load_listings_df()
render_sidebar(df)

st.title("Market Explorer")
st.caption("Marian Garabana · MBDS Student at IE University")
render_caveat()
st.divider()

price_min, price_max = int(df["price"].min()), int(df["price"].max())

f_col1, f_col2 = st.columns([2, 1])
with f_col1:
    selected_price = st.slider("Asking price range (EUR)", price_min, price_max, (price_min, price_max))
with f_col2:
    barrios = sorted(df["neighborhood_name"].dropna().unique().tolist())
    barrio_options = ["All"] + barrios
    selected_barrio_opts = st.multiselect(
        "Barrios", barrio_options, default=["All"], placeholder="Choose barrios..."
    )
    selected_barrios = (
        barrios
        if ("All" in selected_barrio_opts or len(selected_barrio_opts) == 0)
        else selected_barrio_opts
    )

filtered = df[
    df["neighborhood_name"].isin(selected_barrios)
    & df["price"].between(selected_price[0], selected_price[1])
]

overall_median = df["price"].median()
overall_sqm = df["area_m2"].mean()
overall_ppsqm = df["unit_price_m2"].mean()

col1, col2, col3, col4 = st.columns(4)
with col1:
    render_metric_card("Listings", f"{len(filtered):,}", delta=f"{len(filtered) - len(df):,} vs all")
with col2:
    render_metric_card(
        "Median asking price",
        f"EUR {filtered['price'].median():,.0f}",
        delta=f"EUR {filtered['price'].median() - overall_median:+,.0f} vs overall",
    )
with col3:
    render_metric_card(
        "Avg size",
        f"{filtered['area_m2'].mean():.0f} m2",
        delta=f"{filtered['area_m2'].mean() - overall_sqm:+.0f} m2",
    )
with col4:
    render_metric_card(
        "Avg EUR/m2",
        f"EUR {filtered['unit_price_m2'].mean():,.0f}",
        delta=f"EUR {filtered['unit_price_m2'].mean() - overall_ppsqm:+,.0f}",
    )

with st.expander("How this works"):
    st.write(
        f"Exploratory view of {len(df):,} processed idealista18 listings. Use the price "
        "slider and barrio selector above to filter. Delta arrows compare the filtered "
        "selection against the full dataset baseline. Asking prices are 2018 figures, "
        "not current market values."
    )

tab_charts, tab_barrio, tab_data = st.tabs(["Charts", "By barrio", "Raw data"])

with tab_charts:
    median_val = filtered["price"].median()
    fig = px.histogram(
        filtered, x="price", nbins=40, color_discrete_sequence=["#B72683"], labels={"price": "", "count": ""}
    )
    fig.update_layout(xaxis_title="", yaxis_title="")
    fig.add_vline(
        x=median_val,
        line_width=2,
        line_color="#24262B",
        annotation_text=f"Median: EUR {median_val:,.0f}",
        annotation_position="top right",
        annotation_font_color="#24262B",
    )
    chart_header("Asking price distribution", "Distribution of asking prices across the filtered selection. The vertical line marks the median.")
    st.plotly_chart(fig, use_container_width=True)

    fig = px.histogram(
        filtered, x="unit_price_m2", nbins=40, color_discrete_sequence=["#D4A24C"], labels={"unit_price_m2": "", "count": ""}
    )
    fig.update_layout(xaxis_title="", yaxis_title="")
    chart_header("EUR/m2 distribution", "Distribution of asking price per built square meter across the filtered selection.")
    st.plotly_chart(fig, use_container_width=True)

    fig = px.scatter(
        filtered,
        x="area_m2",
        y="price",
        color="property_type",
        opacity=0.6,
        color_discrete_sequence=["#B72683", "#D4A24C", "#5B5D63"],
    )
    chart_header("Price vs size", "Scatter of built area against asking price, colored by property type.")
    st.plotly_chart(fig, use_container_width=True)

with tab_barrio:
    barrio_summary = (
        filtered.dropna(subset=["neighborhood_name"])
        .groupby("neighborhood_name")
        .agg(median_price=("price", "median"), median_eur_m2=("unit_price_m2", "median"), n=("asset_id", "count"))
        .reset_index()
        .sort_values("median_price", ascending=False)
    )

    chart_header("Median asking price by barrio", "Barrios ranked by median asking price within the filtered selection.")
    top_barrios = barrio_summary.head(30)
    fig = px.bar(
        top_barrios,
        x="neighborhood_name",
        y="median_price",
        color="median_price",
        color_continuous_scale="RdPu",
        labels={"neighborhood_name": "", "median_price": ""},
    )
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

    chart_header("Median EUR/m2 by barrio", "Barrios ranked by median asking price per square meter within the filtered selection.")
    top_ppsqm = barrio_summary.sort_values("median_eur_m2", ascending=False).head(30)
    fig = px.bar(
        top_ppsqm,
        x="neighborhood_name",
        y="median_eur_m2",
        color="median_eur_m2",
        color_continuous_scale="RdPu",
        labels={"neighborhood_name": "", "median_eur_m2": ""},
    )
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        barrio_summary.rename(
            columns={
                "neighborhood_name": "Barrio",
                "median_price": "Median price (EUR)",
                "median_eur_m2": "Median EUR/m2",
                "n": "Listings",
            }
        ),
        use_container_width=True,
    )

with tab_data:
    st.dataframe(filtered, use_container_width=True)
    st.download_button(
        "Download filtered data as CSV",
        f"# {CAVEAT_TEXT}\n" + filtered.to_csv(index=False),
        file_name="madrid_listings_2018_prototype.csv",
        mime="text/csv",
    )
