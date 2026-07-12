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

## Status

Phase 0 (setup) complete. Build phases 1 to 8 pending; see
PropertyValuation_BuildPlan_StepByStep.md.
