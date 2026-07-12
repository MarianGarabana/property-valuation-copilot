# Model Card: Explainable Property Valuation Copilot

## Model

- Type: LightGBM regressor (LightGBM 4.6.0), predicting the asking price of a Madrid
  residential listing from 38 tabular features.
- Version: MLflow run `f52e8fc77a9d4a528d48e6ff6103b3b2`, experiment `phase2_tabular`,
  tagged `is_production=true`. The deployed API fetches this exact run as a tarball from
  the public Hugging Face repo `MarianGarabana/property-valuation-model`, pinned to
  immutable revision `e7ab195a35fbad3ce6bc9df2eb749c3977577b2e`.
- A PyTorch tabular neural network was trained side by side and lost to the baseline on
  every metric (MAE 48,325 vs 42,301; RMSE 85,431 vs 74,500; MAPE 14.28 vs 12.78). The
  comparison is in `models/tabular/comparison.md`. LightGBM is the production model.

## Training data

- Source: the idealista18 open dataset, about 94,800 Madrid listings from 2018 with
  asking prices, indoor features, and coordinates.
- These are asking prices, not closed sale prices. Every estimate is an estimated market
  value derived from asking-price data, and the app labels it that way.
- This is a historical prototype on 2018 data, not a live market feed. That caveat
  appears in the README, on every page of both frontends, and inside every API payload.
- No data was scraped from idealista or any restricted portal. The idealista API is
  partner-only and was never used.
- Processing: 94,815 raw rows were deduplicated to one row per asset (75,804), filtered
  for validity (75,763), and trimmed of 1%/99% quantile outliers on price, area, and unit
  price, leaving 72,185 rows in `data/processed/listings.parquet`. Neighborhoods come
  from a point-in-polygon join against 135 Madrid barrios (99.90% matched).

## Evaluation

- One fixed held-out split, `random_seed42_train64_val16_test20`, keyed on `asset_id` and
  persisted as `models/tabular/split_assignment.parquet`: train 46,198, validation
  11,550, test 14,437. All reported numbers come from that test set and were never used
  for tuning.
- Held-out test metrics (from MLflow, reproduced from the live `/health` endpoint):
  MAE 42,301.32 EUR, RMSE 74,500.47 EUR, MAPE 12.78%.
- Leakage controls: `unit_price_m2` (price divided by area) and `price` are excluded from
  the model features. Feature importance was audited after the first fit; area carries
  56.7% of gain, neighborhood 16.5%, bathrooms 10.5%.

## Confidence interval

- Method: conformalized quantile regression (CQR). LightGBM quantile models (q05, q95)
  give a per-property band; split-conformal calibration on the 11,550 validation rows
  pads it by Q = 11,593.72 EUR so the band earns finite-sample coverage.
- Nominal level 90%. Measured coverage on the untouched test set: 0.9029576781879892,
  shown everywhere as 90.3%. The interval is always labeled with the measured number,
  never a bare "90%".
- The band is per-property: cheap flats get intervals around 75k EUR wide, expensive ones
  around 1.0M EUR. Mean width 194,345 EUR.

## Explainability

- Method: LightGBM's native `pred_contrib`, which returns exact TreeSHAP values. It was
  verified equal to `shap.TreeExplainer` output (allclose) and the additivity property
  holds: SHAP values plus the base value equal the prediction exactly.
- Every estimate ships with its top five signed EUR drivers, plain-language driver text,
  and a SHAP plot. The API refuses to return an estimate without at least one driver.

## The CNN condition score: evaluated and dropped

A CNN condition feature was built, evaluated under explicit spatial-leakage controls, and
measured redundant, so it does not feed the model. The full write-up is
`models/image/README.md` and the "CNN study" page on the live site.

- Probe: frozen ResNet18 features plus a class-balanced logistic head over PNOA aerial
  tiles, predicting the existing `condition` label (never price, which would launder the
  target through the image model).
- Leakage control: no tile straddles CNN training and the listings it scores. 41,757
  pure-train tiles trained the probe; 25,235 tiles holding any val/test listing were
  excluded; all scores are out-of-fold.
- Signal on a tile-disjoint holdout: tile ROC AUC 0.5929 (chance 0.5), balanced accuracy
  0.5544, listing-level AUC 0.5924 on 4,048 validation listings. Above chance, weak.
- Ablation on the same 4,048 listings with production hyperparameters: adding the score
  moved MAE +303 EUR, RMSE +386 EUR, MAPE +0.10 points. No lift, slight harm.
- Decision: the score stays null and out of the model. `cnn_condition_score` never
  appears in the live valuation flow; posting it to the API has no effect on the
  estimate (verified on the deployed service).

## Intended use and limitations

- Intended use: a portfolio and teaching prototype of an explainable AVM. It shows how a
  valuation package (estimate, range, drivers, comparables, energy flag, narrative)
  can be assembled honestly on a free stack.
- Not a live valuation tool. The data is 2018 asking prices; the estimates say nothing
  about today's market and must not inform lending, buying, or selling decisions.
- The energy value impact is an observed asking-price difference between age bands, not a
  measured effect of the energy rating, and it is labeled that way everywhere.
- The demo API is unauthenticated by design (free public demo). A real deployment would
  put a key or an auth proxy in front of it.
- The drift check (`mlops/drift.py`) covers input drift only; with no live price feed,
  label drift cannot be measured at all.
- The copilot narrative validates every number against computed facts and falls back to a
  labeled template when the LLM output fails validation; the deployed service runs the
  template path.
- The validator was tested against a live LLM (llama3.1:8b via local Ollama, 10
  properties): it correctly rejected all 9 non-compliant narratives and fell back safely
  to the labeled template every time, with no call failures. Every rejection was a
  missing mandatory disclaimer sentence. The model never fabricated a figure, so the
  number-fidelity check is present and untriggered, not proven in fire; the run shows
  the completeness guard working, not fabrications being caught.

## Licenses and attributions

- idealista18: open dataset released by its authors at github.com/paezha/idealista18;
  see that repository for its terms.
- PNOA aerial imagery (CNN study only): IGN Spain, CC-BY 4.0. Required attribution:
  "Obra derivada de PNOA CC-BY 4.0 scne.es".
- Map tiles in the web frontend: OpenFreeMap, keyless and free.
- All libraries are open source (Polars, scikit-learn, LightGBM, PyTorch, SHAP,
  LangGraph, Streamlit, MLflow, FastAPI, Next.js). Hosting is Render free tier and
  Vercel Hobby. Recurring cost: zero.
