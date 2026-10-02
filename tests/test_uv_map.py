import importlib
import io
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import numpy as np
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.v1.routes import uv
from backend.services import uv_map_service as service
from backend.services import uv_service
from scripts.prepare_uv_map import representative_point

NOW = datetime(2026, 10, 1, 8, tzinfo=UTC)
ROOT = Path(__file__).resolve().parents[1]


def snapshots(tmp_path, monkeypatch):
    monkeypatch.setattr(service, "MAP_SNAPSHOT", tmp_path / "map.json")
    monkeypatch.setattr(uv_service, "SNAPSHOT", tmp_path / "models.json")
    models = {
        "generated_at": NOW.isoformat(),
        "source": "TEMIS clear sky",
        "cities": {
            city: {
                "data_date": "2026-09-30",
                "model_version": "test-model",
                "days": [
                    {
                        "date": day,
                        "uv_index_clear_sky": 11.4,
                        "value_kind": "SARIMAX forecast",
                        "weather": None,
                    }
                    for day in ("2026-10-01", "2026-10-02")
                ],
            }
            for city in ("bangkok", "songkhla", "chiang_mai")
        },
    }
    uv_service.SNAPSHOT.write_text(json.dumps(models), encoding="utf-8")


def api_response(url, timeout):
    query = parse_qs(urlparse(url).query)
    assert timeout == 20
    assert query["daily"] == ["uv_index_clear_sky_max"]
    assert query["timezone"] == ["Asia/Bangkok"]
    latitudes = query["latitude"][0].split(",")
    assert len(latitudes) <= 20
    payload = [
        {
            "location_id": index,
            "timezone": "Asia/Bangkok",
            "daily": {"time": ["2026-10-01", "2026-10-02"], "uv_index_clear_sky_max": [7.2, 8.3]},
        }
        for index in range(len(latitudes))
    ]
    return io.StringIO(json.dumps(payload))


def test_full_country_sources_and_reusable_geometry(tmp_path, monkeypatch):
    snapshots(tmp_path, monkeypatch)
    assert service.refresh_api_map(date(2026, 10, 1), fetch=api_response, now=NOW) == 0
    today = service.load_map("today", NOW)
    tomorrow = service.load_map("tomorrow", NOW)
    shapes = json.loads((ROOT / "frontend/public/assets/uv-map-provinces.json").read_text("utf-8"))
    assert len(today["provinces"]) == len(shapes) == 77
    assert {p["id"] for p in shapes} == {p["id"] for p in today["provinces"]}
    local = service.load_map("today", NOW, source="model")["provinces"]
    assert len(local) == 3
    assert all(p["source"] == "local_model" for p in local)
    assert {p["id"] for p in local} == {"bangkok", "songkhla", "chiang_mai"}
    assert all(p["uv_index"] == 11.4 and p["aggregation"] == "solar_noon" for p in local)
    external = [p for p in today["provinces"] if p["source"] == "open_meteo"]
    assert len(external) == 77
    assert all(p["uv_index"] == 7.2 and p["aggregation"] == "daily_maximum" for p in external)
    assert all(p["status"] == "available" for p in today["provinces"])
    assert all(p["date"] == "2026-10-02" for p in tomorrow["provinces"])
    assert next(p for p in tomorrow["provinces"] if p["id"] == "phuket")["uv_index"] == 8.3


def test_failure_keeps_fresh_data_but_expires_it(tmp_path, monkeypatch):
    snapshots(tmp_path, monkeypatch)
    service.refresh_api_map(date(2026, 10, 1), fetch=api_response, now=NOW)

    def offline(*args, **kwargs):
        raise OSError("offline")

    assert service.refresh_api_map(date(2026, 10, 1), fetch=offline, now=NOW) == 4
    assert all(p["status"] == "available" for p in service.load_map(now=NOW)["provinces"])
    expired = service.load_map(now=NOW + timedelta(hours=9))
    assert all(p["uv_index"] is None and p["level"] is None for p in expired["provinces"])
    assert all(p["status"] == "stale" for p in expired["provinces"] if not p["model_city"])
    uv_service.SNAPSHOT.unlink()
    still_external = service.load_map(now=NOW)["provinces"]
    assert sum(p["status"] == "available" for p in still_external) == 77
    assert all(
        p["uv_index"] is None for p in service.load_map(now=NOW, source="model")["provinces"]
    )
    service.MAP_SNAPSHOT.unlink()
    snapshots(tmp_path, monkeypatch)
    assert all(
        p["status"] == "available" for p in service.load_map(now=NOW, source="model")["provinces"]
    )
    assert all(p["uv_index"] is None for p in service.load_map(now=NOW)["provinces"])


@pytest.mark.parametrize("value", [None, True, -1, 26, float("nan"), "8.5"])
def test_invalid_uv_does_not_become_zero(tmp_path, monkeypatch, value):
    snapshots(tmp_path, monkeypatch)
    service.MAP_SNAPSHOT.write_text(
        json.dumps(
            {
                "provinces": {
                    "phuket": {
                        "generated_at": NOW.isoformat(),
                        "days": [{"date": "2026-10-01", "uv_index": value}],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    record = next(p for p in service.load_map(now=NOW)["provinces"] if p["id"] == "phuket")
    assert record["uv_index"] is None
    assert record["status"] == "unavailable"


def test_missing_snapshot_and_thai_midnight(tmp_path, monkeypatch):
    snapshots(tmp_path, monkeypatch)
    uv_service.SNAPSHOT.unlink()
    before = service.load_map(now=datetime(2026, 10, 1, 16, 59, tzinfo=UTC))
    after = service.load_map(now=datetime(2026, 10, 1, 17, 0, tzinfo=UTC))
    assert before["date"] == "2026-10-01" and after["date"] == "2026-10-02"
    assert all(p["uv_index"] is None for p in after["provinces"])
    app = FastAPI()
    app.include_router(uv.router)
    client = TestClient(app)
    assert client.get("/map?day=next-week").status_code == 422
    assert client.get("/map?source=mixed").status_code == 422
    assert client.get("/map?day=today").status_code == 200
    assert len(client.get("/map?source=model").json()["provinces"]) == 3
    assert len(client.get("/map?source=api").json()["provinces"]) == 77


def test_representative_point_inside_concave_ring():
    ring = [[0, 0], [4, 0], [4, 4], [3, 4], [3, 1], [1, 1], [1, 4], [0, 4], [0, 0]]
    latitude, longitude = representative_point(ring)
    assert latitude == 2 and (0 < longitude < 1 or 3 < longitude < 4)


def test_today_remains_a_model_forecast_when_today_temis_exists(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    refresh = importlib.import_module("scripts.refresh_uv_forecast")
    days = [date(2026, 9, 29), date(2026, 9, 30), date(2026, 10, 1)]
    values = [9.0, 10.0, 20.0]

    class State:
        def __init__(self, observations):
            self.nobs = len(observations)
            self.model = SimpleNamespace(endog=np.asarray(observations))

        def apply(self, observations, **kwargs):
            assert list(observations) == values[:-1]
            return State(observations)

        def get_forecast(self, *, steps, exog):
            assert steps == 2
            return SimpleNamespace(predicted_mean=[10.1, 10.2])

    monkeypatch.setattr(refresh.SARIMAXResults, "load", lambda path: State(values))
    monkeypatch.setattr(refresh, "noon_weather", lambda *args: {})
    result = refresh.build_snapshot(
        {city: (days, values) for city in refresh.CITIES}, date(2026, 10, 1)
    )
    assert all(city["data_date"] == "2026-09-30" for city in result["cities"].values())
    assert all(
        entry["value_kind"] == "SARIMAX forecast" and entry["uv_index_clear_sky"] < 11
        for city in result["cities"].values()
        for entry in city["days"]
    )
