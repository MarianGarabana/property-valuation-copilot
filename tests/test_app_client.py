import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = REPO_ROOT / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import api_client


def test_client_fails_closed_on_unreachable_api(monkeypatch):
    monkeypatch.setattr(api_client, "API_BASE_URL", "http://127.0.0.1:1")
    monkeypatch.setattr(api_client, "TIMEOUT", 1.0)
    with pytest.raises(api_client.ApiError) as exc:
        api_client._request("GET", "/v1/estimate/whatever")
    assert "unreachable" in str(exc.value).lower()


def test_client_error_message_carries_no_numbers(monkeypatch):
    monkeypatch.setattr(api_client, "API_BASE_URL", "http://127.0.0.1:1")
    monkeypatch.setattr(api_client, "TIMEOUT", 1.0)
    try:
        api_client._request("GET", "/v1/estimate/whatever")
        raised = False
    except api_client.ApiError as exc:
        raised = True
        message = str(exc)
    assert raised
    assert not any(ch.isdigit() for ch in message.replace("127.0.0.1", "").replace(":1", ""))
