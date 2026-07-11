# Explainable Property Valuation Copilot

## Goal
An explainable Automated Valuation Model for Madrid residential property: value estimate
with confidence range, SHAP drivers, comparables map, energy/ESG flag, CNN condition
score, and a LangGraph copilot that writes the valuation narrative. Spec:
PropertyValuation_BuildSpec.md. Plan: PropertyValuation_BuildPlan_StepByStep.md.
Success criteria: Section 2 of the spec. A phase is done only when the reviewer
subagent confirms it against those criteria.

## Honesty constraints (hard rules)
- Primary data is idealista18: 2018 Madrid asking prices. This is a historical
  prototype, not a live market feed. State this in the README and in the UI.
- Never scrape idealista or any restricted portal. Its API is partner-only.
  If a live source is ever needed, stop and ask.
- Report real metrics on one fixed held-out split. Never inflate. LightGBM is the
  mandatory baseline; no deep model ships without a side-by-side comparison.
- Never show a prediction without its confidence range and top drivers.

## Free-stack rule
No paid APIs, no paid hosting, no paid CI. Stack: Polars, scikit-learn, LightGBM,
PyTorch, SHAP, LangGraph, Streamlit, MLflow. LLM: Gemini free tier (service account)
or local Ollama. Hosting: Streamlit Community Cloud or Hugging Face Spaces. Training:
local or Colab free GPU. Ask before any step that could cost money.

## Coding rules
- Smallest change that satisfies the request. No unrequested extras.
- Ask before adding code comments or docs.
- Feature names are snake_case and live in one schema file (etl/); no ad hoc renaming.
- Load the property-valuation-domain skill in every subagent.
- Prose (README, narratives, docs): plain direct sentences, no em dashes, straight
  quotes, no banned words (see the domain skill's writing rules).

## Reuse before rebuilding
- Dashboard base: Term 2/MadridRental (multipage Streamlit). Lives outside this repo;
  copy it in or open Claude Code at the IE University level before Phase 6.
- MLOps patterns: Term 2/Hospital-Prediction-System (same access note).
- Transfer-learning CNN references: Term 3/Deep Learning notebooks.
- LangGraph/agent references: Term 3/Generative AI and Term 3/Agentic AI.
Marian reads Python, Polars, PyTorch, Streamlit, LangGraph, and MLflow fluently.
Keep explanations short and only where logic is non-obvious.
