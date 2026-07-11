"""Single feature schema for the Madrid AVM.

Every agent references this file. Feature names are snake_case and are not
renamed anywhere else. Source data is idealista18: 2018 Madrid asking-price
listings (four quarterly snapshots of that year). Values are asking prices,
not closed sale prices, and this is a historical prototype, not a live feed.

The schema defines:
- COLUMN_MAP: raw idealista18 column -> snake_case feature name (direct copies).
- FEATURES: every feature the processed table exposes, with dtype, source,
  nullability, and a short description. Derived and placeholder features
  (condition, property_type, property_age, neighborhood_*, cnn_condition_score)
  are listed with source "derived" or "placeholder".
- KEY_COLUMNS: features that must never be null after ETL.
- Cleaning constants: reference year, Madrid bounding box, outlier bounds.
"""

from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_PARQUET_PATH = REPO_ROOT / "data" / "raw" / "idealista18_madrid.parquet"
PROCESSED_PARQUET_PATH = REPO_ROOT / "data" / "processed" / "listings.parquet"

# idealista18 records 2018 asking prices across four quarterly snapshots.
DATA_YEAR = 2018
REFERENCE_YEAR = 2018
DATA_LABEL = "idealista18 2018 Madrid asking-price listings (historical prototype)"

# Madrid municipality bounding box, used to drop coordinate errors. A handful of
# rows carry coordinates far outside Madrid (e.g. latitude ~36.8, Andalusia).
MADRID_BBOX = {
    "lat_min": 40.30,
    "lat_max": 40.60,
    "lon_min": -3.90,
    "lon_max": -3.55,
}

# Outlier rule: after dedupe and hard-validity filters (price > 0, area > 0,
# coordinates inside MADRID_BBOX), drop rows whose price, area_m2, or
# unit_price_m2 fall outside the [lower, upper] sample quantiles below.
OUTLIER_QUANTILES = {"lower": 0.01, "upper": 0.99}
OUTLIER_COLUMNS = ("price", "area_m2", "unit_price_m2")

# Valid construction years; anything outside this range becomes null.
CONSTRUCTION_YEAR_MIN = 1900
CONSTRUCTION_YEAR_MAX = 2018

# Raw BUILTTYPEID one-hot columns -> condition label (idealista18 encoding).
CONDITION_FROM_BUILTTYPE = {
    "BUILTTYPEID_1": "new",
    "BUILTTYPEID_2": "needs_renovation",
    "BUILTTYPEID_3": "good",
}

# Raw column -> snake_case feature name for directly copied columns.
COLUMN_MAP = {
    "ASSETID": "asset_id",
    "PERIOD": "period",
    "PRICE": "price",
    "UNITPRICE": "unit_price_m2",
    "CONSTRUCTEDAREA": "area_m2",
    "ROOMNUMBER": "rooms",
    "BATHNUMBER": "bathrooms",
    "FLOORCLEAN": "floor",
    "CONSTRUCTIONYEAR": "construction_year",
    "LATITUDE": "latitude",
    "LONGITUDE": "longitude",
    "HASTERRACE": "has_terrace",
    "HASLIFT": "has_lift",
    "HASAIRCONDITIONING": "has_air_conditioning",
    "HASPARKINGSPACE": "has_parking",
    "ISPARKINGSPACEINCLUDEDINPRICE": "parking_included_in_price",
    "PARKINGSPACEPRICE": "parking_space_price",
    "HASNORTHORIENTATION": "has_north_orientation",
    "HASSOUTHORIENTATION": "has_south_orientation",
    "HASEASTORIENTATION": "has_east_orientation",
    "HASWESTORIENTATION": "has_west_orientation",
    "HASBOXROOM": "has_box_room",
    "HASWARDROBE": "has_wardrobe",
    "HASSWIMMINGPOOL": "has_swimming_pool",
    "HASDOORMAN": "has_doorman",
    "HASGARDEN": "has_garden",
    "ISDUPLEX": "is_duplex",
    "ISSTUDIO": "is_studio",
    "ISINTOPFLOOR": "is_top_floor",
    "AMENITYID": "amenity_id",
    "FLATLOCATIONID": "flat_location_id",
    "CADCONSTRUCTIONYEAR": "cad_construction_year",
    "CADMAXBUILDINGFLOOR": "cad_max_building_floor",
    "CADDWELLINGCOUNT": "cad_dwelling_count",
    "CADASTRALQUALITYID": "cadastral_quality_id",
    "DISTANCE_TO_CITY_CENTER": "distance_to_city_center",
    "DISTANCE_TO_METRO": "distance_to_metro",
    "DISTANCE_TO_CASTELLANA": "distance_to_castellana",
}


@dataclass(frozen=True)
class Feature:
    name: str
    dtype: str
    source: str
    nullable: bool
    description: str


FEATURES = [
    # Identifiers and target.
    Feature("asset_id", "str", "ASSETID", False, "idealista18 listing id, unique after dedupe."),
    Feature("period", "int", "PERIOD", False, "2018 quarterly snapshot, YYYYMM (201803/06/09/12)."),
    Feature("price", "float", "PRICE", False, "Asking price in euros (2018). Model target."),
    Feature("unit_price_m2", "float", "UNITPRICE", False, "Asking price per built m2 in euros (2018)."),
    # Core tabular features.
    Feature("area_m2", "float", "CONSTRUCTEDAREA", False, "Constructed area in m2."),
    Feature("rooms", "int", "ROOMNUMBER", False, "Number of rooms."),
    Feature("bathrooms", "int", "BATHNUMBER", False, "Number of bathrooms."),
    Feature("floor", "int", "FLOORCLEAN", True, "Cleaned floor level; -1 is basement/ground."),
    Feature("property_type", "str", "derived", False, "studio, duplex, or flat (from is_studio/is_duplex)."),
    Feature("condition", "str", "derived", False, "new, needs_renovation, or good (from BUILTTYPEID one-hot)."),
    Feature("construction_year", "int", "CONSTRUCTIONYEAR", True, "Build year; values outside 1900-2018 set null."),
    Feature("property_age", "int", "derived", True, "REFERENCE_YEAR minus construction_year; null when year null."),
    Feature("latitude", "float", "LATITUDE", False, "WGS84 latitude, inside Madrid bounding box."),
    Feature("longitude", "float", "LONGITUDE", False, "WGS84 longitude, inside Madrid bounding box."),
    # Barrio, filled by point-in-polygon join to Madrid_Polygons (135 zone-level-8
    # polygons). ~0.1% of rows fall in gaps between barrios and stay null.
    Feature("neighborhood_id", "str", "derived", True, "Barrio LOCATIONID from point-in-polygon join; null if outside all barrios."),
    Feature("neighborhood_name", "str", "derived", True, "Barrio name from point-in-polygon join; null if outside all barrios."),
    # Amenity and quality features.
    Feature("has_terrace", "int", "HASTERRACE", False, "1 if the listing has a terrace."),
    Feature("has_lift", "int", "HASLIFT", False, "1 if the building has a lift."),
    Feature("has_air_conditioning", "int", "HASAIRCONDITIONING", False, "1 if air conditioning is present."),
    Feature("has_parking", "int", "HASPARKINGSPACE", False, "1 if a parking space is available."),
    Feature("parking_included_in_price", "int", "ISPARKINGSPACEINCLUDEDINPRICE", False, "1 if parking is included in the price."),
    Feature("parking_space_price", "float", "PARKINGSPACEPRICE", False, "Parking price in euros; 0 when not applicable."),
    Feature("has_north_orientation", "int", "HASNORTHORIENTATION", False, "1 if the flat faces north."),
    Feature("has_south_orientation", "int", "HASSOUTHORIENTATION", False, "1 if the flat faces south."),
    Feature("has_east_orientation", "int", "HASEASTORIENTATION", False, "1 if the flat faces east."),
    Feature("has_west_orientation", "int", "HASWESTORIENTATION", False, "1 if the flat faces west."),
    Feature("has_box_room", "int", "HASBOXROOM", False, "1 if there is a box/storage room."),
    Feature("has_wardrobe", "int", "HASWARDROBE", False, "1 if there are fitted wardrobes."),
    Feature("has_swimming_pool", "int", "HASSWIMMINGPOOL", False, "1 if there is a swimming pool."),
    Feature("has_doorman", "int", "HASDOORMAN", False, "1 if there is a doorman."),
    Feature("has_garden", "int", "HASGARDEN", False, "1 if there is a garden."),
    Feature("is_duplex", "int", "ISDUPLEX", False, "1 if the property is a duplex."),
    Feature("is_studio", "int", "ISSTUDIO", False, "1 if the property is a studio."),
    Feature("is_top_floor", "int", "ISINTOPFLOOR", False, "1 if the flat is on the top floor."),
    Feature("amenity_id", "int", "AMENITYID", True, "idealista18 amenity category id."),
    Feature("flat_location_id", "int", "FLATLOCATIONID", True, "idealista18 interior/exterior location id."),
    # Cadastral features.
    Feature("cad_construction_year", "int", "CADCONSTRUCTIONYEAR", True, "Cadastral build year."),
    Feature("cad_max_building_floor", "int", "CADMAXBUILDINGFLOOR", True, "Cadastral max building floor."),
    Feature("cad_dwelling_count", "int", "CADDWELLINGCOUNT", True, "Cadastral dwelling count in the building."),
    Feature("cadastral_quality_id", "int", "CADASTRALQUALITYID", True, "Cadastral quality band, 0 (best) to 9."),
    # Geographic distance features.
    Feature("distance_to_city_center", "float", "DISTANCE_TO_CITY_CENTER", False, "Distance to city center in meters."),
    Feature("distance_to_metro", "float", "DISTANCE_TO_METRO", False, "Distance to nearest metro in meters."),
    Feature("distance_to_castellana", "float", "DISTANCE_TO_CASTELLANA", False, "Distance to Paseo de la Castellana in meters."),
    # Image-model placeholder, filled by the CNN in Phase 4.
    Feature("cnn_condition_score", "float", "placeholder", True, "CNN property/neighborhood condition score (0 to 1); null until Phase 4."),
]

FEATURE_NAMES = [f.name for f in FEATURES]

# Features guaranteed non-null after ETL. Tests assert a 0 null rate on these.
KEY_COLUMNS = [
    "asset_id",
    "period",
    "price",
    "unit_price_m2",
    "area_m2",
    "rooms",
    "bathrooms",
    "property_type",
    "condition",
    "latitude",
    "longitude",
]

# Model target.
TARGET = "price"

# Columns that leak the target and must never be model features.
# unit_price_m2 == price / area_m2 exactly, so it reconstructs the target.
LEAKAGE_COLUMNS = ["unit_price_m2"]

# Row identifiers, not predictive features.
IDENTIFIER_COLUMNS = ["asset_id", "period"]

# Safe feature set for the value model: everything except the target, its
# leakage columns, and identifiers. Downstream agents build features from this.
MODEL_FEATURE_NAMES = [
    f
    for f in FEATURE_NAMES
    if f not in {TARGET, *LEAKAGE_COLUMNS, *IDENTIFIER_COLUMNS}
]
