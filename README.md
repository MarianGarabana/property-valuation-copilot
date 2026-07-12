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

## Status

Phases 0 to 6 complete and reviewer-gated: data and ETL, tabular models with CQR
intervals, SHAP explainability, the vision capability demo (evaluated and dropped),
the LangGraph copilot, and the Streamlit dashboard, now backed by the Phase 6B.1
FastAPI /v1 API. Remaining: Phase 6B.2 (Next.js frontend), Phase 7 (MLOps and
deploy), Phase 8 (final review). See PropertyValuation_BuildPlan_StepByStep.md and
PROJECT_HISTORY.md.
