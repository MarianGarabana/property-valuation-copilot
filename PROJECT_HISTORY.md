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
| api-engineer (Phase 6B.1) | Opus 4.8 | medium |
| web-frontend (Phase 6B.2) | Fable 5 | high |

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
`e1d9511` pyreadr pin dropped, `bf175f2` neighborhood geo join.

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

### Phase 2 — Tabular models (complete, reviewer-passed, user-approved)

Every number from executed code, and the lead independently reran the test suite
and recomputed the headline metrics and coverage from MLflow and predict.py.

Comparison on the one fixed held-out test split (14,437 rows):

| Model | MAE (EUR) | RMSE (EUR) | MAPE (%) |
|---|---|---|---|
| LightGBM baseline | 42,301 | 74,500 | 12.78 |
| PyTorch tabular NN | 48,325 | 85,431 | 14.28 |

Winner: LightGBM, on all three metrics. Stated plainly in
`models/tabular/comparison.md`: the deep model loses to the baseline here, which
is the expected outcome on tabular data, not a failure. LightGBM is the
production model.

Split: seeded (42), keyed on `asset_id`, persisted as
`models/tabular/split_assignment.parquet` (git-tracked, the split contract).
Sizes: train 46,198 / val 11,550 / test 14,437. A random split is appropriate
because the data is 2018 cross-sectional (no forecast horizon) and the Phase 1
dedupe already removed the same-asset-across-quarters near-duplicates. Split
before any fitting; NN normalization stats train-only.

Leakage check (directive 5): `unit_price_m2` and `price` excluded from the 38
usable model features (`cnn_condition_score` dropped while 100% null).
LightGBM gain shares read like real estate should: area_m2 56.7%,
neighborhood_id 16.5%, bathrooms 10.5%. No single feature near-total, no
leakage smell. Directives 1-4 all satisfied: retrained on the post-join
parquet, `neighborhood_id` categorical (135 train levels), explicit "unknown"
bucket in the NN for the 73 null neighborhoods, construction_year native null
for LightGBM and imputed plus `year_missing` indicator for the NN.

Confidence range v1: residual-based global 90% band from validation residuals,
[-91,890, +97,963] EUR around the estimate. Test coverage 0.8992 (lead-verified
on 14,437 rows), within a tenth of a percent of nominal. Known weakness, user-
flagged: the band is homoscedastic, so a 90k studio and a 900k penthouse get the
same absolute interval. Fix approved and in progress as a Phase 2 addendum, see
open items.

MLflow: experiment `phase2_tabular`, local file backend (`mlruns/`), runs
`lightgbm_baseline` and `pytorch_tabular_nn` with val+test MAE/RMSE/MAPE, params,
and split id. Production run tagged `is_production=true` (exactly one; stale tags
cleared on retrain), artifacts under `production/`. `predict.py` resolves the
production run by tag and returns `{estimate, low, high, interval_coverage}`.
Env caveat: MLflow 3.14 blocks the file store unless `MLFLOW_ALLOW_FILE_STORE=true`;
train.py and predict.py set it in-process.

Artifact policy (user directive): git is not the model store. Binaries
(`models/tabular/*.pt`, `*.txt`, `*.joblib`) are gitignored; MLflow holds the
production copies. Code, comparison.md, metrics, and the split contract are
committed.

Root cause fixed, not worked around: importing LightGBM and PyTorch in one
process on this Mac loads two OpenMP runtimes and deadlocks then SIGSEGVs
(minimal repro confirmed). `train.py` is a coordinator that runs `train_lgbm.py`
and `train_nn.py` as isolated subprocesses. That is the reason for the
multi-file layout.

Tests: 18 passed (11 data validation + 7 tabular: split disjointness and
coverage, test size, leakage exclusion, predict estimate+range single and
batch). Reviewer verdict: PASS, metrics reproduced to the digit.

Commits: `4121580` PROJECT_HISTORY added, `7223937` governance rules,
`efe024e` schema DISPLAY_COLUMNS fix, `7cb6f38` gitignore model binaries,
`1e3875b` Phase 2 code, comparison, split contract, tests.

---

## 5. Decisions and governance log

- **pyreadr dropped.** It fails on the idealista18 sf object. The R helper (base R, already installed) is the real parse path. Keeping a non-working pin was clutter. `requirements.txt` should note that the `.rda` parse needs R.
- **Kaggle skipped.** No local credentials, and Kaggle is a secondary cross-check source, not in the Section 2 success criteria. Non-blocking.
- **Geo dependency.** Original decision was no geo package: use coordinates plus the existing distance features, and derive a KMeans `location_cluster` only if a categorical was wanted. The data-engineer instead added shapely and did the full point-in-polygon join, then reported after the fact. Outcome: the result was kept, because 135 real barrios is a stronger and more interpretable location feature than KMeans clusters, shapely is small and maintained (not the heavy geopandas), the work was verified with a no-regression check, and nothing was committed. But the behavior was wrong.
- **Governance rule added.** A user veto is a hard stop. Subagents stop and ask before doing anything an instruction said not to do; they never proceed and report after. Reason: if agents override a "no" when they think they know better, control of the build is lost, and the next overridden decision may be a bad one.
- **Shared-file edits serialized.** Two agents edited `requirements.txt` concurrently in Phase 1. It stayed coherent by luck. From now on, edits to shared files (`requirements.txt`, `schema.py`, `CLAUDE.md`) route through the orchestrator, one writer at a time.
- **Commit approval (user-set, 2026-07-12).** No git commit until Marian approves. The lead stages and reports what would be committed; the commit itself waits for her explicit go.
- **Deploy host forced off Hugging Face (2026-07-12).** Mid-deploy, HF began requiring a PRO subscription for Docker Spaces on new free accounts; the repo-create call was refused at the API with "requires a PRO subscription." The cost boundary held: nothing was paid, nothing created. Marian approved Render's free tier as the substitute API host (spec Section 2 amended; the named hosts were examples of free hosting). Measured basis: API RSS 398MB after exercising all endpoints, inside Render's 512MB free cap; 30-50s wake fits the frontend's 90s timeout and cold-start treatment. Pre-authorized fallbacks: single worker first if it OOMs; Koyeb free if Render needs a card or does not fit; if both free hosts fail, hard stop and report, no paid option, no silent demotion to local-only.
- **Subagent permission boundary held (2026-07-12).** The mlops subagent refused to create the public HF model repo on a relayed coordinator message, treating only the user's own words or the permission system as consent for a new public surface. Correct behavior, kept: public-surface creation runs in the lead session where Marian's consent is on record.

---

## 6. Roadmap ahead

Phases run in order; the reviewer gates each against the spec's Section 2 before it is marked done.

- **Phase 2 — Tabular models. DONE**, including the CQR per-property interval addendum (see build log).
- **Phase 3 — Explainability. DONE** (see build log). shap 0.52.0 and matplotlib 3.11.0 added by the lead through the sole-writer flow (the agent hit the missing dependency, paused, and asked instead of editing, as the governance rule intends).
- **Phase 4 — Vision. DONE (closed at the gate, see build log).** Sourcing plan user-approved:
  PNOA aerial orthophoto tiles from IGN Spain (free WMTS, CC-BY 4.0 verified from
  the license document, attribution required in README and UI), keyed lat/lon per
  asset_id, ~67k tiles for all 72,185 listings. Label is a stated proxy: the CNN
  predicts the existing tabular condition field from the tile, never price (that
  would launder target leakage through the image model). Imagery is ~2023-2025
  flights joined to 2018 listings; mismatch goes in the README. torchvision
  0.28.0 added via the sole-writer flow. Four user conditions, all hard:
  1. Tile-level leakage fix: tiles are shared across listings (~1.08 listings per
     tile), so no tile may straddle CNN training and the val/test listings it
     scores. Tiles containing any val/test listing are excluded from CNN
     training entirely; all listings scored out-of-fold; verify any value-model
     gain is not concentrated in shared-tile rows. Reason: a CNN that memorizes
     tiles becomes a tile-ID lookup, tile identity correlates with price, and
     the with/without comparison would report spatial memorization as gain.
  2. Fail fast: stratified ~20k-tile subset first; full 67k download gated on a
     non-neutral subset signal, user sees the subset result before the download.
     Metric rule (user-set): the subset signal is reported as AUC or balanced
     accuracy against the class-prior baseline, on a tile-disjoint holdout,
     never raw accuracy. The condition field is ~78% "good", so blind
     majority-class prediction scores 78% raw accuracy while knowing nothing;
     the honest test is clearing the prior on tiles the CNN never saw.
     Subset signal result (executed, tile-disjoint holdout, probe trained on
     pure-train tiles only, overlap asserted empty): frozen ResNet18 features
     plus balanced logistic head, binary good/new vs needs_renovation.
     Tile-level ROC AUC 0.5929 (chance 0.5), balanced accuracy 0.5544 (chance
     0.5), average precision 0.8716 (class prior 0.8217), listing-level AUC
     0.5924 on 4,048 val listings. AUC stable across regularization
     (0.5926-0.5939). License gate passed before download (WMS
     AccessConstraints: CC BY 4.0). 19,997 of 20,000 tiles at 17.3 tiles/s,
     ~460 MB. Honest read: above chance but weak.
     Gate outcome (user decision): no full download, no fine-tune. Reasoning:
     the ceiling is redundancy, not AUC. The CNN predicts condition, which the
     value model already has exactly, so the score is by construction a noisy
     compression of a known feature; fine-tuning sharpens the copy but a
     sharper copy is still redundant, and retargeting to price is the standing
     leakage veto. Instead one cheap measurement: a scoped subset ablation.
     Ablation (executed, same 4,048 val listings both runs, production
     hyperparameters, out-of-fold scores, straddle exclusion intact):
     without cnn_condition_score MAE 48,580 / RMSE 84,124 / MAPE 14.41;
     with it MAE 48,884 / RMSE 84,510 / MAPE 14.51. Delta +303 / +386 /
     +0.10pp: uniformly negative sign, within sampling wobble, no lift to
     chase. The redundancy hypothesis is a measurement now, not an assumption.
     Defect caught mid-ablation: the first pass returned byte-identical
     with/without results because the join collided with the all-null
     cnn_condition_score placeholder in listings.parquet and silently renamed
     the real scores away, feeding LightGBM the null column. Fixed (drop
     placeholder before join) plus a non-null assertion. Standing warning: any
     code joining a real score onto listings.parquet must drop the placeholder
     column first or the join fails silently.
     Drop executed (user-approved): cnn_condition_score stays null and out of
     the model; schema.py note marks it a closed decision. The CNN ships as a
     documented capability demo. Spec Section 2's CNN criterion was amended
     (user-approved) to what actually happened: leakage-controlled CNN built
     and evaluated, measured redundant against condition, dropped per the
     honest-AVM rule; Phase 8 reviews against the amended wording.
     No-cascade confirmation: the feature is dropped, so the point model is
     unchanged and every Phase 2/3 artifact stays valid. No SHAP cache
     regeneration, no quantile refit, no CQR re-run, no coverage change. The
     Phase 4 invalidation cascade is void.
  3. Honesty gate: measure only what the image adds over and above the existing
     condition feature. Neutral-and-drop is a passing outcome.
  4. Fallback stance: if PNOA falls through, no synthetic per-listing score from
     the 535-house fallback set; either drop the feature or ship the CNN as a
     disclosed standalone demo, never a value-model input.
- **Phase 5 — Agentic copilot. DONE, reviewer-passed (see build log).** LangGraph graph: comparables, valuation, energy, narrative agents. Free LLM backend (Ollama or Gemini free tier) with a validated template fallback.
- **Phase 6 — Dashboard (frontend).** Built (seven pages on the MadridRental base, commit c5aad04), lead-verified in the browser, honesty rules A-H wired into the UI. Remaining before DONE: design polish pass and the reviewer gate. The Streamlit app is the internal/demo deliverable and passes on its own; it is not held for Phase 6B.
- **Phase 6B — Production track (user-directed, added 2026-07-12).** Two steps, each reviewer-gated, run after the Phase 6 gate:
  1. api-engineer (Opus 4.8, medium): **DONE, reviewer-passed (re-gate).** FastAPI /v1 API in api/ (Pydantic models, Envelope caveat on every payload, fail-closed in the response models, errors carry no domain fields, posted cnn_condition_score stripped, CORS via API_CORS_ORIGINS, Dockerfile for HF Spaces port 7860). Marian reviewed and approved the contract before the refactor. Copilot returns 200 with the labeled template narrative when no LLM backend exists, 502 only on real generation failure (verified; the deployed Space runs the template path). Streamlit refactored onto the API through app/api_client.py (VALUATION_API_URL env var, st.cache_data ttl 900, ApiError fail-closed across the network hop, verified live with the API killed). Re-gate verdict PASS: number identity direct-call vs API JSON vs browser exact on two assets; wiring purity grep clean; 52 tests. Related fix: etl made a real package (etl/__init__.py; prep/split/cache and tests now put the repo root on sys.path and import etl.schema; the old pattern let etl/etl.py shadow the package under adversarial import order). README carries the two-process run instructions and the unauthenticated-by-design deployment note.
  2. web-frontend (Fable 5, high): **DONE, reviewer-passed.** Next.js 16 + TypeScript + Tailwind + shadcn/ui in web/, static routes, deployable on Vercel Hobby. Types generated from the API's openapi.json via openapi-zod-client (npm run gen:api), Zod-validated at the boundary, contract failure renders the error state. SHAP drivers chart rendered natively from top_drivers as diverging bars (deliberately no cumulative waterfall: the payload holds only the top 5 of 38 features, a bridge chart would fabricate intermediate totals; on-chart note says the bars do not sum to the estimate). shap_plot_png_base64 unused. Map: maplibre-gl with keyless OpenFreeMap tiles, subject plus 5 comps with real asset_ids and prices. Fail-closed verified with the API killed: explicit error panels, zero numbers, landing metrics fetched live from /health and never cached. Cold-start design: skeletons under 8s, "Waking the model" notice with elapsed counter after, hard 90s AbortController timeout that fails closed. Contrast script (web/scripts/contrast-check.mjs) all pairs AA, reviewer recomputed three independently. Reviewer verified number identity API-vs-rendered exact on the reference asset.
     Two out-of-web changes made and re-gated (both PASS): additive optional coordinates on the comparables payload (a deployed Vercel app cannot read the local parquet; latitude/longitude per comp, subject_latitude/subject_longitude on the response; spot-checked against the parquet; no existing field changed), and a module-level threading.Lock around the matplotlib waterfall render in models/explain/shap_explainer.py (matplotlib global state is not thread-safe; concurrent API requests raced with IndexError inside shap.plots.waterfall; reviewer reproduced 8 failures in 16 concurrent renders without the lock, 0 with it; Streamlit never hit it because it called endpoints sequentially). Known ceiling, user-noted: the lock serializes SHAP rendering; if throughput ever matters, switch the render to matplotlib's object-oriented API (explicit Figure, no global pyplot state) and drop the lock. Fine as-is for a demo.
     User-recorded judgment call: the agent was told to render a SHAP waterfall and refused on honesty grounds; a bridge chart from only the top 5 of 38 features fabricates the intermediate cumulative totals it appears to show. Diverging bars with an on-screen top-5 note are the honest chart. Marian confirmed the override was correct.
  The framework-agnostic honesty rules for the API and every frontend are in the spec's Section 2 Phase 6B addendum. Deploy folds into Phase 7, all free: API Docker image on Hugging Face Spaces, Next.js on Vercel Hobby, CORS from Vercel to the Space, backend URL as a frontend env var, cold start noted in the README.
- **Phase 7 — MLOps and deploy: BUILT AND LIVE, reviewer gate pending.** Live
  stack: API https://property-valuation-api-f5et.onrender.com (Render free,
  Docker), frontend https://web-two-ebon-18.vercel.app (Vercel Hobby), model
  bundle MarianGarabana/property-valuation-model at immutable revision e7ab195.
  CI: red at the first Phase 7 gate (the pred_contrib commit dropped a blank
  line, flake8 E302, and the lead recorded "CI green" without rechecking after
  that push; reviewer caught both the red runs and the false claim). Fixed and
  re-verified green before the re-gate. Drift check in mlops/drift.py. CORS pinned to the Vercel origin and verified refused for a
  foreign origin. Deployed number identity exact at full precision on the
  reference asset. The old CI note about R and a sample parquet was moot: the
  full parquet has been git-tracked since Phase 1.
  Deploy war stories, each measured and fixed at the root:
  1. HF paywalled Docker Spaces mid-deploy (see governance log); Render
     substituted.
  2. macOS bsdtar contaminated the model tarball with binary xattr pax records;
     MLflow crashed reading them as UTF-8. Repacked with python tarfile.
  3. Absolute file:///Users/... artifact URIs in the MLflow meta.yaml broke
     artifact download in the container; sed rewrite at build plus a build-time
     model-resolution check so the class fails builds, not runtimes.
  4. shap.TreeExplainer init spiked to 683MB peak (measured) and OOM-killed the
     512MB instance. Replaced with LightGBM's native pred_contrib: identical
     SHAP values (allclose verified; the suite's additivity test holds), 372MB
     peak. Every Phase 3 artifact stays valid. OMP_NUM_THREADS=1 and
     MALLOC_ARENA_MAX=2 also set on the image.
- **Phase 8 — Final review (reviewer on Fable 5).** Full pass against Section 2, honesty constraints visible, no paid dependency, model card and demo script.
- **Stretch (after Phase 8).** RL module (budget-constrained re-valuation ordering or retrofit sequencing), Barcelona/Valencia expansion, physical-climate-risk overlay.

### Phase 2 addendum — per-property CQR intervals (complete, reviewer-passed)

The global homoscedastic band was replaced in two steps, both on the untouched
14,437-row test set, all numbers lead-verified against MLflow:

| Band | Test coverage | Mean width (EUR) |
|---|---|---|
| Old additive residual (flat) | 0.8992 | 189,853 |
| Raw LightGBM quantile (q05/q95) | 0.8267 | 171,180 |
| CQR-calibrated quantile (shipped) | 0.9030 | 194,345 |

The raw quantile band had the right per-property shape (cheap flat width 75k vs
expensive 1.0M after calibration, ~13x) but undercovered at 0.8267 because
regularized LightGBM quantile fits have narrow tails. Fix: standard split-
conformal CQR, user-prescribed. Conformity scores E = max(q05 - y, y - q95) on
the 11,550 validation rows only, Q = 11,594 EUR at the ceil((n+1)*0.90)/n
quantile, shipped band [q05 - Q, q95 + Q] with low <= estimate <= high enforced
(14 of 14,437 rows corrected, 0 crossings). Coverage measured on test, never
tuned there; the reviewer recomputed Q independently and confirmed. Point
estimate and its metrics unchanged. Concept: conformal prediction measures how
far the raw band missed on held-out data and pads every interval by that
amount, which is what buys the finite-sample coverage guarantee the raw
quantile models lack.

MLflow now logs coverage on every retrain (`test_interval_coverage` plus raw
coverage, widths, calibration_q, correction count), so future retrains prove
their own calibration. Retagging is atomic (tag new production run before
clearing stale tags); an earlier empty-tag window had briefly broken the Phase 3
cache build. predict() returns nominal 0.90 and measured 0.9030 side by side.

### Phase 3 — Explainability (complete, reviewer-passed)

Built in `models/explain/`: `shap_explainer.py` (TreeExplainer over the
production booster, resolved through the same MLflow production tag predict.py
uses), `labels.py` (plain-language driver text per the domain skill's writing
rules, every clause carries a concrete EUR number), `explain.py` (one entry
point returning estimate, range from predict.py, five signed EUR drivers,
driver text, plot), `cache.py`.

Cache: full-dataset precompute chosen after a timing test (TreeExplainer over
all 72,185 rows x 38 features took 441 seconds, one-time). Layout:
`cache/shap_values.parquet` (28MB, asset_id + per-feature SHAP + base value +
prediction) and `cache/global_importance.parquet` (mean abs SHAP, 38 features).
explain() hits the cache by asset_id and recomputes only for unseen or
user-entered properties. Additivity verified: SHAP values plus base equal the
prediction exactly.

Defect found by the reviewer and fixed in scope: the shipped cache parquets
were unreadable in the reviewer's environment (pyarrow writer/reader version
skew) while the round-trip test passed by writing fresh tmp files. Read path
switched to polars (version-tolerant). Two hardening steps followed by the
lead: `requirements.txt` pyarrow pin corrected from 25.0.0 to the actually
installed 24.0.0 (the pin had never matched the venv), and a test added that
reads the shipped cache files, not a tmp round-trip. Lesson recorded: a test
that exercises a fresh artifact does not prove the shipped artifact loads.

Tests: 28 passing total (12 data validation, 9 tabular including the CQR
coverage-tolerance and ordering-invariant tests, 7 explain).

### Phase 4 — Vision (complete, closed at the gate)

Full record in the roadmap entry below and in `models/image/README.md`. Summary:
leakage-controlled CNN probe built and evaluated on a 20k PNOA tile subset,
signal above chance but weak (tile AUC 0.5929), measured redundant against the
existing condition feature in a scoped ablation (MAE +303, RMSE +386, MAPE
+0.10pp on the same 4,048 val listings), dropped from the value model per the
honest-AVM rule. Ships as a documented capability demo. Code committed under
`models/image/`; the derived artifacts (`tile_assignment.parquet`,
`subset_manifest.parquet`, `features_subset.npz`) are deterministic outputs of
the scripts and gitignored per the artifact policy (git is not the model
store). Tile images live in `data/images/` (gitignored).

### Phase 5 — Agentic copilot (complete, reviewer-passed)

Built in `agents/`: LangGraph graph (`graph.py`) fanning out from START to
comparables, valuation, and energy nodes, all joining at narrative, then END.
State is a TypedDict; tool-node failures are caught per node and recorded in an
additive `errors` list, so one failed agent degrades the report instead of
killing it. The narrative fails closed if valuation is missing: no number ever
renders without its range and drivers.

- `comparables_agent.py`: same property_type pool, haversine distance in
  polars expressions, score = distance_km + area_diff/20 + 0.7 * rooms_diff,
  top 5, deterministic tie-break on asset_id. Every comp carries a "why" line
  and its real asset_id.
- `valuation_agent.py`: thin composition of Phase 2 `predict.py` (estimate +
  CQR range + measured coverage) and Phase 3 `explain.py` (SHAP drivers).
- `energy_agent.py`: rule-based EPC proxy from build year and condition
  (C >= 2007 or new, E 1980-2006, F pre-1980 with the energy-risk flag,
  unknown for missing/invalid years). Value impact is the observed median
  asking EUR/m2 gap between pre-1980 and post-2006 stock, barrio-scoped when
  both segments have >= 20 listings, else citywide, always with scope and
  sample sizes, always worded as an observed asking-price difference, never a
  measured rating effect.
- `narrative_agent.py`: builds a deterministic facts list, prompts the LLM to
  phrase it, then validates the output: number-fidelity gate (every figure in
  the prose must appear in the facts; regex handles comma grouping and
  decimals), forbidden characters (em/en dash, curly quotes), banned-word
  list, required verbatim sentences (estimate, range, measured coverage,
  2018 caveat, energy disclaimer). Any violation falls back to a labeled
  template assembled directly from the facts, which must pass the same
  validation or the node raises. Reviewer stress-tested the regex on
  decimals, comma-grouped numbers, and percentages: no false accepts.
- `llm.py`: backend detection at call time. Local Ollama first, then Gemini
  free tier via service account, else template. `COPILOT_DISABLE_LLM=1`
  forces the template path for deterministic tests. No paid API.

The three user-set LLM-boundary rules are implemented and test-covered:
number fidelity with fallback, energy impact grounded and disclaimed, 2018
caveat inline in every narrative. The Phase 6 display rule is already honored:
the narrative prints "90% nominal interval that covered 90.3% of held-out test
properties when measured", never a bare 90% claim.

End-to-end evidence: `agents/run_samples.py` ran the graph on three real
listings at the 10th/50th/90th price percentiles (cheap Pueblo Nuevo flat, mid
Numancia duplex, expensive Lista flat). All three narratives combined
estimate + range + coverage, SHAP drivers, five verified comparables, and the
energy band with its disclaimed impact. In this environment no LLM backend is
reachable, so the labeled template path is the live path; that is the designed
honest outcome.

Defect found and fixed during closeout: `models/explain/labels.py` printed the
distance features as meters with zero decimals ("distance to the city center
(4 m)") while the data is in kilometers (mean 4.5, max 13.3 km to center).
Root cause: the original idealista18 docs wording said meters and Phase 3
copied it; the schema docstrings were corrected to kilometers and labels.py
now formats "{v:.1f} km". Display-only, no model or cache artifact touched.

Shared-file edits, lead-authored per the sole-writer rule: `requirements.txt`
+langgraph==1.2.9, `etl/schema.py` distance-unit docstrings meters to
kilometers (verified against the data), `.gitignore` +data/images/ and the
derived image artifacts.

Tests: 38 passing total (12 data validation, 9 tabular, 7 explain, 10
agents). Agent tests cover end-to-end graph run, estimate/range presence, measured coverage,
writing rules, 2018 caveat, energy wording with segment minimums, number-
injection rejection, comps verified against the parquet, band rules, and the
forced template fallback. Reviewer verdict: PASS.

### Open items and pending flags

- **Phase 6 display rule (permanent, user-set).** The dashboard and the copilot
  surface the MEASURED interval coverage and never print a bare "90% confidence
  interval" over a band that does not cover 90%. If the conformal band lands near
  0.90 measured, "90%" becomes an honest label, but the rule is
  display-measured-never-inflate, forever. Goes verbatim into the frontend and
  agent-builder dispatches.
- **Phase 5 LLM-boundary rules: implemented and test-covered (see Phase 5 build
  log).** They remain standing rules for any future narrative change: number
  fidelity with template fallback, energy impact grounded and disclaimed, 2018
  caveat inline.
- **LLM live-path check before Phase 8 (user-set, scheduled).** The narrative
  LLM path has never executed in this environment (no backend reachable); only
  the template fallback has run. Before the Phase 8 final review: start Ollama
  once, run real narratives through it, judge the phrasing quality, and record
  how often the LLM output trips the validator and falls back to the template.
  Not blocking Phase 6 or 7.
- **Kaggle.** Add `~/.kaggle/kaggle.json` if the secondary source is wanted later.
- **CI data strategy.** Decide the test fixture (small committed sample parquet) so CI does not need R at runtime.
- **Deploy cache strategy (Phase 7).** The SHAP cache is gitignored (derived,
  deterministic, 28MB per regeneration). The deployed app must get it another
  way: rebuild at startup (441s one-time, e.g. behind a Streamlit resource
  cache) or fetch it as an MLflow/release artifact. Decide in Phase 7 alongside
  the CI fixture.

---

## Update protocol

At the end of each phase, the orchestrator appends to this file: what was done (with numbers from executed code, never estimated), issues faced, decisions and their reasoning, concepts applied, and any new open items. Move completed pending flags out of the open-items list. Keep the prose rules from Section 2. This file plus the four project docs are the full context handoff for any new session.
