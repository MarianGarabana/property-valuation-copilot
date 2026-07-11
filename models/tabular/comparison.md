# Phase 2 tabular model comparison

Data: idealista18 2018 Madrid asking prices (historical prototype).
Split: random_seed42_train64_val16_test20 (seed 42). Train 46198 / val 11550 / test 14437.
Metrics below are on the held-out test split only.

| Model | MAE (EUR) | RMSE (EUR) | MAPE (%) |
|---|---|---|---|
| LightGBM baseline | 42,301 | 74,500 | 12.78 |
| PyTorch tabular NN | 48,325 | 85,431 | 14.28 |

Winner (lowest test MAE): LightGBM baseline. Saved as the production artifact.

Confidence range: conformalized per-property LightGBM quantile regression (CQR).
Two extra LightGBM models with objective=quantile at alpha 0.05 and 0.95 give a
central interval whose width scales with the property. Split-conformal calibration on the
validation split (11550 rows, never test) pads both ends by a single Q = 11,594 EUR,
the ceil((n+1)*0.90)-th conformity score, which restores marginal coverage while keeping
the per-property shape. The point estimate stays from the production point model.

Interval coverage and width (held-out test, 14437 rows):

| Band | Test coverage | Mean width (EUR) |
|---|---|---|
| Old additive residual (homoscedastic) | 0.8992 | 189,853 (constant) |
| Raw LightGBM quantile (per-property) | 0.8267 | 171,180 |
| CQR-calibrated quantile (shipped) | 0.9030 | 194,345 |

The raw quantile band undercovered at 0.8267. CQR padding by Q = 11,594 EUR
lifts test coverage to 0.9030, near the 0.90 nominal, measured
on the untouched test set (Q was fixed on validation, never tuned on test). The band stays
per-property: the additive Q shifts both ends by the same amount but the base quantile
spread differs by property, so cheap listings keep a narrower band than expensive ones.
Ordering low <= estimate <= high is enforced; 14 of 14437 test
rows needed a correction. The old additive band gave every property the same euro
width, which is not credible on cheap listings.

Top LightGBM feature importances (gain share):
- area_m2: 56.7%
- neighborhood_id: 16.5%
- bathrooms: 10.5%
- rooms: 3.0%
- distance_to_castellana: 2.2%
- latitude: 1.8%
- distance_to_city_center: 1.5%
- floor: 1.2%
