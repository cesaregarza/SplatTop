import time

import orjson

from shared_lib.constants import (
    RIPPLE_DANGER_LATEST_KEY,
    RIPPLE_PLAYER_INDEX_LATEST_KEY,
    RIPPLE_PLAYER_INDEX_META_KEY,
    RIPPLE_PLAYER_INDEX_PLAYER_PREFIX,
    RIPPLE_STABLE_DELTAS_KEY,
    RIPPLE_STABLE_LATEST_KEY,
    RIPPLE_STABLE_META_KEY,
)


def _now_ms() -> int:
    return int(time.time() * 1000)


def _player_index_key(player_id: str) -> str:
    return f"{RIPPLE_PLAYER_INDEX_PLAYER_PREFIX}{player_id}"


def test_public_leaderboard_disabled_returns_404(client_factory, fake_redis):
    with client_factory(
        env={"COMP_LEADERBOARD_ENABLED": "false"}, redis=fake_redis
    ) as client:
        res = client.get("/api/ripple/public/leaderboard")
        assert res.status_code == 404


def test_public_legacy_leaderboard_alias_works(client_factory, fake_redis):
    generated_at = _now_ms()
    payload = {
        "build_version": "2024.09.01",
        "calculated_at_ms": generated_at,
        "generated_at_ms": generated_at,
        "query_params": {},
        "record_count": 0,
        "total": 0,
        "data": [],
    }
    fake_redis.set(RIPPLE_STABLE_LATEST_KEY, orjson.dumps(payload))
    with client_factory(
        env={"COMP_LEADERBOARD_ENABLED": "true"}, redis=fake_redis
    ) as client:
        res = client.get("/api/ripple/public")
        assert res.status_code == 200


def test_public_leaderboard_returns_cached_payload(client_factory, fake_redis):
    generated_at = _now_ms()
    payload = {
        "build_version": "2024.09.01",
        "calculated_at_ms": generated_at,
        "generated_at_ms": generated_at,
        "query_params": {"limit": 200},
        "record_count": 2,
        "total": 2,
        "data": [
            {
                "player_id": "p1",
                "display_name": "Player 1",
                "stable_score": 12.3,
                "display_score": 307.5,
                "stable_rank": 1,
                "tournament_count": 10,
                "last_active_ms": generated_at,
                "last_tournament_ms": generated_at,
            },
            {
                "player_id": "p2",
                "display_name": "Player 2",
                "stable_score": 11.1,
                "display_score": 277.5,
                "stable_rank": 2,
                "tournament_count": 8,
                "last_active_ms": generated_at,
                "last_tournament_ms": generated_at,
            },
        ],
    }
    fake_redis.set(RIPPLE_STABLE_LATEST_KEY, orjson.dumps(payload))

    delta_payload = {
        "generated_at_ms": generated_at,
        "baseline_generated_at_ms": generated_at - 86_400_000,
        "record_count": 2,
        "comparison_count": 2,
        "players": {
            "p1": {
                "rank_delta": 1,
                "score_delta": 0.2,
                "display_score_delta": 5.0,
                "previous_rank": 2,
                "previous_score": 12.1,
                "previous_display_score": 302.5,
                "is_new": False,
            }
        },
        "newcomers": [],
        "dropouts": [],
    }
    fake_redis.set(RIPPLE_STABLE_DELTAS_KEY, orjson.dumps(delta_payload))

    with client_factory(
        env={"COMP_LEADERBOARD_ENABLED": "true"}, redis=fake_redis
    ) as client:
        res = client.get("/api/ripple/public/leaderboard")
        assert res.status_code == 200
        data = res.json()
        assert data["build_version"] == "2024.09.01"
        assert data["record_count"] == 2
        assert data["data"][0]["player_id"] == "p1"
        assert data["stale"] is False
        assert isinstance(data["retrieved_at_ms"], int)
        assert (
            data["deltas"]["baseline_generated_at_ms"]
            == generated_at - 86_400_000
        )
        assert data["deltas"]["players"]["p1"]["rank_delta"] == 1
        assert data["deltas"]["stale"] is False


def test_public_danger_returns_cached_payload(client_factory, fake_redis):
    generated_at = _now_ms()
    payload = {
        "build_version": "2024.09.01",
        "calculated_at_ms": generated_at,
        "generated_at_ms": generated_at,
        "query_params": {"limit": 50},
        "record_count": 1,
        "total": 1,
        "data": [
            {
                "rank": 10,
                "player_id": "p3",
                "display_name": "Player 3",
                "display_score": 250.0,
                "window_tournament_count": 3,
                "oldest_in_window_ms": generated_at - 1000,
                "next_expiry_ms": generated_at + 1000,
                "days_left": 0.5,
            }
        ],
    }
    fake_redis.set(RIPPLE_DANGER_LATEST_KEY, orjson.dumps(payload))

    with client_factory(
        env={"COMP_LEADERBOARD_ENABLED": "true"}, redis=fake_redis
    ) as client:
        res = client.get("/api/ripple/public/leaderboard/danger")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1
        assert data["data"][0]["player_id"] == "p3"
        assert data["stale"] is False


def test_public_meta_reports_presence(client_factory, fake_redis):
    generated_at = _now_ms()
    meta_payload = {
        "generated_at_ms": generated_at,
        "stable_calculated_at_ms": generated_at,
        "stable_record_count": 2,
        "danger_calculated_at_ms": generated_at,
        "danger_record_count": 1,
        "build_version": "2024.09.01",
    }
    stable_payload = {
        "build_version": "2024.09.01",
        "calculated_at_ms": generated_at,
        "generated_at_ms": generated_at,
        "query_params": {},
        "record_count": 0,
        "total": 0,
        "data": [],
    }
    danger_payload = {
        "build_version": "2024.09.01",
        "calculated_at_ms": generated_at,
        "generated_at_ms": generated_at,
        "query_params": {},
        "record_count": 0,
        "total": 0,
        "data": [],
    }
    fake_redis.set(RIPPLE_STABLE_META_KEY, orjson.dumps(meta_payload))
    fake_redis.set(RIPPLE_STABLE_LATEST_KEY, orjson.dumps(stable_payload))
    fake_redis.set(RIPPLE_DANGER_LATEST_KEY, orjson.dumps(danger_payload))

    with client_factory(
        env={"COMP_LEADERBOARD_ENABLED": "true"}, redis=fake_redis
    ) as client:
        res = client.get("/api/ripple/public/metadata")
        assert res.status_code == 200
        data = res.json()
        assert data["meta"]["build_version"] == "2024.09.01"
        assert data["stable"]["present"] is True
        assert data["danger"]["present"] is True
        assert data["feature_flag"]["enabled"] is True
        assert isinstance(data["retrieved_at_ms"], int)


def test_public_player_profile_returns_cached_payload(
    client_factory, fake_redis
):
    generated_at = _now_ms()
    meta_payload = {
        "generated_at_ms": generated_at,
        "calculated_at_ms": generated_at - 1_000,
        "build_version": "2024.09.01",
        "minimum_required_tournaments": 3,
        "record_count": 2,
    }
    player_payload = {
        "player_id": "p1",
        "display_name": "Player 1",
        "eligible": True,
        "ineligible_reason": None,
        "minimum_required_tournaments": 3,
        "lifetime_ranked_tournaments": 12,
        "window_tournament_count": 4,
        "progress_to_minimum": {
            "current": 3,
            "required": 3,
            "remaining": 0,
        },
        "stable_rank": 7,
        "stable_score": 5.1,
        "display_score": 277.5,
        "danger_days_left": 8.5,
        "last_active_ms": generated_at - 10_000,
        "last_tournament_ms": generated_at - 10_000,
        "rank_delta": 2,
        "display_score_delta": 4.25,
        "delta_is_new": False,
        "delta_has_baseline": True,
        "previous_rank": 9,
        "previous_display_score": 273.25,
        "history_generated_at_ms": generated_at,
        "history_record_count": 1,
        "history_max_records": 25,
        "tournament_history_ranked": [
            {
                "tournament_id": 44,
                "tournament_name": "Midnight Splat",
                "event_ms": generated_at - 86_400_000,
                "ranked": True,
                "placement_label": None,
                "result_summary": None,
                "team_name": None,
                "team_id": None,
            }
        ],
        "match_loo_generated_at_ms": generated_at,
        "match_loo_record_count": 1,
        "match_loo_max_records": 20,
        "match_loo_impacts": [
            {
                "match_id": 501,
                "tournament_id": 44,
                "tournament_name": "Midnight Splat",
                "event_ms": generated_at - 86_400_000,
                "player_rank": 7,
                "player_score": 5.1,
                "is_win": False,
                "exact_score_delta": 0.42,
                "exact_abs_delta": 0.42,
                "player_team_id": 17,
                "player_team_name": "Luma",
                "opponent_team_id": 19,
                "opponent_team_name": "Nova",
                "player_team_score": 1,
                "opponent_team_score": 3,
                "player_team_players": [
                    "Aster",
                    "Beryl",
                    "Cinder",
                    "Drift",
                ],
                "opponent_team_players": [
                    "Ember",
                    "Flint",
                    "Glint",
                    "Halo",
                ],
            }
        ],
    }
    fake_redis.set(RIPPLE_PLAYER_INDEX_META_KEY, orjson.dumps(meta_payload))
    fake_redis.set(
        _player_index_key("p1"),
        orjson.dumps(player_payload),
    )

    with client_factory(
        env={"COMP_LEADERBOARD_ENABLED": "true"}, redis=fake_redis
    ) as client:
        res = client.get("/api/ripple/public/player/p1")
        assert res.status_code == 200
        data = res.json()
        assert data["player_id"] == "p1"
        assert data["eligible"] is True
        assert data["match_loo_impacts"][0]["match_id"] == 501
        assert data["match_loo_impacts"][0]["player_team_name"] == "Luma"
        assert data["match_loo_impacts"][0]["opponent_team_score"] == 3
        assert data["match_loo_impacts"][0]["player_team_players"][0] == "Aster"
        assert data["build_version"] == "2024.09.01"
        assert data["stale"] is False
        assert isinstance(data["retrieved_at_ms"], int)


def test_public_player_profile_falls_back_to_legacy_index_blob(
    client_factory, fake_redis
):
    generated_at = _now_ms()
    payload = {
        "generated_at_ms": generated_at,
        "calculated_at_ms": generated_at - 1_000,
        "build_version": "2024.09.01",
        "minimum_required_tournaments": 3,
        "record_count": 1,
        "players": {
            "p1": {
                "player_id": "p1",
                "display_name": "Player 1",
                "eligible": True,
                "match_loo_impacts": [
                    {
                        "match_id": 501,
                        "tournament_id": 44,
                        "tournament_name": "Midnight Splat",
                        "event_ms": generated_at - 86_400_000,
                        "player_rank": 7,
                        "player_score": 5.1,
                        "is_win": False,
                        "exact_score_delta": 0.42,
                        "exact_abs_delta": 0.42,
                        "player_team_id": 17,
                        "player_team_name": "Luma",
                        "opponent_team_id": 19,
                        "opponent_team_name": "Nova",
                        "player_team_score": 1,
                        "opponent_team_score": 3,
                        "player_team_players": [
                            "Aster",
                            "Beryl",
                            "Cinder",
                            "Drift",
                        ],
                        "opponent_team_players": [
                            "Ember",
                            "Flint",
                            "Glint",
                            "Halo",
                        ],
                    }
                ],
            },
        },
    }
    fake_redis.set(RIPPLE_PLAYER_INDEX_LATEST_KEY, orjson.dumps(payload))

    with client_factory(
        env={"COMP_LEADERBOARD_ENABLED": "true"}, redis=fake_redis
    ) as client:
        res = client.get("/api/ripple/public/player/p1")
        assert res.status_code == 200
        data = res.json()
        assert data["player_id"] == "p1"
        assert data["eligible"] is True
        assert data["match_loo_impacts"][0]["match_id"] == 501
        assert data["match_loo_impacts"][0]["player_team_name"] == "Luma"
        assert data["match_loo_impacts"][0]["opponent_team_score"] == 3
        assert data["match_loo_impacts"][0]["player_team_players"][0] == "Aster"
        assert data["build_version"] == "2024.09.01"
        assert data["calculated_at_ms"] == generated_at - 1_000
        assert data["generated_at_ms"] == generated_at
        assert data["stale"] is False
        assert isinstance(data["retrieved_at_ms"], int)


def test_public_player_profile_returns_404_for_unknown_player(
    client_factory, fake_redis
):
    generated_at = _now_ms()
    payload = {
        "generated_at_ms": generated_at,
        "calculated_at_ms": generated_at,
        "build_version": "2024.09.01",
        "minimum_required_tournaments": 3,
        "record_count": 1,
        "player_ids": ["p1"],
    }
    fake_redis.set(RIPPLE_PLAYER_INDEX_META_KEY, orjson.dumps(payload))
    fake_redis.set(RIPPLE_PLAYER_INDEX_LATEST_KEY, orjson.dumps(payload))

    with client_factory(
        env={"COMP_LEADERBOARD_ENABLED": "true"}, redis=fake_redis
    ) as client:
        res = client.get("/api/ripple/public/player/missing")
        assert res.status_code == 404
        assert res.json()["detail"] == "Player not found in competition index"


def test_public_player_preview_page_returns_dynamic_meta(
    client_factory, fake_redis
):
    generated_at = _now_ms()
    meta_payload = {
        "generated_at_ms": generated_at,
        "calculated_at_ms": generated_at - 1_000,
        "build_version": "2024.09.01",
        "minimum_required_tournaments": 3,
        "record_count": 1,
    }
    player_payload = {
        "player_id": "p1",
        "display_name": "Player 1",
        "eligible": True,
        "minimum_required_tournaments": 3,
        "lifetime_ranked_tournaments": 12,
        "window_tournament_count": 4,
        "stable_rank": 7,
        "display_score": 80,
        "last_active_ms": generated_at - 10_000,
    }
    fake_redis.set(RIPPLE_PLAYER_INDEX_META_KEY, orjson.dumps(meta_payload))
    fake_redis.set(_player_index_key("p1"), orjson.dumps(player_payload))

    with client_factory(
        env={"COMP_LEADERBOARD_ENABLED": "true"}, redis=fake_redis
    ) as client:
        res = client.get("/u/p1")
        assert res.status_code == 200
        assert res.headers["content-type"].startswith("text/html")
        body = res.text
        assert (
            'property="og:title" content="Player 1 · #7 · splat.top Competitive"'
            in body
        )
        assert (
            'property="og:image" content="http://testserver/api/ripple/public/player/p1/share-image.png"'
            in body
        )
        assert 'property="og:url" content="http://testserver/u/p1"' in body
        assert 'http-equiv="refresh"' not in body


def test_public_player_share_alias_redirects_to_canonical_url(
    client_factory, fake_redis
):
    generated_at = _now_ms()
    meta_payload = {
        "generated_at_ms": generated_at,
        "calculated_at_ms": generated_at - 1_000,
        "build_version": "2024.09.01",
        "minimum_required_tournaments": 3,
        "record_count": 1,
    }
    player_payload = {
        "player_id": "p1",
        "display_name": "Player 1",
        "eligible": True,
        "minimum_required_tournaments": 3,
        "lifetime_ranked_tournaments": 12,
        "window_tournament_count": 4,
        "stable_rank": 7,
        "display_score": 80,
        "last_active_ms": generated_at - 10_000,
    }
    fake_redis.set(RIPPLE_PLAYER_INDEX_META_KEY, orjson.dumps(meta_payload))
    fake_redis.set(_player_index_key("p1"), orjson.dumps(player_payload))

    with client_factory(
        env={"COMP_LEADERBOARD_ENABLED": "true"}, redis=fake_redis
    ) as client:
        res = client.get("/share/u/p1")
        assert res.status_code == 200
        body = res.text
        assert 'property="og:url" content="http://testserver/u/p1"' in body
        assert 'http-equiv="refresh" content="0;url=http://testserver/u/p1"' in body


def test_public_player_share_image_returns_png(client_factory, fake_redis):
    generated_at = _now_ms()
    meta_payload = {
        "generated_at_ms": generated_at,
        "calculated_at_ms": generated_at - 1_000,
        "build_version": "2024.09.01",
        "minimum_required_tournaments": 3,
        "record_count": 1,
    }
    player_payload = {
        "player_id": "p1",
        "display_name": "Player 1",
        "eligible": True,
        "minimum_required_tournaments": 3,
        "lifetime_ranked_tournaments": 12,
        "window_tournament_count": 4,
        "stable_rank": 7,
        "display_score": 80,
        "last_active_ms": generated_at - 10_000,
    }
    fake_redis.set(RIPPLE_PLAYER_INDEX_META_KEY, orjson.dumps(meta_payload))
    fake_redis.set(_player_index_key("p1"), orjson.dumps(player_payload))

    with client_factory(
        env={"COMP_LEADERBOARD_ENABLED": "true"}, redis=fake_redis
    ) as client:
        res = client.get("/api/ripple/public/player/p1/share-image.png")
        assert res.status_code == 200
        assert res.headers["content-type"].startswith("image/png")
        assert res.content.startswith(b"\x89PNG\r\n\x1a\n")
        assert len(res.content) > 1024
