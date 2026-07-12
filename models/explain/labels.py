BOOL_FEATURES = {
    "has_terrace": ("having a terrace", "not having a terrace"),
    "has_lift": ("having a lift", "not having a lift"),
    "has_air_conditioning": ("having air conditioning", "not having air conditioning"),
    "has_parking": ("having a parking space", "not having a parking space"),
    "parking_included_in_price": ("parking included in the price", "parking not included in the price"),
    "has_north_orientation": ("north orientation", "no north orientation"),
    "has_south_orientation": ("south orientation", "no south orientation"),
    "has_east_orientation": ("east orientation", "no east orientation"),
    "has_west_orientation": ("west orientation", "no west orientation"),
    "has_box_room": ("having a box room", "not having a box room"),
    "has_wardrobe": ("having fitted wardrobes", "not having fitted wardrobes"),
    "has_swimming_pool": ("having a swimming pool", "not having a swimming pool"),
    "has_doorman": ("having a doorman", "not having a doorman"),
    "has_garden": ("having a garden", "not having a garden"),
    "is_duplex": ("being a duplex", "not being a duplex"),
    "is_studio": ("being a studio", "not being a studio"),
    "is_top_floor": ("being on the top floor", "not being on the top floor"),
}

CONTINUOUS_LABELS = {
    "area_m2": "size ({v:.0f} m2)",
    "rooms": "number of rooms ({v:.0f})",
    "bathrooms": "number of bathrooms ({v:.0f})",
    "floor": "floor level ({v:.0f})",
    "construction_year": "construction year ({v:.0f})",
    "property_age": "property age ({v:.0f} years)",
    "latitude": "latitude ({v:.4f})",
    "longitude": "longitude ({v:.4f})",
    "parking_space_price": "parking space price ({v:,.0f} euros)",
    "amenity_id": "amenity category ({v:.0f})",
    "flat_location_id": "interior/exterior location code ({v:.0f})",
    "cad_construction_year": "cadastral construction year ({v:.0f})",
    "cad_max_building_floor": "building max floor ({v:.0f})",
    "cad_dwelling_count": "number of dwellings in the building ({v:.0f})",
    "cadastral_quality_id": "cadastral quality band ({v:.0f})",
    "distance_to_city_center": "distance to the city center ({v:.1f} km)",
    "distance_to_metro": "distance to the nearest metro ({v:.1f} km)",
    "distance_to_castellana": "distance to Paseo de la Castellana ({v:.1f} km)",
}

CATEGORICAL_LABELS = {
    "property_type": "property type ({v})",
    "condition": "condition ({v})",
    "neighborhood_id": "neighborhood ({v})",
}


def describe_feature(feature, value, neighborhood_name=None):
    if feature in BOOL_FEATURES:
        present, absent = BOOL_FEATURES[feature]
        try:
            is_present = float(value) == 1.0
        except (TypeError, ValueError):
            is_present = False
        return present if is_present else absent
    if feature == "neighborhood_id" and neighborhood_name:
        return f"neighborhood ({neighborhood_name})"
    if feature in CATEGORICAL_LABELS:
        return CATEGORICAL_LABELS[feature].format(v=value)
    if feature in CONTINUOUS_LABELS:
        try:
            return CONTINUOUS_LABELS[feature].format(v=float(value))
        except (TypeError, ValueError):
            return CONTINUOUS_LABELS[feature].split(" (")[0]
    return feature.replace("_", " ")
