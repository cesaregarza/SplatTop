def test_openapi_contains_canonical_kebab_case_paths(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json().get("paths", {})

    assert "/api/weapon-info" in paths
    assert "/api/game-translation" in paths
    assert "/api/skill-offset" in paths
    assert "/api/weapon-leaderboard/{weapon_id}" in paths
    assert "/api/players/{player_id}" in paths
    assert "/api/ripple/leaderboard" in paths
    assert "/api/ripple/leaderboard/raw" in paths
    assert "/api/ripple/leaderboard/danger" in paths
    assert "/api/ripple/public/leaderboard" in paths
    assert "/api/ripple/public/leaderboard/danger" in paths
    assert "/api/ripple/public/metadata" in paths
    assert "/api/ripple/public/leaderboard/percentiles" in paths
    assert "/api/ripple/leaderboard/docs" in paths


def test_openapi_excludes_legacy_underscore_paths(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json().get("paths", {})

    assert "/api/weapon_info" not in paths
    assert "/api/game_translation" not in paths
    assert "/api/skill_offset" not in paths
    assert "/api/weapon_leaderboard/{weapon_id}" not in paths
    assert "/api/player/{player_id}" not in paths
    assert "/api/ripple" not in paths
    assert "/api/ripple/raw" not in paths
    assert "/api/ripple/danger" not in paths
    assert "/api/ripple/public" not in paths
    assert "/api/ripple/public/danger" not in paths
    assert "/api/ripple/public/meta" not in paths
    assert "/api/ripple/public/percentiles" not in paths
    assert "/api/ripple/docs" not in paths
