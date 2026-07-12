import sys
from pathlib import Path

import polars as pl
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agents import energy_agent, narrative_agent
from agents.data import load_listings
from agents.graph import run_copilot
from agents.narrative_agent import (
    CAVEAT,
    ENERGY_DISCLAIMER,
    TEMPLATE_LABEL,
    format_eur,
    validate_narrative,
)

pytestmark = pytest.mark.local_only


@pytest.fixture(scope="module")
def listings():
    return load_listings()


@pytest.fixture(scope="module")
def subject(listings):
    return (
        listings.filter(pl.col("neighborhood_id").is_not_null())
        .sort("asset_id")
        .row(0, named=True)
    )


@pytest.fixture(scope="module")
def result(subject):
    return run_copilot(subject)


def test_graph_runs_end_to_end(result):
    assert isinstance(result["narrative"], str) and result["narrative"]
    assert result["narrative_source"] == "template" or result["narrative_source"].startswith("llm:")
    assert result["valuation"] is not None
    assert result["comps"] is not None
    assert result["energy"] is not None


def test_narrative_contains_estimate_and_range(result):
    valuation = result["valuation"]
    assert format_eur(valuation["estimate"]) in result["narrative"]
    assert format_eur(valuation["low"]) in result["narrative"]
    assert format_eur(valuation["high"]) in result["narrative"]
    assert valuation["low"] <= valuation["estimate"] <= valuation["high"]


def test_narrative_surfaces_measured_coverage(result):
    measured = f"{result['valuation']['interval_test_coverage'] * 100:.1f}"
    assert measured in result["narrative"]


def test_narrative_writing_rules(result):
    problems = validate_narrative(result["narrative"], result["narrative_facts"], [])
    assert problems == []
    assert "—" not in result["narrative"]
    assert "–" not in result["narrative"]


def test_narrative_carries_2018_caveat(result):
    assert CAVEAT in result["narrative"]


def test_narrative_energy_wording(result):
    assert "proxy" in result["narrative"]
    assert ENERGY_DISCLAIMER in result["narrative"]
    impact = result["energy"]["impact"]
    assert impact["n_old"] >= energy_agent.MIN_SEGMENT_N
    assert impact["n_new"] >= energy_agent.MIN_SEGMENT_N
    assert impact["scope"]


def test_number_fidelity_gate_catches_injection(result):
    tampered = result["narrative"] + " A further adjustment of 999,731 euros applies."
    problems = validate_narrative(tampered, result["narrative_facts"], [])
    assert any("numbers not present" in p for p in problems)


def test_comps_are_real_listings(result, listings, subject):
    comps = result["comps"]["comps"]
    assert len(comps) == 5
    for comp in comps:
        assert comp["asset_id"] != subject["asset_id"]
        match = listings.filter(pl.col("asset_id") == comp["asset_id"])
        assert match.height == 1
        assert match["price"][0] == comp["price"]
        assert match["property_type"][0] == subject["property_type"]
        assert comp["why"]


def test_energy_band_rules():
    assert energy_agent.derive_band({"condition": "good", "construction_year": 1950})[:2] == ("F", True)
    assert energy_agent.derive_band({"condition": "good", "construction_year": 1995})[:2] == ("E", False)
    assert energy_agent.derive_band({"condition": "good", "construction_year": 2010})[:2] == ("C", False)
    assert energy_agent.derive_band({"condition": "new"})[:2] == ("C", False)
    assert energy_agent.derive_band(
        {"condition": "good", "construction_year": None, "cad_construction_year": 1623}
    )[:2] == ("unknown", False)


def test_template_fallback_when_no_llm(monkeypatch, subject, result):
    monkeypatch.setenv("COPILOT_DISABLE_LLM", "1")
    text, source, notes, facts_text = narrative_agent.write_narrative(
        subject, result["valuation"], result["comps"], result["energy"]
    )
    assert source == "template"
    assert text.startswith(TEMPLATE_LABEL)
    assert validate_narrative(text, facts_text, []) == []
    assert any("template fallback" in note for note in notes)
