import importlib

import numpy as np
import orjson

from shared_lib.constants import SKILL_OFFSET_REDIS_KEY


def test_skill_offset_selects_mode_and_region_slices(
    client, fake_redis, monkeypatch
):
    import fast_api_app.routes.weapon_info as weapon_info_mod

    monkeypatch.setattr(
        weapon_info_mod, "redis_conn", fake_redis, raising=False
    )

    payload = {
        "all": {
            "all": [{"weapon_name": "global"}],
            "Tentatek": [{"weapon_name": "tentatek"}],
            "Takoroka": [{"weapon_name": "takoroka"}],
        },
        "Splat Zones": {
            "all": [{"weapon_name": "zones"}],
            "Tentatek": [{"weapon_name": "zones_tentatek"}],
            "Takoroka": [{"weapon_name": "zones_takoroka"}],
        },
    }
    fake_redis.set(SKILL_OFFSET_REDIS_KEY, orjson.dumps(payload))

    assert client.get("/api/skill-offset").json() == payload["all"]["all"]
    assert (
        client.get("/api/skill-offset?region=Tentatek").json()
        == payload["all"]["Tentatek"]
    )
    assert (
        client.get("/api/skill-offset?mode=Splat%20Zones").json()
        == payload["Splat Zones"]["all"]
    )
    assert (
        client.get(
            "/api/skill-offset?mode=Splat%20Zones&region=Takoroka"
        ).json()
        == payload["Splat Zones"]["Takoroka"]
    )


def test_skill_offset_rejects_unknown_slices(client, fake_redis, monkeypatch):
    import fast_api_app.routes.weapon_info as weapon_info_mod

    monkeypatch.setattr(
        weapon_info_mod, "redis_conn", fake_redis, raising=False
    )
    fake_redis.set(SKILL_OFFSET_REDIS_KEY, orjson.dumps({"all": {"all": []}}))

    response = client.get("/api/skill-offset?mode=Unknown")
    assert response.status_code == 404
    assert response.json() == {"detail": "Skill offset slice not found."}


def test_align_sorted_xp_scaled_to_surface_resamples_percentiles(monkeypatch):
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_USER", "user")
    monkeypatch.setenv("DB_PASSWORD", "pass")
    monkeypatch.setenv("DB_NAME", "db")
    monkeypatch.setenv("RANKINGS_DB_NAME", "db")

    skill_offset_mod = importlib.import_module(
        "celery_app.tasks.analytics.skill_offset"
    )

    input_values = np.linspace(0, 1, 5)
    aligned = skill_offset_mod.align_sorted_xp_scaled_to_surface(
        skill_offset_mod.pd.Series(input_values), 11
    )

    assert len(aligned) == 11
    assert np.isclose(aligned.iloc[0], 0.0)
    assert np.isclose(aligned.iloc[-1], 1.0)
    assert np.all(np.diff(aligned.to_numpy()) >= 0)


def test_align_sorted_xp_scaled_to_surface_keeps_canonical_size(monkeypatch):
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_USER", "user")
    monkeypatch.setenv("DB_PASSWORD", "pass")
    monkeypatch.setenv("DB_NAME", "db")
    monkeypatch.setenv("RANKINGS_DB_NAME", "db")

    skill_offset_mod = importlib.import_module(
        "celery_app.tasks.analytics.skill_offset"
    )

    input_values = np.array([0.1, 0.3, 0.6, 0.9])
    aligned = skill_offset_mod.align_sorted_xp_scaled_to_surface(
        skill_offset_mod.pd.Series(input_values), len(input_values)
    )

    np.testing.assert_allclose(aligned.to_numpy(), input_values)
