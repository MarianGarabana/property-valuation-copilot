# Explainable Property Valuation Copilot — Build Spec for Fable 5

A build specification for Claude Code (Fable 5) to implement an explainable Automated Valuation Model for Spanish residential real estate, with a deep-learning image component, SHAP explainability, an agentic valuation copilot, and a deployable Streamlit dashboard.

---

## 1. What this is and why it matters

The product estimates the market value of a residential property in Madrid, explains the drivers behind that number, surfaces comparable properties, flags energy/ESG risk, and writes a short valuation narrative a human analyst could review.

The "wow" is not the price prediction alone. Gradient boosting predicts house prices well and everyone knows it. The differentiators are:

1. Every prediction ships with its SHAP-based reason ("+40k from size, -15k from an F energy rating").
2. A deep-learning image model reads listing photos or satellite tiles to score property/neighborhood condition, a signal a pure tabular model cannot see.
3. A multi-agent copilot turns a raw property into a review-ready valuation report on its own.

This matters commercially because property and mortgage valuation is regulated, so a black-box number is unusable to a bank or a valuation firm. Turning a price into an explained, comparable-backed, energy-aware valuation package is the part that makes a company want to productize it.

## 2. Success criteria

The build is done when:

- A user can select or enter a Madrid property and receive an estimated value with a confidence range.
- The estimate is accompanied by a SHAP explanation (both a plot and plain-language text).
- A CNN produces a condition/quality score from an image, and that score feeds the valuation.
- The dashboard shows comparable properties on a map.
- An energy/ESG flag appears (rule-based or predicted EPC band) with its value impact.
- A copilot produces a written valuation summary combining the above.
- Model training is tracked (MLflow), and there is a basic drift/monitoring check and CI.
- The app is deployed to a free host (Streamlit Community Cloud or Hugging Face Spaces) and loads publicly.

Honesty constraints to keep in the code and docs: idealista18 is 2018 data, so the app is a prototype on historical data, not a live market feed. Do not scrape idealista; its API is partner-restricted. State both facts in the README.

## 3. Data (all free)

- **idealista18** open dataset: ~94,800 Madrid listings with asking prices, indoor features, and coordinates. Primary training data. Published as an R package; export to CSV/Parquet for Python.
- **Kaggle "Madrid real estate market"** and **"Idealista Madrid Rental"**: secondary features and cross-checks.
- **Property/satellite images**: a small labeled subset for the CNN. Options: use listing thumbnails where licensing allows, or public satellite tiles (e.g. via a free static maps tile source) keyed on coordinates. If clean image data is hard to source, fall back to a transfer-learning condition classifier on a public housing-image set and document the substitution.
- **Energy**: derive an EPC-band proxy from building age/type features, or join any open EPC reference table for Madrid. Keep this rule-based if no clean dataset is found.

Reuse the existing `Term 2/MadridRental` Streamlit app as the structural starting point for the dashboard.

## 4. Architecture

**Models**
- Baseline: LightGBM regressor on tabular features. This is the honesty benchmark every other model must beat.
- Deep model: a tabular neural network (PyTorch) on structured features, reported side by side with LightGBM.
- Image model: a CNN via transfer learning (e.g. ResNet/EfficientNet backbone, frozen then fine-tuned) that outputs a condition/quality score. That score becomes an input feature to the value model.
- Explainability: SHAP over the value model; store SHAP values so the dashboard renders them instantly.

**Agentic copilot** (LangGraph)
- comparables_agent: retrieves nearest similar listings (feature + geo distance).
- valuation_agent: calls the trained value model, returns estimate + range.
- energy_agent: returns EPC band/flag and its value impact.
- narrative_agent: writes the valuation summary from the other three outputs.
- Orchestrated as a small graph; LLM calls use the Gemini free tier via a Google Cloud service account, or a local Ollama model, to keep cost at zero.

**App**: Streamlit multi-page, extending the MadridRental layout. Pages: Market Explorer, Value Estimator (with SHAP), Comparables Map, Energy/ESG, Copilot Report.

**MLOps**: MLflow for experiment tracking, a saved model registry/artifact, a simple data-drift check, and a GitHub Actions workflow running tests and linting. Reuse patterns from `Term 2/Hospital-Prediction-System`.

## 5. Free/cheap stack

- Hosting: Streamlit Community Cloud or Hugging Face Spaces (free).
- Training: local, or Colab free GPU for the CNN.
- Libraries: pandas/Polars, scikit-learn, LightGBM, PyTorch, SHAP, LangGraph, Streamlit, MLflow.
- LLM for copilot: Gemini free tier (Google Cloud service account) or local Ollama.
- Repo + CI: GitHub + GitHub Actions free tier.
- Target recurring cost: zero.

## 6. Repository structure

```
property-valuation-copilot/
  CLAUDE.md
  README.md
  data/            raw + processed (gitignored raw)
  etl/             cleaning, feature engineering (Polars)
  models/
    tabular/       LightGBM + tabular NN
    image/         CNN transfer learning
    explain/       SHAP
  agents/          LangGraph copilot (comparables, valuation, energy, narrative)
  app/             Streamlit multipage
  mlops/           MLflow config, drift check, monitoring
  tests/
  .github/workflows/ci.yml
```

## 7. Build plan with Claude subagents

Run this in Claude Code with Fable 5 as an orchestrated crew. The lead agent owns `CLAUDE.md`, the plan, and integration; it fans out to specialized subagents and reviews their output against the success criteria.

- **orchestrator (lead)**: maintains plan and CLAUDE.md, wires modules together, runs the reviewer at each phase.
- **data-engineer**: sources idealista18 + Kaggle, builds the Polars ETL and feature set, writes data validation.
- **ml-modeler**: trains LightGBM baseline and the tabular NN, logs to MLflow, reports comparison.
- **vision-modeler**: builds the CNN transfer-learning pipeline, produces the condition score feature.
- **explainability**: wires SHAP, generates plots and the plain-language reason text.
- **agent-builder**: implements the LangGraph copilot (four agents above) with the free LLM backend.
- **frontend**: builds the Streamlit pages on the MadridRental base.
- **mlops**: MLflow, drift check, GitHub Actions CI, deployment config.
- **reviewer/QA**: checks each phase against Section 2 and the tests before the phase is marked done.

Suggested phase order: data-engineer to ml-modeler to explainability to vision-modeler to agent-builder to frontend, with mlops and reviewer running throughout.

## 8. Claude Code setup before starting

1. Create a domain skill with `skill-creator` that encodes the valuation domain (valuation, risk, energy, mortgage) and AVM vocabulary, so every subagent shares the same definitions. Use `PropertyValuation_Domain_SKILL.md`.
2. Reuse existing plugin skills already installed: `data:*` (SQL, viz, validation) and `engineering:*` (testing-strategy, code-review, documentation).
3. Write a `CLAUDE.md` capturing: the goal, the honesty constraints (2018 data, no scraping), the free-stack rules (no paid APIs), and the coding conventions (ask before adding comments/docs, smallest change that satisfies the request, no unrequested extras).
4. Define the subagents in Section 7 as Claude Code subagents so the orchestrator can spawn them.

## 9. Kickoff prompt to paste into Fable 5

> You are the orchestrator for building an explainable Automated Valuation Model for Madrid residential real estate with an agentic valuation copilot, per the attached build spec (PropertyValuation_BuildSpec.md). Read it fully. Then: (1) confirm the plan and repo structure, (2) set up the subagents listed in Section 7, (3) start with the data-engineer subagent to source idealista18 and build the Polars ETL. Enforce the honesty constraints and the free-stack rule (no paid APIs). Track everything in MLflow. Mark a phase done only when the reviewer subagent confirms it against the Section 2 success criteria. Ask me before any step that would cost money or scrape a restricted source.

## 10. Stretch ideas (only after the core works)

- RL module: a budget-constrained agent that picks which portfolio properties to re-value first, or sequences retrofit investments to maximize value uplift. Use as a demo of RL capability, not a dependency.
- Barcelona/Valencia expansion (idealista18 includes both).
- A physical-climate-risk overlay on the map.

---

### Sources consulted for this spec

- idealista18 open dataset (Madrid ~94,800 listings): github.com/paezha/idealista18
- Kaggle Madrid real estate datasets: kaggle.com
- Claude Code subagents/skills (2026 patterns): Anthropic docs and 2026 guides
