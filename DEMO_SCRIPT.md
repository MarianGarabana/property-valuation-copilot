# Demo Script: Explainable Property Valuation Copilot

A 5 to 10 minute walkthrough for presenting the project in a portfolio or interview
setting. The theme to land: every number on screen is real, labeled with how it was
measured, and the app would rather show nothing than show a number without its range
and drivers.

## Links

- Frontend (canonical): https://property-valuation-copilot.vercel.app
- API: https://property-valuation-api-f5et.onrender.com (health check at `/health`)
- Repo docs: `README.md`, `MODEL_CARD.md`, `PROJECT_HISTORY.md`

Cold-start note: the API sleeps after 15 minutes idle on Render's free tier. The first
request answers 502 while the container wakes (30 to 50 seconds). The frontend knows
this: it retries with backoff and shows a "waking the model" notice. Either open the
site a minute before presenting, or present the waking state itself; it is a designed
behavior worth showing.

## Walkthrough

### 1. Landing page (about 2 minutes)

Open https://property-valuation-copilot.vercel.app.

- Point at the live sample valuation in the hero. Those numbers are fetched from the
  deployed API on page load, not hardcoded. The coverage figure reads "90.3% measured
  coverage" because 0.9029576781879892 is what the interval actually covered on 14,437
  held-out test properties. The app never rounds that to a bare "90%".
- Read the honesty cards: the point estimate (LightGBM on 38 features from the open
  idealista18 dataset), the honest range (conformalized quantile regression labeled with
  measured coverage), and "Dropped features stay dropped" (the CNN negative result).
- Point at the footer: "Estimates come from 2018 Madrid asking prices; this is a
  historical prototype, not a live market feed." That sentence is on every page and
  inside every API payload.

### 2. Valuation workspace (about 3 minutes)

Click "Open the valuation workspace" or the Valuation nav link.

- Look up a real 2018 listing (the page offers samples; asset A15019136831406238029 is a
  47 m2 flat in Pau de Carabanchel that estimates at about 146,736 EUR in a range of
  100,596 to 222,124 EUR).
- Estimate panel: the range is labeled "this 90% nominal interval covered 90.3% of
  held-out test properties". Say why that wording matters: the interval is per-property
  (a cheap flat gets a band around 75k EUR wide, an expensive one around 1.0M), and the
  coverage claim is a measurement, not a promise.
- SHAP drivers: signed EUR contributions rendered as diverging bars. Concrete talking
  point: "size at 47 m2 subtracts 103,487 EUR, the neighborhood subtracts 58,493". Note
  the on-chart honesty detail: these are the top 5 of 38 features, so the bars are not
  drawn as a waterfall that would fake a running total.
- Comparables map: five real listings with real asset ids, prices, and a "why" line
  (distance, area, rooms). Nothing synthetic.
- Energy flag: the EPC band is a stated proxy from build year and condition, and the
  value impact always carries the sentence "This is an observed asking-price difference
  between age bands, not a measured effect of the energy rating."
- Copilot narrative: a written valuation summary that combines all of the above. Every
  figure in the text is validated against the computed facts; if an LLM ever invents or
  drops a number, the narrative falls back to a labeled template built directly from the
  facts. The deployed service runs that template path, and says so in the label.

### 3. Fail-closed behavior (about 1 minute)

Explain rather than break the demo: if the API is unreachable or a payload fails schema
validation, every page shows an explicit error and zero numbers. There is no cached or
partial estimate. During a cold start the app shows the waking notice, retries within a
90 second budget, and then fails closed. An estimate renders with its range and drivers
or it does not render at all.

### 4. The CNN study page (about 2 minutes)

Click "Read the CNN study". This is the strongest interview material because it is a
negative result told straight.

- A frozen ResNet18 probe over PNOA aerial tiles predicts listing condition above chance
  (tile AUC 0.5929 vs 0.5) under a strict rule: no tile may straddle CNN training and
  the listings it scores, because a CNN that memorizes tiles fakes gains.
- The ablation measured what the score adds over the condition feature the model already
  has: MAE +303 EUR, RMSE +386 EUR, MAPE +0.10 points. Worse on all three.
- So the feature was dropped. The pitch line: "the model measured its own new feature,
  found it redundant, and the write-up ships instead of the feature. Posting a
  cnn_condition_score to the live API changes nothing; I verified that on the deployed
  service."

### 5. The API as the single source of truth (about 1 minute)

Open https://property-valuation-api-f5et.onrender.com/health in a tab.

- The payload holds the real test metrics (MAE 42,301.32, RMSE 74,500.47, MAPE 12.78)
  and the measured coverage at full precision. The frontend renders these; it never
  recomputes or re-rounds an API number into a different value.
- Every `/v1` payload carries the 2018 caveat inside the JSON itself, so any client that
  consumes the API inherits the honesty statement.

## One-command local run

Two processes from the repo root (full instructions in the README):

    .venv/bin/python -m uvicorn api.main:app --port 8600
    VALUATION_API_URL=http://localhost:8600 .venv/bin/python -m streamlit run app/Home.py --server.port 8510

The Streamlit dashboard is the internal twin of the public site and reads every number
from the same API. Kill the API mid-demo and the dashboard fails closed on the spot,
which is a good live proof of the honesty rules.

## Wow moments, in order of impact

1. The live sample valuation on the landing page: real model, real 2018 listing, range
   and drivers attached, fetched from a free-tier host in front of the viewer.
2. The SHAP driver bars: a valuation a bank reviewer could argue with, feature by
   feature, in euros.
3. The fail-closed rule: the app shows nothing rather than an unexplained number, and
   the cold-start waking state proves it live.
4. The CNN story: a deep-learning feature that was built, measured redundant on a
   controlled ablation, and dropped, with the evaluation published. Honest negative
   results are rare in portfolios and interviewers know it.
5. The narrative validator, stated precisely: it was tested against a live LLM on 10
   properties and correctly rejected every non-compliant narrative (9 of 10, each for a
   dropped mandatory disclaimer sentence), falling back to the labeled template every
   time. The model never fabricated a number, so say the fabrication defense is present
   and untriggered; do not claim it caught fabrications, because there were none to
   catch.
