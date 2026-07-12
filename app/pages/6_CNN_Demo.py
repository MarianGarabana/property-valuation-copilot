import streamlit as st
from utils import apply_css, render_sidebar, render_caveat, load_listings_df

st.set_page_config(page_title="CNN Demo · Valuation Copilot", page_icon="🏠", layout="wide")
apply_css()

df = load_listings_df()
render_sidebar(df)

st.title("CNN Demo: Evaluated and Dropped")
st.caption("Marian Garabana · MBDS Student at IE University")
render_caveat()
st.divider()

st.error(
    "This feature was evaluated and dropped. It does not feed the value model shown in "
    "the rest of this app. cnn_condition_score stays null in the data and is never used "
    "in the Value Estimator, Comparables Map, or Copilot Report."
)

st.markdown(
    "A frozen ResNet18 probe over PNOA aerial imagery was built and evaluated under "
    "explicit spatial-leakage controls, to test whether an aerial-image condition score "
    "could improve the value model beyond the existing `condition` feature."
)

st.subheader("Leakage control: the straddle-exclusion rule")
st.write(
    "Each tile is a 256x256 aerial image covering about 120 m around a listing. Some "
    "tiles hold more than one listing, and the value-model split is on asset_id, so a "
    "tile could hold both a train listing and a val or test listing. A CNN that "
    "memorizes tiles would leak split information into the score. The rule applied: no "
    "tile may straddle the CNN's training set and the listings it scores. 41,757 tiles "
    "contain only train listings and are the only tiles the CNN trained on. 25,235 "
    "tiles contain at least one val or test listing and were excluded from CNN training "
    "entirely, along with 2,486 train listings that sit on those excluded tiles. All "
    "scoring is out-of-fold."
)

st.subheader("What was measured")
col1, col2 = st.columns(2)
with col1:
    st.markdown("**Tile-disjoint holdout signal**")
    st.table(
        {
            "Metric": ["Tile ROC AUC", "Tile balanced accuracy", "Listing ROC AUC (4,048 listings)"],
            "Value": ["0.5929", "0.5544", "0.5924"],
            "Know-nothing baseline": ["0.5", "0.5", "0.5"],
        }
    )
with col2:
    st.markdown("**Ablation: LightGBM value model, 4,048 held-out validation listings**")
    st.table(
        {
            "Metric": ["MAE (EUR)", "RMSE (EUR)", "MAPE (%)"],
            "Without score": ["48,580", "84,124", "14.41"],
            "With score": ["48,884", "84,510", "14.51"],
            "Delta": ["+303", "+386", "+0.10 pp"],
        }
    )

st.subheader("Why it was dropped")
st.write(
    "The CNN was trained to predict `condition`, and `condition` is already a clean "
    "tabular feature in the value model. The image score is a noisy copy of something "
    "the model already knows exactly. Adding it changed every held-out metric for the "
    "worse, so the score does not ship. The pipeline stays in the repo as a documented "
    "capability demo, per the project's honest-AVM rule: no feature ships unless it "
    "measurably improves held-out metrics."
)

st.subheader("Data source and attribution")
st.write(
    "Imagery: PNOA Maxima Actualidad orthophotos from IGN Spain, fetched through the "
    "free public WMS endpoint at ign.es, no API key, no cost. License: CC-BY 4.0 under "
    "Orden Ministerial FOM/2807/2015."
)
st.markdown("**Obra derivada de PNOA CC-BY 4.0 scne.es**")

st.caption("No live CNN inference runs in this app. See models/image/README.md for the full record.")
