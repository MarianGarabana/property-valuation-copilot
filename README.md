# Explainable Property Valuation Copilot

An explainable Automated Valuation Model for Madrid residential property. It estimates
market value with a confidence range, explains the drivers with SHAP, shows comparable
properties on a map, flags energy/ESG risk, scores property condition from images with
a CNN, and writes a review-ready valuation narrative through a LangGraph copilot.

## Data honesty

- Training data is the idealista18 open dataset: about 94,800 Madrid listings from 2018
  with asking prices, not closed sale prices. This app is a prototype on historical
  data, not a live market feed.
- No data was scraped from idealista or any restricted portal. The idealista API is
  partner-only. All sources are free and open.

## Stack

Polars, scikit-learn, LightGBM, PyTorch, SHAP, LangGraph, Streamlit, MLflow. Free tier
only: no paid APIs, hosting, or CI.

## Deployment honesty

The REST API is unauthenticated by design. This is a free portfolio demo, so the API
is open and has no API key or rate limit. A real deployment would put an API key or an
auth proxy in front of it before exposing it to the public internet.

## Running locally

The dashboard reads every valuation number from the REST API, so the API must run
first. Start two processes with the repo interpreter.

Start the API on port 8600:

    .venv/bin/python -m uvicorn api.main:app --port 8600

Then start the dashboard on port 8510, pointing it at the API:

    VALUATION_API_URL=http://localhost:8600 .venv/bin/python -m streamlit run app/Home.py --server.port 8510

The dashboard reads the API base URL from the VALUATION_API_URL environment variable
and defaults to http://localhost:8600. If the API is down, the valuation, comparables,
energy, and copilot pages show an explicit error and no numbers.

## Deploy topology

The public deployment is two free-tier hosts:

- The FastAPI service runs as a Docker web service on Render's free tier
  (512MB RAM; the API was measured at 398MB with every endpoint exercised).
  It is the single source of truth for every number. Hugging Face was the
  original target but paywalled Docker Spaces for new free accounts mid-deploy,
  so Render substitutes as the free host.
- The Next.js frontend runs on Vercel Hobby (personal, non-commercial use) and
  reads the API base URL from the NEXT_PUBLIC_API_URL environment variable.

A browser talks to the Vercel app, which talks to the Render service. CORS on
the service is set through the API_CORS_ORIGINS variable to the exact Vercel
origin.

The free service sleeps after 15 minutes of inactivity. The first request after
it sleeps has to wake the container (30 to 50 seconds on Render) and load the
model (about 7 seconds measured) before it can answer. The frontend shows a
waking state and gives up after a hard 90 second timeout, failing closed with no
numbers rather than showing a partial result.

## Model artifact delivery

The production LightGBM model is not stored in git (git is not the model store).
The processed listings parquet is committed, but the MLflow production run is
published as a small tarball to a public Hugging Face model repo and fetched into
the Docker image at build time, pinned to an immutable revision. Inside the
container that tarball reconstructs the minimal mlruns subtree, so predict.py
resolves the model through the is_production tag with no code change. The SHAP
cache is not shipped; the API recomputes SHAP per property on demand, which is
fast for a single property. The API image installs api/requirements.txt, a slim
set that leaves out torch, torchvision, Streamlit, Plotly, and pydeck, since the
production model is LightGBM and those are not on the serving path.

## Continuous integration

GitHub Actions runs on every push and pull request to main. It has two jobs:

- python: flake8 lint, then the model-free part of the pytest suite
  (pytest -m "not local_only").
- web: install, generate the API types from the committed openapi.json, build the
  Next.js app, and run the color-contrast check.

What CI does and does not catch, stated plainly. CI covers data validation, the
data-drift check, the app client fail-closed behavior, lint, and the web build. It
does not run the model-output tests, because those need the MLflow production model
artifact, which is not in git. The tests that load the model and check its numbers
(predict, explain, the API endpoints, and the end-to-end copilot graph) are marked
local_only and run locally and at the reviewer gate, not in CI. A green CI run
therefore proves the code lints, the data contract holds, the drift check works,
and the frontend builds. It does not prove the served predictions are correct;
that is verified locally and by the deployed-service smoke test.

## Data drift

mlops/drift.py is an input-drift check only. The data is 2018 asking prices with no
live feed of closed sale prices, so label drift cannot be measured at all. The only
signal that exists here is whether the properties a user queries differ in their
numeric-feature distribution from the 2018 training population. The check computes a
Population Stability Index and a Kolmogorov-Smirnov test per numeric feature against
the training split and flags a feature when its PSI is above 0.2. A no-drift result
means the queried properties look like the training data, not that the model is
accurate today.

## Status

Phases 0 to 6B complete and reviewer-gated: data and ETL, tabular models with CQR
intervals, SHAP explainability, the vision capability demo (evaluated and dropped),
the LangGraph copilot, the Streamlit dashboard, the FastAPI /v1 API, and the Next.js
frontend. Phase 7 (MLOps and deploy) is in progress: MLflow model artifact delivery,
the data-drift check, GitHub Actions CI, and the free-host deployment. Remaining:
Phase 8 (final review). See PropertyValuation_BuildPlan_StepByStep.md and
PROJECT_HISTORY.md.
