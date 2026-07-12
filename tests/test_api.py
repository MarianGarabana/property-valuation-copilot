import json
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
for _p in (
    str(REPO_ROOT),
    str(REPO_ROOT / "models" / "tabular"),
    str(REPO_ROOT / "models" / "explain"),
):
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.environ.setdefault("COPILOT_DISABLE_LLM", "1")

from fastapi.testclient import TestClient

import etl.schema  # noqa: F401
import predict as tabular_predict
import explain as tabular_explain
from agents import comparables_agent, energy_agent
from agents.data import get_subject
from agents.narrative_agent import CAVEAT, ENERGY_DISCLAIMER
from api.main import app

ASSET_ID = "A15019136831406238029"

client = TestClient(app)
client_no_reraise = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(scope="module")
def subject():
    return get_subject(ASSET_ID)


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["model"]["model_type"] == "lightgbm"


def test_estimate_number_identity(subject):
    direct = tabular_explain.explain(subject)
    interval = tabular_predict.predict_one(subject)
    r = client.get(f"/v1/estimate/{ASSET_ID}")
    assert r.status_code == 200
    body = r.json()
    assert body["estimate"] == direct["estimate"]
    assert body["low"] == direct["low"]
    assert body["high"] == direct["high"]
    assert body["interval_coverage"] == direct["interval_coverage"]
    assert body["interval_test_coverage"] == interval["interval_test_coverage"]
    assert body["driver_text"] == direct["driver_text"]
    for got, want in zip(body["top_drivers"], direct["top_drivers"]):
        assert got["shap_eur"] == want["shap_eur"]


def test_estimate_carries_range_and_drivers(subject):
    body = client.get(f"/v1/estimate/{ASSET_ID}").json()
    assert "low" in body and "high" in body
    assert len(body["top_drivers"]) >= 1
    assert body["shap_plot_png_base64"]


def test_comparables_number_identity(subject):
    direct = comparables_agent.run(subject)
    body = client.get(f"/v1/comparables/{ASSET_ID}").json()
    assert body["price_min"] == direct["price_min"]
    assert body["price_max"] == direct["price_max"]
    assert body["price_median"] == direct["price_median"]
    assert body["max_distance_km"] == direct["max_distance_km"]
    for got, want in zip(body["comps"], direct["comps"]):
        assert got["price"] == want["price"]
        assert got["distance_km"] == want["distance_km"]


def test_energy_number_identity_and_disclaimer(subject):
    direct = energy_agent.run(subject)
    body = client.get(f"/v1/energy/{ASSET_ID}").json()
    assert body["band"] == direct["band"]
    assert body["effective_year"] == direct["effective_year"]
    for k in ("median_old_eur_m2", "gap_eur_m2", "subject_gap_eur", "n_old", "n_new"):
        assert body["impact"][k] == direct["impact"][k]
    assert body["energy_disclaimer"] == ENERGY_DISCLAIMER


def test_copilot_narrative_shape():
    r = client.get(f"/v1/copilot/{ASSET_ID}")
    assert r.status_code == 200
    body = r.json()
    assert body["text"]
    assert body["narrative_source"]
    assert "facts" in body
    assert isinstance(body["errors"], list)


def test_copilot_template_fallback_returns_200(monkeypatch):
    monkeypatch.setenv("COPILOT_DISABLE_LLM", "1")
    r = client.get(f"/v1/copilot/{ASSET_ID}")
    assert r.status_code == 200
    assert r.json()["narrative_source"] == "template"


def test_caveat_in_every_estimate_payload():
    for path in (
        f"/v1/estimate/{ASSET_ID}",
        f"/v1/comparables/{ASSET_ID}",
        f"/v1/energy/{ASSET_ID}",
        f"/v1/copilot/{ASSET_ID}",
    ):
        assert client.get(path).json()["caveat"] == CAVEAT


def test_fail_closed_unknown_asset():
    r = client.get("/v1/estimate/DOES_NOT_EXIST")
    assert r.status_code == 404
    body = r.json()
    assert "error" in body
    assert "estimate" not in body and "low" not in body


def test_fail_closed_backend_error_no_partial_numbers():
    r = client_no_reraise.post("/v1/comparables", json={"property_type": "flat", "area_m2": 90, "rooms": 3})
    assert r.status_code == 500
    body = r.json()
    assert set(body.keys()) == {"error"}


def test_no_cnn_condition_score_anywhere():
    for path in (
        f"/v1/estimate/{ASSET_ID}",
        f"/v1/comparables/{ASSET_ID}",
        f"/v1/energy/{ASSET_ID}",
        f"/v1/copilot/{ASSET_ID}",
        "/health",
    ):
        assert "cnn_condition_score" not in json.dumps(client.get(path).json())


def test_posted_property_strips_cnn_condition_score():
    payload = {
        "area_m2": 90,
        "rooms": 3,
        "bathrooms": 2,
        "floor": 4,
        "property_type": "flat",
        "condition": "good",
        "construction_year": 1995,
        "latitude": 40.42,
        "longitude": -3.70,
        "cnn_condition_score": 0.9,
    }
    r = client.post("/v1/estimate", json=payload)
    assert r.status_code == 200
    assert "cnn_condition_score" not in json.dumps(r.json())
    assert len(r.json()["top_drivers"]) >= 1
