from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from agents.narrative_agent import CAVEAT, ENERGY_DISCLAIMER


class Envelope(BaseModel):
    caveat: str = CAVEAT


class ErrorDetail(BaseModel):
    type: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class PropertyInput(BaseModel):
    model_config = ConfigDict(extra="allow")

    asset_id: Optional[str] = None
    area_m2: Optional[float] = None
    rooms: Optional[int] = None
    bathrooms: Optional[int] = None
    floor: Optional[float] = None
    property_type: Optional[str] = None
    condition: Optional[str] = None
    construction_year: Optional[int] = None
    cad_construction_year: Optional[int] = None
    property_age: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    neighborhood_id: Optional[str] = None
    neighborhood_name: Optional[str] = None


class Driver(BaseModel):
    feature: str
    value: Any = None
    shap_eur: float
    description: str


class EstimateResponse(Envelope):
    asset_id: Optional[str] = None
    estimate: float
    low: float
    high: float
    interval_coverage: float
    interval_test_coverage: float
    top_drivers: List[Driver]
    driver_text: str
    shap_plot_png_base64: str

    @field_validator("top_drivers")
    @classmethod
    def _drivers_present(cls, v):
        if not v:
            raise ValueError("estimate response requires at least one SHAP driver")
        return v


class Comparable(BaseModel):
    asset_id: str
    price: float
    area_m2: float
    rooms: int
    bathrooms: int
    property_type: str
    neighborhood_name: Optional[str] = None
    distance_km: float
    why: str


class ComparablesResponse(Envelope):
    asset_id: Optional[str] = None
    method: str
    n: int
    comps: List[Comparable]
    price_min: float
    price_max: float
    price_median: float
    max_distance_km: float


class EnergyImpact(BaseModel):
    scope: str
    n_old: int
    n_new: int
    median_old_eur_m2: int
    median_new_eur_m2: int
    gap_eur_m2: int
    subject_area_m2: int
    subject_gap_eur: int


class EnergyResponse(Envelope):
    asset_id: Optional[str] = None
    band: str
    band_is_proxy: bool
    flag: bool
    effective_year: Optional[int] = None
    year_source: Optional[str] = None
    impact: Optional[EnergyImpact] = None
    energy_disclaimer: str = ENERGY_DISCLAIMER


class CopilotResponse(Envelope):
    asset_id: Optional[str] = None
    text: str
    narrative_source: str
    facts: Optional[str] = None
    errors: List[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    model: dict
