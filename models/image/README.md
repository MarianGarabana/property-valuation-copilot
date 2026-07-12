# Image model: PNOA condition probe (capability demo)

This module is the Phase 4 vision work: a leakage-controlled CNN pipeline over aerial
imagery, built, evaluated, and then measured redundant against the existing `condition`
feature. On that measurement the score was dropped from the value model. The pipeline
ships as a documented capability demo, per the project's honest-AVM rule. Nothing here
feeds the production model: `cnn_condition_score` in `listings.parquet` stays null.

## Outcome in one paragraph

A frozen ResNet18 probe over aerial tiles predicts the listing `condition` label above
chance on tiles it never trained on (ROC AUC 0.5929 vs 0.5). But the value model already
holds `condition` as a clean tabular feature, so the CNN score is by construction a noisy
compression of a known input. A scoped ablation confirmed it: adding the score to the
LightGBM value model changed held-out error by MAE +303 EUR, RMSE +386 EUR, MAPE +0.10
points on the same 4,048 validation listings. No lift, slight harm. The honest outcome is
a controlled evaluation with a measured negative, and the feature does not ship.

## Data source and license

- Imagery: PNOA "Maxima Actualidad" orthophotos from IGN Spain, fetched through the free
  public WMS endpoint `https://www.ign.es/wms-inspire/pnoa-ma`, layer
  `OI.OrthoimageCoverage`. No API key, no cost.
- License: CC-BY 4.0 under Orden Ministerial FOM/2807/2015. The service self-describes as
  `AccessConstraints: CC BY 4.0 scne.es` and `Fees: No se aplican condiciones` (checked in
  GetCapabilities before any download).
- Required attribution: "Obra derivada de PNOA CC-BY 4.0 scne.es".
- Honesty caveat: PNOA imagery is from recent flights, joined to 2018 listings by
  coordinate. Buildings and urban fabric mostly persist, but the dates do not match.
- idealista18 ships no images, and fetching listing thumbnails would mean hitting
  idealista, which is banned for this project. Aerial tiles were the only clean path.

## Tile design and the straddle-exclusion rule

Each tile is a 256x256 JPEG (about 0.47 m per pixel, roughly 120 m square) centered on
the listing coordinate rounded to 4 decimals. The 72,185 listings map to 66,992 tiles, so
some tiles hold more than one listing, and the value-model split is on `asset_id`. A tile
can therefore hold a train listing and a val or test listing at once. A CNN that
memorizes tiles would leak split information into the score and fake a gain in the
with/without comparison.

The rule applied: no tile may straddle the CNN's training set and the listings it scores.
Executed numbers: 41,757 tiles contain only train listings and are the only tiles the CNN
may train on; 25,235 tiles contain at least one val or test listing and are excluded from
CNN training entirely; 2,486 train listings sit on those excluded tiles and are excluded
from CNN training too. All scoring is out-of-fold: train listings get 5-fold
tile-grouped out-of-fold scores, and eval listings get scores from a probe that never saw
their tiles.

## What was measured

Downloaded subset (gated; the full 67k download was intentionally never run): 19,997 of
20,000 stratified tiles, 16,000 pure-train and 4,000 validation-listing tiles, 1,155
seconds at 17.3 tiles per second, about 460 MB.

Probe: frozen ResNet18 (ImageNet weights) 512-dim features, standardized, class-balanced
logistic head. Binary label: condition good or new vs needs_renovation, train-split
labels only. Never price or unit price as the CNN target; that would launder the
regression target through the image model.

Signal on the tile-disjoint holdout (baselines beside each number):

| Metric | Value | Know-nothing baseline |
|---|---|---|
| Tile ROC AUC | 0.5929 | 0.5 |
| Tile balanced accuracy | 0.5544 | 0.5 |
| Tile average precision | 0.8716 | 0.8217 (class prior) |
| Listing ROC AUC (4,048 val listings) | 0.5924 | 0.5 |

Stable across probe regularization (AUC 0.5939 / 0.5929 / 0.5926 at C = 0.01 / 0.1 / 1.0).

Ablation: LightGBM with the production Phase 2 hyperparameters, trained on 15,107 subset
train listings, early stopping on a tile-disjoint 1,606-listing stop set identical for
both runs, evaluated on the same 4,048 validation listings in both runs.

| Metric (4,048 val listings) | Without score | With score | Delta |
|---|---|---|---|
| MAE (EUR) | 48,580 | 48,884 | +303 (+0.63%) |
| RMSE (EUR) | 84,124 | 84,510 | +386 (+0.46%) |
| MAPE (%) | 14.41 | 14.51 | +0.10 pp |

The model did use the feature (gain share 0.27%), and every metric got slightly worse.

## Why the ceiling was redundancy, not AUC

The CNN was trained to predict `condition`, and `condition` is already a clean feature in
the value model, so the score is a noisy copy of something the model knows exactly.
Fine-tuning would sharpen the copy, but a sharper copy of an existing feature is still
redundant. The only way an image helps is signal orthogonal to `condition` that
correlates with price, and training on the `condition` target throws that away.
Retargeting the CNN to price is banned as target leakage. So the path was capped low by
design, the measured 0.59 AUC is consistent with that cap, and the ablation turned "we
assume it adds nothing over condition" into "we measured that it adds nothing over
condition."

## Defect log

The first ablation run produced byte-identical with and without results, which was the
tell. Root cause: `listings.parquet` carries an all-null `cnn_condition_score`
placeholder column, and the polars join silently renamed the real probe scores to
`cnn_condition_score_right`, so LightGBM received the null placeholder. Fix: drop the
placeholder before the join, plus a non-null assertion on the score column. Any future
code joining a real score onto `listings.parquet` collides with that placeholder by name.

## Files

- `tiles.py`: tile assignment, straddle exclusion, stratified subset manifest.
- `download_tiles.py`: polite resumable WMS fetch of the subset manifest.
- `train_subset_cnn.py`: feature extraction and the linear-probe signal test.
- `ablation_subset.py`: out-of-fold scoring and the with/without value-model ablation.

Run everything with the repo venv interpreter, from this directory:

```
../../.venv/bin/python tiles.py
../../.venv/bin/python download_tiles.py
../../.venv/bin/python train_subset_cnn.py
../../.venv/bin/python ablation_subset.py
```

Downloads land in `data/images/tiles/` (gitignored). Derived artifacts here
(`tile_assignment.parquet`, `subset_manifest.parquet`, `features_subset.npz`) are
deterministic and reproducible from the scripts above.
