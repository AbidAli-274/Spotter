from datetime import UTC, datetime, timedelta

import pytest

from apps.trips import views
from apps.trips.services import TripAnalyzer
from tests.test_trip_analysis import FakeOrs, FakeWeather, line_route


@pytest.fixture
def api(monkeypatch, client):
    routes = [line_route(-100.0), line_route(-101.0, 220, 4.5), line_route(-99.0, 240, 5)]
    monkeypatch.setattr(views, "TripAnalyzer", lambda: TripAnalyzer(FakeOrs(routes), FakeWeather()))
    return client


def body(**overrides):
    payload = {
        "origin": {"label": "Dallas, TX"},
        "destination": {"label": "Denver, CO"},
        "departure": (datetime.now(UTC) + timedelta(hours=2)).isoformat(),
        "load_lb": 38000,
        "interval_mi": 25,
    }
    payload.update(overrides)
    return payload


def post(client, payload):
    return client.post("/api/trips/analyze/", payload, content_type="application/json")


def test_analyze_returns_routes_checkpoints_and_heatmap(api):
    response = post(api, body())
    assert response.status_code == 200
    data = response.json()
    assert len(data["routes"]) == 3
    assert sum(r["recommended"] for r in data["routes"]) == 1
    assert data["routes"][0]["checkpoints"][0]["eta"]
    assert data["heatmap"]["hours"] == 48


@pytest.mark.parametrize(
    "override",
    [
        {"load_lb": -1},
        {"load_lb": "abc"},
        {"interval_mi": 30},
        {"departure": "tomorrow-ish"},
        {"origin": {"label": ""}},
        {"origin": {"label": "X", "lat": 10}},
    ],
)
def test_validation_errors_are_structured(api, override):
    response = post(api, body(**override))
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert error["details"]


def test_past_departure_is_a_clear_422(api):
    response = post(api, body(departure=(datetime.now(UTC) - timedelta(days=2)).isoformat()))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "forecast_out_of_range"


def test_interval_defaults_to_25(api):
    payload = body()
    del payload["interval_mi"]
    assert post(api, payload).json()["interval_mi"] == 25


def test_openapi_schema_is_served(client):
    response = client.get("/api/schema/")
    assert response.status_code == 200
    assert b"/api/trips/analyze/" in response.content
