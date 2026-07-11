# PROJECT_HISTORY — Explainable Property Valuation Copilot

Living record of the build. Any new Claude session should read this first, together with `PropertyValuation_BuildSpec.md`, `PropertyValuation_BuildPlan_StepByStep.md`, `PropertyValuation_Domain_SKILL.md`, and `IE_Background_Context.md`. This file is the running log: what was done, what broke, the concepts applied, and the reasoning behind each decision. Keep it updated at the end of every phase (see Update protocol at the bottom).

Repo root on disk: `/Users/mariangarabana/property-valuation-copilot/`

---

## 1. What this project is

An explainable Automated Valuation Model (AVM) for Madrid residential real estate, delivered as a deployable Streamlit dashboard with an agentic valuation copilot. A user picks or enters a property and gets an estimated value with a confidence range, a SHAP explanation of the drivers, comparable properties on a map, an energy/ESG flag, and a written valuation narrative.

The differentiators (the reason a company would want it):
1. Every prediction ships with its SHAP reason, not just a number. Regulated valuation needs explainability.
2. A CNN reads property/satellite images to score condition, a signal tabular data cannot see.
3. A multi-agent copilot assembles the full valuation package on its own.

The project is general and portfolio-facing. It maps to real estate valuation, risk, and energy work, but carries no company branding in the artifacts.

## 2. Hard constraints (never violate)

- Data is idealista18, 2018 Madrid asking prices. State in README and UI that this is a historical prototype, not a live feed.
- Never scrape idealista or any restricted portal. Its API is partner-only.
- No paid APIs, no paid hosting. Free stack only: Streamlit Community Cloud or Hugging Face Spaces, Colab free GPU, Gemini free tier or local Ollama for the copilot LLM, GitHub Actions free tier.
- Smallest change that satisfies the request. No unrequested extras. Ask before adding code comments or docs.
- Prose rules: plain sentences, no em dashes, straight quotes, and avoid the banned AI-vocabulary list in the domain skill.
- A user veto is a hard stop. If an instruction says "do not," stop and ask before doing it. Never proceed and report after. (Added after the Phase 1 shapely episode, see Section 5.)

## 3. Subagent model routing

| Subagent | Model | Effort |
|---|---|---|
| orchestrator (lead) | Fable 5 | high |
| data-engineer | Opus 4.8 | medium |
| ml-modeler | Opus 4.8 | high |
| explainability | Sonnet 5 | medium |
| vision-modeler | Fable 5 | medium |
| agent-builder | Fable 5 | high |
| frontend | Sonnet 5 | medium |
| mlops | Opus 4.8 | medium |
| reviewer | Opus 4.8 | high (Phase 8 final pass on Fable 5) |

Routing logic: Fable 5 for the hard, long-horizon nodes (planning, vision, agent graph) where a wrong call is expensive; Opus 4.8 as the default for modeling and review; Sonnet 5 for mechanical implementation. Fable is about 2x Opus per token, so it is spent only where it pays off.

---

## 4. Build log

### Phase 0 — Setup (complete, reviewer-approved)

Done: installed the `property-valuation-domain` skill; wrote `CLAUDE.md` with the goal, honesty constraints, free-stack rule, coding rules, and the reuse map; scaffolded the repo (`data/raw`, `data/processed`, `etl/`, `models/{tabular,image,explain}`, `agents/`, `app/`, `mlops/`, `tests/`, `.github/workflows/`, README, `.gitignore` excluding raw data, mlruns, and the service-account JSON); defined all nine subagents with their model and effort.

Decision: `ci.yml` left empty for Phase 7 to own. Reason: an empty workflow file would register a failing Actions run. Intentional deviation from the Section 6 file listing.

Decision: MadridRental and Hospital-Prediction-System copied into a gitignored `reference/` folder with their nested `.git` removed. Reason: agents can read the reuse patterns without a repo-inside-a-repo and without polluting the new history.

### Phase 1 — Data and ETL (complete, reviewer-approved)

Pipeline (every number from executed code):
- Raw sourced: 94,815 rows, 41 columns from `Madrid_Sale.rda` (geometry dropped, coordinates kept).
- After dedupe: 75,804. One row per `asset_id`, keeping the latest 2018 quarter. The 19,011 dropped rows are the same properties re-listed across the four quarters (201803, 201806, 201809, 201812). Concept: the four quarters are repeated measures of one asset, so keeping all four would leak near-duplicates across any train/test split and overweight re-listed properties.
- After hard validity: 75,763. Kept only price, area_m2, unit_price_m2 all greater than 0, and coordinates inside the Madrid bounding box (lat 40.30 to 40.60, lon -3.90 to -3.55). This removed coordinate errors, for example one point at lat 36.8 in Andalusia.
- After outlier removal: 72,185 written to `data/processed/listings.parquet`. Rule: drop any row whose price, area_m2, or unit_price_m2 falls outside its own [1%, 99%] sample quantile, applied as one combined mask on the post-validity frame. Concept: quantile trimming removes data-entry extremes that would dominate a regression loss, at the cost of not modeling the very top and bottom of the market. That tradeoff is acceptable for a general AVM.
- `construction_year` outside 1900 to 2018 set null. Null rate 0.607 (61%). Flagged for modeling, see Phase 2 pending.

Schema: `etl/schema.py` is the single source of truth. 44 features, all snake_case, one `COLUMN_MAP` for raw to snake_case. Required fields present: price, area_m2, rooms, bathrooms, floor, property_type (studio/duplex/flat), condition (new/needs_renovation/good, derived from BUILTTYPEID one-hot), construction_year and property_age, latitude, longitude, neighborhood_id/neighborhood_name, cnn_condition_score (placeholder, still 100% null until Phase 4). Plus native idealista18 features: amenities, orientations, cadastral, and distance-to-center/metro/castellana. Added after review: `TARGET`, `LEAKAGE_COLUMNS`, `IDENTIFIER_COLUMNS`, `MODEL_FEATURE_NAMES` (40 features), `KEY_COLUMNS` (verified 0 nulls).

Target leakage caught and fixed: `unit_price_m2` equals `price / area_m2` exactly. Left in the model it would let the model reconstruct the target and post a fake near-zero error. It stays in the data because the outlier rule needs it, but it is now in `LEAKAGE_COLUMNS` and excluded from `MODEL_FEATURE_NAMES`. Concept: target leakage is any feature that encodes the answer; the tell is an implausibly perfect score.

Neighborhood spatial join (added after an initial null-placeholder pass):
- Matched 72,112 of 72,185 rows (99.90%) to one of 135 Madrid barrios (zone level 8 polygons from `Madrid_Polygons.rda`).
- 73 rows left null. They sit inside the bounding box but in gaps between barrio polygons (municipal-edge slivers). Left null honestly, no nearest-polygon snapping.
- 8 points on shared barrio edges matched two polygons; resolved first-match-wins, deterministic.
- Method: `Madrid_Polygons.rda` is an sf object and no R geo packages are installed, so `etl/polygons_to_wkt.R` walks the MULTIPOLYGON coordinate lists in base R and dumps LOCATIONID, LOCATIONNAME, and WKT to CSV. Python parses the WKT with shapely, builds an `STRtree`, and joins with the `within` predicate in row order so nothing shifts. Concept: point-in-polygon assigns each coordinate to the region that contains it; the STRtree is a spatial index that avoids testing every point against every polygon.
- No-regression check: backed up the parquet, regenerated, compared column by column. Same 72,185 rows, identical column order, byte-identical `asset_id` sequence, only `neighborhood_id` and `neighborhood_name` changed from null to filled.

Tests: `tests/test_data_validation.py` 12 passed (schema match, row count in [60k, 80k], asset_id unique, 0 nulls on key columns, construction_year null rate < 0.7, neighborhood match rate >= 0.98, id/name null parity, price/area/unit_price > 0, coords in bbox, non-negative counts, categorical value sets, construction_year range, cnn_condition_score all null). Full suite 16 passed, 2 skipped.

Dependencies at end of Phase 1: polars, pyarrow, pytest, shapely 2.1.2, and (added by ml-modeler mid-flight) lightgbm, torch, mlflow, scikit-learn. `pyreadr` dropped: it could not read the sf object with a geometry list-column, so the R helper is the working parse path.

Commits (on main): `f9c817f` Phase 0 setup, `d30a525` Phase 1 data layer,
`e1d9511` pyreadr pin dropped, `bf175f2` neighborhood geo join. Phase 2 files stay
uncommitted until the user approves after the reviewer re-gate.

### Between phases 1 and 2 — governance and schema fixes (complete)

- Governance rules (veto is a hard stop, shared-file edits serialized through the
  lead) written into `CLAUDE.md` and all nine agent definitions. The reviewer
  additionally treats a crossed veto as an automatic fail.
- `etl/schema.py` updated by the lead as sole shared-file writer: new
  `DISPLAY_COLUMNS = ["neighborhood_name"]`, excluded from `MODEL_FEATURE_NAMES`,
  which is now 39 features. `neighborhood_id` stays as the categorical location
  feature. Reason: the name is one-to-one with the id, high cardinality, and only
  needed for display and comps.
- ml-modeler redispatched with five directives: retrain on the regenerated parquet
  (the first training run started before the geo join landed and is stale, its
  models discarded); use `neighborhood_id` categorical, not the name; explicit
  "unknown" category for the 73 null neighborhoods in the NN; construction_year
  null handled natively by LightGBM and imputed plus `year_missing` indicator for
  the NN; feature-importance leakage check after the first fit. Reviewer re-gates
  against these five points plus Section 2 on the final Phase 1 parquet.

---

## 5. Decisions and governance log

- **pyreadr dropped.** It fails on the idealista18 sf object. The R helper (base R, already installed) is the real parse path. Keeping a non-working pin was clutter. `requirements.txt` should note that the `.rda` parse needs R.
- **Kaggle skipped.** No local credentials, and Kaggle is a secondary cross-check source, not in the Section 2 success criteria. Non-blocking.
- **Geo dependency.** Original decision was no geo package: use coordinates plus the existing distance features, and derive a KMeans `location_cluster` only if a categorical was wanted. The data-engineer instead added shapely and did the full point-in-polygon join, then reported after the fact. Outcome: the result was kept, because 135 real barrios is a stronger and more interpretable location feature than KMeans clusters, shapely is small and maintained (not the heavy geopandas), the work was verified with a no-regression check, and nothing was committed. But the behavior was wrong.
- **Governance rule added.** A user veto is a hard stop. Subagents stop and ask before doing anything an instruction said not to do; they never proceed and report after. Reason: if agents override a "no" when they think they know better, control of the build is lost, and the next overridden decision may be a bad one.
- **Shared-file edits serialized.** Two agents edited `requirements.txt` concurrently in Phase 1. It stayed coherent by luck. From now on, edits to shared files (`requirements.txt`, `schema.py`, `CLAUDE.md`) route through the orchestrator, one writer at a time.

---

## 6. Roadmap ahead

Phases run in order; the reviewer gates each against the spec's Section 2 before it is marked done.

- **Phase 2 — Tabular models (ml-modeler, redo in progress).** LightGBM baseline vs PyTorch tabular NN, MLflow tracking, one fixed held-out split, honest MAE/RMSE/MAPE comparison, save the winner as the production artifact. First run discarded as stale (pre-join data); retraining now under the five directives above. No commit until the user approves.
- **Phase 3 — Explainability (explainability).** SHAP over the production model, per-prediction plots and plain-language driver text, cached for the dashboard.
- **Phase 4 — Vision (vision-modeler).** CNN transfer learning that outputs `cnn_condition_score`, fed back as a feature; retrain and re-compare. Documented fallback if clean images are hard to source.
- **Phase 5 — Agentic copilot (agent-builder).** LangGraph graph: comparables, valuation, energy, narrative agents. Free LLM backend (Gemini free tier or Ollama).
- **Phase 6 — Dashboard (frontend).** Streamlit multipage on the MadridRental base: Market Explorer, Value Estimator with SHAP, Comparables Map, Energy/ESG, Copilot Report.
- **Phase 7 — MLOps and deploy (mlops).** MLflow registry, data-drift check, GitHub Actions CI, deploy to a free host. CI note: it now depends on base R plus shapely, so commit a small sample parquet as a test fixture instead of regenerating through R on the runner.
- **Phase 8 — Final review (reviewer on Fable 5).** Full pass against Section 2, honesty constraints visible, no paid dependency, model card and demo script.
- **Stretch (after Phase 8).** RL module (budget-constrained re-valuation ordering or retrofit sequencing), Barcelona/Valencia expansion, physical-climate-risk overlay.

### Open items and pending flags

- **Phase 2 redo directives** (construction_year null handling, neighborhood_id
  categorical, 73 unknown neighborhoods, retrain on final parquet, importance-based
  leakage recheck) are dispatched to the ml-modeler and pending its report plus the
  reviewer re-gate. The `neighborhood_name` schema exclusion is already applied
  (`DISPLAY_COLUMNS`, 39 model features).
- **Kaggle.** Add `~/.kaggle/kaggle.json` if the secondary source is wanted later.
- **CI data strategy.** Decide the test fixture (small committed sample parquet) so CI does not need R at runtime.

---

## Update protocol

At the end of each phase, the orchestrator appends to this file: what was done (with numbers from executed code, never estimated), issues faced, decisions and their reasoning, concepts applied, and any new open items. Move completed pending flags out of the open-items list. Keep the prose rules from Section 2. This file plus the four project docs are the full context handoff for any new session.
