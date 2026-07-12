"""Rule-based EPC-band proxy and its data-grounded value impact.

No clean Madrid EPC dataset exists in this repo, so per Section 3 of the
build spec the band is a proxy derived from building age and condition,
never a certificate. Effective year is construction_year when valid, else
cad_construction_year (0 nulls in the data). The rule:

- condition == "new", or effective year >= 2007: band C proxy. The CTE
  (Codigo Tecnico de la Edificacion, 2006) sets modern efficiency
  requirements for new builds.
- 1980 <= year <= 2006: band E proxy. Built under NBE-CT-79, the first
  Spanish insulation code, but before the CTE.
- 1800 <= year <= 1979: band F proxy, energy-risk flag set. Pre NBE-CT-79
  stock had no insulation requirement and carries the EU
  renovation-regulation exposure.
- year < 1800 or missing: unknown (10 rows carry data-error years such
  as 1623).

The value impact is not a measured effect of the rating. It is the
observed median asking EUR/m2 gap between pre-1980 and post-2006 stock,
computed within the subject's barrio when both segments have at least 20
listings (47 of 135 barrios), else citywide, always reported with scope
and sample sizes. The narrative words it as an observed asking-price
difference between age bands.
"""

import sys
from pathlib import Path

import polars as pl

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agents.data import load_listings

VALID_YEAR_MIN = 1800
VALID_YEAR_MAX = 2018
OLD_YEAR_MAX = 1979
NEW_YEAR_MIN = 2007
MID_YEAR_MIN = 1980
MIN_SEGMENT_N = 20


def _effective_year(subject):
    for key in ("construction_year", "cad_construction_year"):
        year = subject.get(key)
        if year is not None and VALID_YEAR_MIN <= year <= VALID_YEAR_MAX:
            return int(year), key
    return None, None


def derive_band(subject):
    year, source = _effective_year(subject)
    if subject.get("condition") == "new":
        return "C", False, year, source or "condition"
    if year is None:
        return "unknown", False, None, None
    if year >= NEW_YEAR_MIN:
        return "C", False, year, source
    if year >= MID_YEAR_MIN:
        return "E", False, year, source
    return "F", True, year, source


def stock_gap(neighborhood_id, neighborhood_name, subject_area_m2):
    frame = load_listings().with_columns(
        pl.coalesce(pl.col("construction_year"), pl.col("cad_construction_year")).alias("_year")
    )
    frame = frame.filter(
        pl.col("_year").is_between(VALID_YEAR_MIN, VALID_YEAR_MAX)
    )
    scopes = []
    if neighborhood_id is not None:
        scopes.append(
            (f"barrio {neighborhood_name}", frame.filter(pl.col("neighborhood_id") == neighborhood_id))
        )
    scopes.append(("Madrid citywide", frame))
    for scope_label, segment in scopes:
        old = segment.filter(pl.col("_year") <= OLD_YEAR_MAX)
        new = segment.filter(pl.col("_year") >= NEW_YEAR_MIN)
        if old.height >= MIN_SEGMENT_N and new.height >= MIN_SEGMENT_N:
            median_old = int(round(old["unit_price_m2"].median()))
            median_new = int(round(new["unit_price_m2"].median()))
            gap_eur_m2 = median_new - median_old
            area = int(round(float(subject_area_m2)))
            return {
                "scope": scope_label,
                "n_old": old.height,
                "n_new": new.height,
                "median_old_eur_m2": median_old,
                "median_new_eur_m2": median_new,
                "gap_eur_m2": gap_eur_m2,
                "subject_area_m2": area,
                "subject_gap_eur": gap_eur_m2 * area,
            }
    return None


def run(subject):
    band, flagged, year, source = derive_band(subject)
    impact = stock_gap(
        subject.get("neighborhood_id"),
        subject.get("neighborhood_name"),
        subject["area_m2"],
    )
    return {
        "band": band,
        "band_is_proxy": True,
        "flag": flagged,
        "effective_year": year,
        "year_source": source,
        "impact": impact,
    }
