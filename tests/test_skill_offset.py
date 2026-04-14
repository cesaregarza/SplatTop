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
