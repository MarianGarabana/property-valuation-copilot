# Phase 2 tabular model comparison

Data: idealista18 2018 Madrid asking prices (historical prototype).
Split: random_seed42_train64_val16_test20 (seed 42). Train 46198 / val 11550 / test 14437.
Metrics below are on the held-out test split only.

| Model | MAE (EUR) | RMSE (EUR) | MAPE (%) |
|---|---|---|---|
| LightGBM baseline | 42,301 | 74,500 | 12.78 |
| PyTorch tabular NN | 48,325 | 85,431 | 14.28 |

Winner (lowest test MAE): LightGBM baseline. Saved as the production artifact.

Confidence range: residual-based. The interval is the point estimate plus the
empirical 90% quantile band of the winning model's validation-set
residuals (y_true minus y_pred), so the band reflects real out-of-sample error
rather than a model-reported variance.

Top LightGBM feature importances (gain share):
- area_m2: 56.7%
- neighborhood_id: 16.5%
- bathrooms: 10.5%
- rooms: 3.0%
- distance_to_castellana: 2.2%
- latitude: 1.8%
- distance_to_city_center: 1.5%
- floor: 1.2%
