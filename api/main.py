import base64
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for _p in (
    str(REPO_ROOT),
    str(REPO_ROOT / "models" / "tabular"),
    str(REPO_ROOT / "models" / "explain"),
):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

import predict as tabular_predict
import explain as tabular_explain
from agents import comparables_agent, energy_agent
from agents.data import get_subject
from agents.graph import run_copilot

from api.models import (
    Comparable,
    ComparablesResponse,
    CopilotResponse,
    Driver,
    EnergyImpact,
    EnergyResponse,
    EstimateResponse,
    HealthResponse,
    PropertyInput,
)

app = FastAPI(title="Property Valuation Copilot API", version="1.0.0")
v1 = APIRouter(prefix="/v1")

_origins_env = os.environ.get("API_CORS_ORIGINS", "*")
_origins = [o.strip() for o in _origins_env.split(",") if o.strip()] or ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _error_body(exc_type, message):
    return {"error": {"type": exc_type, "message": message}}


@app.exception_handler(StarletteHTTPException)
async def _http_exc_handler(request, exc):
    detail = exc.detail if isinstance(exc.detail, str) else "http_error"
    return JSONResponse(status_code=exc.status_code, content=_error_body("http_error", detail))


@app.exception_handler(RequestValidationError)
async def _validation_exc_handler(request, exc):
    return JSONResponse(status_code=422, content=_error_body("validation_error", str(exc.errors())))


@app.exception_handler(Exception)
async def _unhandled_exc_handler(request, exc):
    return JSONResponse(status_code=500, content=_error_body("backend_error", str(exc)))


def _subject_from_asset(asset_id):
    try:
        return get_subject(asset_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"asset_id {asset_id} not found in listings")


def _subject_from_input(payload: PropertyInput):
    subject = payload.model_dump()
    subject.pop("cnn_condition_score", None)
    return subject


def _build_estimate(subject, asset_id):
    explained = tabular_explain.explain(subject)
    interval = tabular_predict.predict_one(subject)
    drivers = [
        Driver(
            feature=d["feature"],
            value=d.get("value"),
            shap_eur=d["shap_eur"],
            description=d["description"],
        )
        for d in explained["top_drivers"]
    ]
    return EstimateResponse(
        asset_id=asset_id,
        estimate=explained["estimate"],
        low=explained["low"],
        high=explained["high"],
        interval_coverage=explained["interval_coverage"],
        interval_test_coverage=interval["interval_test_coverage"],
        top_drivers=drivers,
        driver_text=explained["driver_text"],
        shap_plot_png_base64=base64.b64encode(explained["plot"]).decode("ascii"),
    )


def _build_comparables(subject, asset_id):
    result = comparables_agent.run(subject)
    comps = [
        Comparable(
            asset_id=c["asset_id"],
            price=c["price"],
            area_m2=c["area_m2"],
            rooms=c["rooms"],
            bathrooms=c["bathrooms"],
            property_type=c["property_type"],
            neighborhood_name=c.get("neighborhood_name"),
            distance_km=c["distance_km"],
            why=c["why"],
        )
        for c in result["comps"]
    ]
    return ComparablesResponse(
        asset_id=asset_id,
        method=result["method"],
        n=result["n"],
        comps=comps,
        price_min=result["price_min"],
        price_max=result["price_max"],
        price_median=result["price_median"],
        max_distance_km=result["max_distance_km"],
    )


def _build_energy(subject, asset_id):
    result = energy_agent.run(subject)
    impact = result.get("impact")
    return EnergyResponse(
        asset_id=asset_id,
        band=result["band"],
        band_is_proxy=result["band_is_proxy"],
        flag=result["flag"],
        effective_year=result["effective_year"],
        year_source=result["year_source"],
        impact=EnergyImpact(**impact) if impact is not None else None,
    )


def _build_copilot(subject, asset_id):
    result = run_copilot(subject)
    text = result.get("narrative")
    if text is None:
        raise HTTPException(
            status_code=502,
            detail="copilot produced no narrative: " + "; ".join(result.get("errors") or []),
        )
    return CopilotResponse(
        asset_id=asset_id,
        text=text,
        narrative_source=result.get("narrative_source"),
        facts=result.get("narrative_facts"),
        errors=result.get("errors") or [],
    )


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok", model=tabular_predict.model_info())


@v1.get("/estimate/{asset_id}", response_model=EstimateResponse)
def estimate_by_asset(asset_id: str):
    return _build_estimate(_subject_from_asset(asset_id), asset_id)


@v1.post("/estimate", response_model=EstimateResponse)
def estimate_posted(payload: PropertyInput):
    return _build_estimate(_subject_from_input(payload), payload.asset_id)


@v1.get("/comparables/{asset_id}", response_model=ComparablesResponse)
def comparables_by_asset(asset_id: str):
    return _build_comparables(_subject_from_asset(asset_id), asset_id)


@v1.post("/comparables", response_model=ComparablesResponse)
def comparables_posted(payload: PropertyInput):
    return _build_comparables(_subject_from_input(payload), payload.asset_id)


@v1.get("/energy/{asset_id}", response_model=EnergyResponse)
def energy_by_asset(asset_id: str):
    return _build_energy(_subject_from_asset(asset_id), asset_id)


@v1.post("/energy", response_model=EnergyResponse)
def energy_posted(payload: PropertyInput):
    return _build_energy(_subject_from_input(payload), payload.asset_id)


@v1.get("/copilot/{asset_id}", response_model=CopilotResponse)
def copilot_by_asset(asset_id: str):
    return _build_copilot(_subject_from_asset(asset_id), asset_id)


@v1.post("/copilot", response_model=CopilotResponse)
def copilot_posted(payload: PropertyInput):
    return _build_copilot(_subject_from_input(payload), payload.asset_id)


app.include_router(v1)
