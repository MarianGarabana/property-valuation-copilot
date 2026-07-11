# Explainable Property Valuation Copilot — Step-by-Step Build Plan with Model Routing

Drop this into a fresh Claude Code session to build the explainable Automated Valuation Model with an agentic copilot. It pairs with `PropertyValuation_BuildSpec.md` (the what) and `PropertyValuation_Domain_SKILL.md` (the shared context). This file is the how, in order, with a specific Claude model and effort level assigned to every subagent.

---

## How to read the model assignments

Anthropic's 2026 lineup, from most to least capable:

- **Fable 5** (Mythos-class): the strongest agentic coder and reasoner, best on long-horizon multi-file work, vision (reading images/screenshots), and finance/document reasoning. Costs about 10 dollars per million input / 50 per million output, roughly 2x Opus, and is slower to first token because it reasons hard before answering. Use it for the hard, autonomous jobs where a wrong plan is expensive.
- **Opus 4.8**: strong all-round reasoning and agentic coding at about half the price (5 / 25) and lower latency. The correct default for most implementation work.
- **Sonnet 5**: fast and cheaper, great for straightforward, well-specified implementation, tests, and glue code.
- **Haiku 4.5**: cheapest and fastest, for mechanical edits, formatting, and quick lookups.

Effort/thinking level: turn it **high** for planning, architecture, and hard debugging; **medium** for standard implementation; **low** for mechanical work. Higher effort costs more tokens, so spend it where a mistake propagates.

Routing principle: **Fable 5 for the three hard nodes (planning, vision, the agent graph), Opus for the core modeling and review, Sonnet/Haiku for mechanical work.** This keeps cost near the Opus baseline while buying Fable's edge only where it pays off. If budget is tight, downgrade the orchestrator to Opus and keep Fable only on vision and the agent graph.

### Model routing table

| Subagent | Model | Effort | Why this model |
|---|---|---|---|
| orchestrator (lead) | Fable 5 | high | Long-horizon planning and cross-module integration is exactly where Fable's lead is largest; a bad plan is the most expensive mistake. Downgrade to Opus to save cost. |
| data-engineer | Opus 4.8 | medium | ETL and feature work is well-defined; Opus handles it cheaply. |
| ml-modeler | Opus 4.8 | high | Training, tuning, and honest metric comparison need strong reasoning but not Fable. Escalate a single stuck training bug to Fable. |
| vision-modeler | Fable 5 | medium | CNN transfer learning plus messy image-data wrangling, and Fable is the strongest at vision tasks. |
| explainability | Sonnet 5 | medium | SHAP wiring is fairly mechanical once the model exists. |
| agent-builder | Fable 5 | high | The LangGraph multi-agent copilot is long-horizon orchestration logic; Fable's agentic-coding edge matters most here. |
| frontend | Sonnet 5 | medium | Streamlit pages on the existing MadridRental base are mostly straightforward; send only tricky interactive bits to Opus. |
| mlops | Opus 4.8 | medium | MLflow, CI, drift, and deploy config are config-heavy and benefit from Opus reliability. |
| reviewer/QA | Opus 4.8 | high | Critical code review and checking against success criteria needs strong reasoning; run the final pre-deploy review on Fable. |

In Claude Code, set the model per subagent in the subagent definition (the `model` field), and consider a `fallbackModel` so a node degrades gracefully instead of stalling. The orchestrator can override a node's model for a single hard task.

---

## Phase 0 — Session setup (orchestrator, Fable 5, high)

1. Read `PropertyValuation_BuildSpec.md` and `PropertyValuation_Domain_SKILL.md` fully.
2. Install/enable the `property-valuation-domain` skill so every subagent loads it.
3. Write `CLAUDE.md` capturing: the goal, honesty constraints (2018 data, no scraping), free-stack rule (no paid APIs or hosting), and the coding rules (ask before adding comments/docs, smallest change that satisfies the request, no unrequested extras, no em dashes in prose).
4. Scaffold the repo structure from Section 6 of the spec.
5. Define all subagents from the routing table above, each with its model, effort, and the domain skill loaded.
6. Confirm the plan back to the user before building.

## Phase 1 — Data (data-engineer, Opus 4.8, medium)

1. Source idealista18 (Madrid, ~94,800 listings); export to Parquet.
2. Pull the Kaggle Madrid sets as secondary features and cross-checks.
3. Build the Polars ETL: clean, dedupe, handle outliers and missing values.
4. Define the single feature schema file every agent references (snake_case names).
5. Write data validation tests (row counts, null rates, value ranges).
6. Reviewer checks before marking done.

## Phase 2 — Tabular models (ml-modeler, Opus 4.8, high)

1. Train the LightGBM baseline; log MAE/RMSE/MAPE to MLflow on a fixed held-out split.
2. Train the tabular neural network (PyTorch); log the same metrics.
3. Produce an honest side-by-side comparison table.
4. Save the winning model as the production artifact.
5. Reviewer confirms metrics are real and the split is clean (no leakage).

## Phase 3 — Explainability (explainability, Sonnet 5, medium)

1. Wire SHAP over the production value model.
2. Generate per-prediction SHAP plots and plain-language driver text.
3. Cache SHAP values for instant dashboard rendering.
4. Reviewer checks that no prediction renders without range + top drivers.

## Phase 4 — Vision model (vision-modeler, Fable 5, medium)

1. Assemble the image dataset (listing thumbnails where licensing allows, or public satellite tiles by coordinate). If clean data is hard, use the documented transfer-learning fallback.
2. Build the CNN via transfer learning (frozen backbone, then fine-tune).
3. Output a condition/quality score and feed it back as a feature to the value model; retrain and re-compare.
4. Reviewer confirms the image feature is added honestly and improves or is neutral on held-out metrics.

## Phase 5 — Agentic copilot (agent-builder, Fable 5, high)

1. Build the LangGraph graph with four agents: comparables, valuation, energy, narrative.
2. Back the LLM calls with the Gemini free tier (Google Cloud service account) or local Ollama.
3. comparables: feature + geo distance retrieval. energy: EPC band/flag and value impact. valuation: calls the model for estimate + range. narrative: writes the summary following the domain skill's writing rules.
4. Reviewer runs the graph end to end on sample properties.

## Phase 6 — Dashboard (frontend, Sonnet 5, medium; hard bits to Opus)

1. Extend the MadridRental Streamlit structure.
2. Pages: Market Explorer, Value Estimator (with SHAP), Comparables Map, Energy/ESG, Copilot Report.
3. Wire the models and the copilot into the pages.
4. Reviewer checks each success criterion from Section 2 of the spec is visible in the UI.

## Phase 7 — MLOps and deploy (mlops, Opus 4.8, medium)

1. Finalize MLflow tracking and a model registry/artifact.
2. Add a simple data-drift check.
3. GitHub Actions CI running tests and lint.
4. Deploy to Streamlit Community Cloud or Hugging Face Spaces; confirm it loads publicly.

## Phase 8 — Final review (reviewer/QA, run on Fable 5, high)

1. Full pass against every success criterion in Section 2 of the spec.
2. Confirm honesty constraints are visible (2018 data, no scraping) in README and UI.
3. Confirm no paid dependency crept in.
4. Produce a short model card and a demo script.

## Stretch (only after Phase 8, agent-builder or ml-modeler, Fable 5, high)

- RL module: budget-constrained re-valuation ordering or retrofit sequencing. Demo of capability, not a dependency.
- Barcelona/Valencia expansion (idealista18 includes both).

---

## Kickoff prompt for the new session

> You are the orchestrator for building an explainable Automated Valuation Model for Madrid residential real estate with an agentic valuation copilot. Read `PropertyValuation_BuildSpec.md`, `PropertyValuation_Domain_SKILL.md`, and this plan (`PropertyValuation_BuildPlan_StepByStep.md`) in full before doing anything. Then execute Phase 0: enable the domain skill, write CLAUDE.md, scaffold the repo, and define every subagent with the exact model and effort level from the routing table in this plan. Run the phases in order. Mark a phase done only when the reviewer subagent confirms it against the spec's Section 2 success criteria. Enforce the honesty constraints (2018 data, no scraping) and the free-stack rule (no paid APIs or hosting). Ask me before any step that would cost money or scrape a restricted source. Confirm the plan and the subagent model assignments back to me before you start building.

---

### Sources for the model routing

- Claude Fable 5 vs Opus 4.8 (benchmarks, pricing, when to use each): truefoundry.com, anthropic.com
- Fable 5 as first Mythos-class model, SWE-bench Pro 80.3 percent, vision strengths: anthropic.com/news/claude-fable-5-mythos-5
