import json
import math
import os

import httpx
import streamlit as st

API_BASE_URL = os.environ.get("VALUATION_API_URL", "http://localhost:8600").rstrip("/")
TIMEOUT = float(os.environ.get("VALUATION_API_TIMEOUT", "30"))
CACHE_TTL = 900


class ApiError(Exception):
    pass


def _extract_detail(resp):
    try:
        body = resp.json()
        if isinstance(body, dict) and isinstance(body.get("error"), dict):
            return body["error"].get("message", "")
    except Exception:
        pass
    return (resp.text or "")[:200]


def _request(method, path, json_body=None):
    url = f"{API_BASE_URL}{path}"
    try:
        resp = httpx.request(method, url, json=json_body, timeout=TIMEOUT)
    except httpx.HTTPError as exc:
        raise ApiError(
            f"The valuation API at {API_BASE_URL} is unreachable "
            f"({exc.__class__.__name__}). No numbers can be shown."
        ) from exc
    if resp.status_code >= 400:
        raise ApiError(
            f"The valuation API returned an error ({resp.status_code}): {_extract_detail(resp)}"
        )
    try:
        return resp.json()
    except Exception as exc:
        raise ApiError("The valuation API returned a response that could not be read.") from exc


def _coerce(v):
    if v is None:
        return None
    if hasattr(v, "item"):
        v = v.item()
    if isinstance(v, float) and math.isnan(v):
        return None
    return v


def jsonable(mapping):
    return {k: _coerce(v) for k, v in mapping.items()}


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def fetch_estimate(asset_id):
    return _request("GET", f"/v1/estimate/{asset_id}")


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def fetch_estimate_posted(payload_json):
    return _request("POST", "/v1/estimate", json.loads(payload_json))


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def fetch_comparables(asset_id):
    return _request("GET", f"/v1/comparables/{asset_id}")


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def fetch_energy(asset_id):
    return _request("GET", f"/v1/energy/{asset_id}")


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def fetch_copilot(asset_id):
    return _request("GET", f"/v1/copilot/{asset_id}")


def post_payload_key(mapping):
    return json.dumps(jsonable(mapping), sort_keys=True, default=str)
