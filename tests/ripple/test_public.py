from contextlib import asynccontextmanager
import time
from urllib.parse import parse_qs, urlparse

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


def _login_comp_user(client, monkeypatch, discord_id):
    import fast_api_app.routes.comp_auth as comp_auth_mod

    async def _fake_exchange(_code):
        return discord_id

    monkeypatch.setattr(
        comp_auth_mod,
        "exchange_discord_code_for_user_id",
        _fake_exchange,
    )
    login_response = client.get(
        "/api/comp-auth/discord/login",
        params={"next": "/u/p1"},
        follow_redirects=False,
    )
    state = parse_qs(urlparse(login_response.headers["location"]).query)[
        "state"
    ][0]
    callback_response = client.get(
        "/api/comp-auth/discord/callback",
        params={"code": "discord-code", "state": state},
        follow_redirects=False,
    )
    assert callback_response.status_code == 302


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
        assert data["viewer_can_view_results"] is False
        assert "match_loo_generated_at_ms" not in data
        assert "match_loo_record_count" not in data
        assert "match_loo_max_records" not in data
        assert "match_loo_impacts" not in data
        assert data["build_version"] == "2024.09.01"
        assert data["stale"] is False
        assert isinstance(data["retrieved_at_ms"], int)


def test_public_player_profile_hides_private_player_fields(
    client_factory, fake_redis
):
    generated_at = _now_ms()
    fake_redis.set(
        RIPPLE_PLAYER_INDEX_META_KEY,
        orjson.dumps(
            {
                "generated_at_ms": generated_at,
                "calculated_at_ms": generated_at,
                "build_version": "2024.09.01",
                "minimum_required_tournaments": 3,
                "record_count": 1,
            }
        ),
    )
    fake_redis.set(
        _player_index_key("p1"),
        orjson.dumps(
            {
                "player_id": "p1",
                "display_name": "Player 1",
                "stable_rank": None,
                "stable_score": None,
                "display_score": None,
                "private_stable_rank": 21,
                "private_stable_score": 1.75,
                "private_display_score": 193.75,
            }
        ),
    )

    with client_factory(
        env={"COMP_LEADERBOARD_ENABLED": "true"}, redis=fake_redis
    ) as client:
        res = client.get("/api/ripple/public/player/p1")
        assert res.status_code == 200
        data = res.json()
        assert data["stable_rank"] is None
        assert data["stable_score"] is None
        assert data["display_score"] is None
        assert data["viewer_can_view_results"] is False
        assert "private_stable_rank" not in data
        assert "private_stable_score" not in data
        assert "private_display_score" not in data


def test_public_player_profile_returns_results_for_signed_in_owner(
    client_factory, fake_redis, monkeypatch
):
    generated_at = _now_ms()
    fake_redis.set(
        RIPPLE_PLAYER_INDEX_META_KEY,
        orjson.dumps(
            {
                "generated_at_ms": generated_at,
                "calculated_at_ms": generated_at,
                "build_version": "2024.09.01",
                "minimum_required_tournaments": 3,
                "record_count": 1,
            }
        ),
    )
    fake_redis.set(
        _player_index_key("p1"),
        orjson.dumps(
            {
                "player_id": "p1",
                "display_name": "Player 1",
                "eligible": True,
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
                        "player_team_name": "Luma",
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
        ),
    )

    with client_factory(
        env={
            "COMP_LEADERBOARD_ENABLED": "true",
            "COMP_AUTH_SESSION_SECRET": "test-comp-session-secret",
            "COMP_DISCORD_CLIENT_ID": "discord-client-id",
            "COMP_DISCORD_CLIENT_SECRET": "discord-client-secret",
            "COMP_DISCORD_REDIRECT_URI": (
                "http://localhost:5000/api/comp-auth/discord/callback"
            ),
            "COMP_AUTH_FRONTEND_URL": "http://comp.localhost:3000",
            "COMP_AUTH_PLAYER_OWNERS": "p1=11111",
        },
        redis=fake_redis,
    ) as client:
        _login_comp_user(client, monkeypatch, "11111")
        res = client.get("/api/ripple/public/player/p1")
        assert res.status_code == 200
        data = res.json()
        assert data["viewer_can_view_results"] is True
        assert data["match_loo_record_count"] == 1
        assert data["match_loo_impacts"][0]["match_id"] == 501
        assert data["match_loo_impacts"][0]["player_team_name"] == "Luma"


def test_admin_player_profile_returns_unredacted_values_for_admin(
    client_factory, fake_redis, monkeypatch
):
    generated_at = _now_ms()
    fake_redis.set(
        RIPPLE_PLAYER_INDEX_META_KEY,
        orjson.dumps(
            {
                "generated_at_ms": generated_at,
                "calculated_at_ms": generated_at,
                "build_version": "2024.09.01",
                "minimum_required_tournaments": 3,
                "record_count": 1,
            }
        ),
    )
    fake_redis.set(
        _player_index_key("p1"),
        orjson.dumps(
            {
                "player_id": "p1",
                "display_name": "Player 1",
                "stable_rank": None,
                "stable_score": None,
                "display_score": None,
                "private_stable_rank": 21,
                "private_stable_score": 1.75,
                "private_display_score": 193.75,
            }
        ),
    )

    with client_factory(
        env={
            "COMP_LEADERBOARD_ENABLED": "true",
            "COMP_AUTH_SESSION_SECRET": "test-comp-session-secret",
            "COMP_DISCORD_CLIENT_ID": "discord-client-id",
            "COMP_DISCORD_CLIENT_SECRET": "discord-client-secret",
            "COMP_DISCORD_REDIRECT_URI": (
                "http://localhost:5000/api/comp-auth/discord/callback"
            ),
            "COMP_AUTH_FRONTEND_URL": "http://comp.localhost:3000",
            "COMP_AUTH_ADMIN_DISCORD_IDS": "24680,99999",
        },
        redis=fake_redis,
    ) as client:
        _login_comp_user(client, monkeypatch, "24680")
        res = client.get("/api/ripple/admin/player/p1")
        assert res.status_code == 200
        data = res.json()
        assert data["stable_rank"] == 21
        assert data["stable_score"] == 1.75
        assert data["display_score"] == 193.75
        assert "private_stable_rank" not in data
        assert "private_stable_score" not in data
        assert "private_display_score" not in data


def test_admin_player_profile_enriches_cached_profile_with_full_history(
    client_factory, fake_redis, monkeypatch
):
    generated_at = _now_ms()
    fake_redis.set(
        RIPPLE_PLAYER_INDEX_META_KEY,
        orjson.dumps(
            {
                "generated_at_ms": generated_at,
                "calculated_at_ms": generated_at,
                "build_version": "2024.09.01",
                "minimum_required_tournaments": 3,
                "record_count": 1,
            }
        ),
    )
    fake_redis.set(
        _player_index_key("p1"),
        orjson.dumps(
            {
                "player_id": "p1",
                "display_name": "Cached Player",
                "eligible": True,
                "minimum_required_tournaments": 3,
                "lifetime_ranked_tournaments": 25,
                "window_tournament_count": 4,
                "stable_rank": None,
                "stable_score": None,
                "display_score": None,
                "private_stable_rank": 21,
                "private_stable_score": 1.75,
                "private_display_score": 193.75,
                "history_record_count": 25,
                "history_max_records": 25,
                "tournament_history_ranked": [
                    {
                        "tournament_id": 1,
                        "tournament_name": "Cached Cup",
                        "event_ms": generated_at - 86_400_000,
                        "ranked": True,
                        "result_summary": "2W-1L",
                        "team_name": "Cached Team",
                        "team_id": 7,
                    }
                ],
                "match_loo_record_count": 0,
                "match_loo_max_records": 20,
                "match_loo_impacts": [],
            }
        ),
    )

    db_history = [
        {
            "tournament_id": 1_000 + idx,
            "tournament_name": f"DB Cup {idx}",
            "event_ms": generated_at - idx,
            "ranked": True,
            "placement_label": None,
            "result_summary": "1W-0L",
            "team_name": "DB Team",
            "team_id": 900 + idx,
        }
        for idx in range(40)
    ]

    with client_factory(
        env={
            "COMP_LEADERBOARD_ENABLED": "true",
            "COMP_AUTH_SESSION_SECRET": "test-comp-session-secret",
            "COMP_DISCORD_CLIENT_ID": "discord-client-id",
            "COMP_DISCORD_CLIENT_SECRET": "discord-client-secret",
            "COMP_DISCORD_REDIRECT_URI": (
                "http://localhost:5000/api/comp-auth/discord/callback"
            ),
            "COMP_AUTH_FRONTEND_URL": "http://comp.localhost:3000",
            "COMP_AUTH_ADMIN_DISCORD_IDS": "24680,99999",
        },
        redis=fake_redis,
    ) as client:
        import fast_api_app.routes.ripple_public as ripple_public_mod

        @asynccontextmanager
        async def _fake_session():
            class _Session:
                pass

            yield _Session()

        async def _unexpected_base(*_args, **_kwargs):
            raise AssertionError(
                "cached admin payload should not call the DB-only base query"
            )

        async def _fake_fetch_history(session, player_ids, *, max_per_player):
            assert session is not None
            assert player_ids == ["p1"]
            assert max_per_player is None
            return {"p1": db_history}

        async def _fake_fetch_match_loo(
            session,
            player_ids,
            *,
            calculated_at_ms,
            build_version,
            max_per_player,
        ):
            assert session is not None
            assert player_ids == ["p1"]
            assert calculated_at_ms == generated_at
            assert build_version == "2024.09.01"
            assert max_per_player == ripple_public_mod.MAX_PLAYER_MATCH_LOO_ENTRIES
            return {}

        monkeypatch.setattr(
            ripple_public_mod,
            "rankings_async_session",
            _fake_session,
            raising=False,
        )
        monkeypatch.setattr(
            ripple_public_mod,
            "_load_admin_player_base_from_db",
            _unexpected_base,
        )
        monkeypatch.setattr(
            ripple_public_mod,
            "_fetch_player_ranked_history",
            _fake_fetch_history,
        )
        monkeypatch.setattr(
            ripple_public_mod,
            "_fetch_player_match_loo_impacts",
            _fake_fetch_match_loo,
        )

        _login_comp_user(client, monkeypatch, "24680")
        res = client.get("/api/ripple/admin/player/p1")
        assert res.status_code == 200
        data = res.json()
        assert data["display_name"] == "Cached Player"
        assert data["stable_rank"] == 21
        assert data["stable_score"] == 1.75
        assert data["display_score"] == 193.75
        assert data["history_record_count"] == 40
        assert data["history_max_records"] is None
        assert len(data["tournament_history_ranked"]) == 40
        assert data["tournament_history_ranked"][0]["tournament_name"] == "DB Cup 0"
        assert "private_stable_rank" not in data
        assert "private_stable_score" not in data
        assert "private_display_score" not in data


def test_admin_player_profile_rejects_non_admin_user(
    client_factory, fake_redis, monkeypatch
):
    fake_redis.set(
        _player_index_key("p1"),
        orjson.dumps({"player_id": "p1", "display_name": "Player 1"}),
    )

    with client_factory(
        env={
            "COMP_LEADERBOARD_ENABLED": "true",
            "COMP_AUTH_SESSION_SECRET": "test-comp-session-secret",
            "COMP_DISCORD_CLIENT_ID": "discord-client-id",
            "COMP_DISCORD_CLIENT_SECRET": "discord-client-secret",
            "COMP_DISCORD_REDIRECT_URI": (
                "http://localhost:5000/api/comp-auth/discord/callback"
            ),
            "COMP_AUTH_FRONTEND_URL": "http://comp.localhost:3000",
            "COMP_AUTH_ADMIN_DISCORD_IDS": "24680,99999",
        },
        redis=fake_redis,
    ) as client:
        _login_comp_user(client, monkeypatch, "11111")
        res = client.get("/api/ripple/admin/player/p1")
        assert res.status_code == 403
        assert res.json()["detail"] == "Competition admin access is required"


def test_admin_player_profile_prefers_db_payload_over_cached_profile(
    client_factory, fake_redis, monkeypatch
):
    generated_at = _now_ms()
    fake_redis.set(
        RIPPLE_PLAYER_INDEX_META_KEY,
        orjson.dumps(
            {
                "generated_at_ms": generated_at,
                "calculated_at_ms": generated_at,
                "build_version": "2024.09.01",
                "minimum_required_tournaments": 3,
                "record_count": 1,
            }
        ),
    )
    fake_redis.set(
        _player_index_key("p1"),
        orjson.dumps(
            {
                "player_id": "p1",
                "display_name": "Cached Player",
                "eligible": True,
                "minimum_required_tournaments": 3,
                "lifetime_ranked_tournaments": 25,
                "window_tournament_count": 4,
                "stable_rank": 11,
                "display_score": 200.0,
                "history_record_count": 25,
                "history_max_records": 25,
                "tournament_history_ranked": [
                    {
                        "tournament_id": 1,
                        "tournament_name": "Cached Cup",
                        "event_ms": generated_at - 86_400_000,
                        "ranked": True,
                        "result_summary": "2W-1L",
                        "team_name": "Cached Team",
                        "team_id": 7,
                    }
                ],
                "match_loo_record_count": 0,
                "match_loo_max_records": 20,
                "match_loo_impacts": [],
            }
        ),
    )

    db_history = [
        {
            "tournament_id": 1_000 + idx,
            "tournament_name": f"DB Cup {idx}",
            "event_ms": generated_at - idx,
            "ranked": True,
            "placement_label": None,
            "result_summary": "1W-0L",
            "team_name": "DB Team",
            "team_id": 900 + idx,
        }
        for idx in range(40)
    ]

    async def _fake_db_profile(player_id):
        assert player_id == "p1"
        return {
            "player_id": "p1",
            "display_name": "DB Player",
            "eligible": True,
            "ineligible_reason": None,
            "minimum_required_tournaments": 3,
            "lifetime_ranked_tournaments": 40,
            "window_tournament_count": 6,
            "progress_to_minimum": {
                "current": 3,
                "required": 3,
                "remaining": 0,
            },
            "stable_rank": 9,
            "stable_score": 2.0,
            "display_score": 200.0,
            "danger_days_left": 7.0,
            "last_active_ms": generated_at,
            "last_tournament_ms": generated_at,
            "rank_delta": 1,
            "display_score_delta": 4.0,
            "delta_is_new": False,
            "delta_has_baseline": True,
            "previous_rank": 10,
            "previous_display_score": 196.0,
            "history_generated_at_ms": generated_at,
            "history_record_count": len(db_history),
            "history_max_records": None,
            "tournament_history_ranked": db_history,
            "match_loo_generated_at_ms": generated_at,
            "match_loo_record_count": 0,
            "match_loo_max_records": 20,
            "match_loo_impacts": [],
            "generated_at_ms": generated_at,
            "calculated_at_ms": generated_at,
            "build_version": "2024.09.01",
            "stale": False,
            "retrieved_at_ms": generated_at,
        }

    with client_factory(
        env={
            "COMP_LEADERBOARD_ENABLED": "true",
            "COMP_AUTH_SESSION_SECRET": "test-comp-session-secret",
            "COMP_DISCORD_CLIENT_ID": "discord-client-id",
            "COMP_DISCORD_CLIENT_SECRET": "discord-client-secret",
            "COMP_DISCORD_REDIRECT_URI": (
                "http://localhost:5000/api/comp-auth/discord/callback"
            ),
            "COMP_AUTH_FRONTEND_URL": "http://comp.localhost:3000",
            "COMP_AUTH_ADMIN_DISCORD_IDS": "24680,99999",
        },
        redis=fake_redis,
    ) as client:
        import fast_api_app.routes.ripple_public as ripple_public_mod

        monkeypatch.setattr(
            ripple_public_mod,
            "_load_admin_player_payload_from_db",
            _fake_db_profile,
        )
        _login_comp_user(client, monkeypatch, "24680")
        res = client.get("/api/ripple/admin/player/p1")
        assert res.status_code == 200
        data = res.json()
        assert data["display_name"] == "DB Player"
        assert data["history_record_count"] == 40
        assert data["history_max_records"] is None
        assert len(data["tournament_history_ranked"]) == 40
        assert data["tournament_history_ranked"][0]["tournament_name"] == "DB Cup 0"


def test_admin_refresh_endpoint_queues_snapshot_refresh(
    client_factory, fake_redis, monkeypatch
):
    class _TaskResult:
        id = "refresh-task-123"

    class _SpyCelery:
        def __init__(self):
            self.calls = []

        def send_task(self, name, args=None, kwargs=None):
            self.calls.append((name, list(args or []), dict(kwargs or {})))
            return _TaskResult()

    with client_factory(
        env={
            "COMP_LEADERBOARD_ENABLED": "true",
            "COMP_AUTH_SESSION_SECRET": "test-comp-session-secret",
            "COMP_DISCORD_CLIENT_ID": "discord-client-id",
            "COMP_DISCORD_CLIENT_SECRET": "discord-client-secret",
            "COMP_DISCORD_REDIRECT_URI": (
                "http://localhost:5000/api/comp-auth/discord/callback"
            ),
            "COMP_AUTH_FRONTEND_URL": "http://comp.localhost:3000",
            "COMP_AUTH_ADMIN_DISCORD_IDS": "24680,99999",
        },
        redis=fake_redis,
    ) as client:
        import fast_api_app.routes.ripple_public as ripple_public_mod

        celery_spy = _SpyCelery()
        monkeypatch.setattr(
            ripple_public_mod,
            "celery",
            celery_spy,
            raising=False,
        )
        _login_comp_user(client, monkeypatch, "24680")
        res = client.post("/api/ripple/admin/refresh")
        assert res.status_code == 200
        assert res.json()["queued"] is True
        assert res.json()["completed"] is False
        assert res.json()["task_name"] == "tasks.refresh_ripple_snapshots"
        assert res.json()["task_id"] == "refresh-task-123"
        assert len(celery_spy.calls) == 1
        assert celery_spy.calls[0] == (
            "tasks.refresh_ripple_snapshots",
            [],
            {},
        )


def test_admin_refresh_endpoint_can_run_snapshot_refresh_inline(
    client_factory, fake_redis, monkeypatch
):
    with client_factory(
        env={
            "COMP_LEADERBOARD_ENABLED": "true",
            "COMP_AUTH_SESSION_SECRET": "test-comp-session-secret",
            "COMP_DISCORD_CLIENT_ID": "discord-client-id",
            "COMP_DISCORD_CLIENT_SECRET": "discord-client-secret",
            "COMP_DISCORD_REDIRECT_URI": (
                "http://localhost:5000/api/comp-auth/discord/callback"
            ),
            "COMP_AUTH_FRONTEND_URL": "http://comp.localhost:3000",
            "COMP_AUTH_ADMIN_DISCORD_IDS": "24680,99999",
        },
        redis=fake_redis,
    ) as client:
        import fast_api_app.routes.ripple_public as ripple_public_mod

        calls = []

        def _fake_refresh():
            calls.append("refresh")
            return {"refreshed": True}

        monkeypatch.setattr(
            ripple_public_mod,
            "refresh_ripple_snapshots",
            _fake_refresh,
            raising=False,
        )
        _login_comp_user(client, monkeypatch, "24680")
        res = client.post("/api/ripple/admin/refresh?wait=true")
        assert res.status_code == 200
        assert res.json()["queued"] is False
        assert res.json()["completed"] is True
        assert res.json()["task_name"] == "tasks.refresh_ripple_snapshots"
        assert res.json()["task_id"] is None
        assert res.json()["result"] == {"refreshed": True}
        assert calls == ["refresh"]


def test_admin_player_profile_falls_back_to_db_when_cache_misses(
    client_factory, fake_redis, monkeypatch
):
    async def _fake_db_profile(player_id):
        assert player_id == "p9"
        return {
            "player_id": "p9",
            "display_name": "Fallback Player",
            "eligible": False,
            "ineligible_reason": "not_currently_eligible",
            "minimum_required_tournaments": 3,
            "lifetime_ranked_tournaments": 7,
            "window_tournament_count": 0,
            "progress_to_minimum": {
                "current": 3,
                "required": 3,
                "remaining": 0,
            },
            "stable_rank": None,
            "stable_score": None,
            "display_score": None,
            "danger_days_left": None,
            "last_active_ms": _now_ms() - 10_000,
            "last_tournament_ms": _now_ms() - 10_000,
            "rank_delta": None,
            "display_score_delta": None,
            "delta_is_new": False,
            "delta_has_baseline": False,
            "previous_rank": None,
            "previous_display_score": None,
            "history_generated_at_ms": _now_ms(),
            "history_record_count": 1,
            "history_max_records": 25,
            "tournament_history_ranked": [
                {
                    "tournament_id": 44,
                    "tournament_name": "Fallback Cup",
                    "event_ms": _now_ms() - 10_000,
                    "ranked": True,
                    "placement_label": None,
                    "result_summary": "2W-2L",
                    "team_name": "Fallback Team",
                    "team_id": 8,
                }
            ],
            "match_loo_generated_at_ms": _now_ms(),
            "match_loo_record_count": 0,
            "match_loo_max_records": 20,
            "match_loo_impacts": [],
            "generated_at_ms": _now_ms(),
            "calculated_at_ms": _now_ms(),
            "build_version": "2026.03.29",
            "stale": False,
            "retrieved_at_ms": _now_ms(),
        }

    with client_factory(
        env={
            "COMP_LEADERBOARD_ENABLED": "true",
            "COMP_AUTH_SESSION_SECRET": "test-comp-session-secret",
            "COMP_DISCORD_CLIENT_ID": "discord-client-id",
            "COMP_DISCORD_CLIENT_SECRET": "discord-client-secret",
            "COMP_DISCORD_REDIRECT_URI": (
                "http://localhost:5000/api/comp-auth/discord/callback"
            ),
            "COMP_AUTH_FRONTEND_URL": "http://comp.localhost:3000",
            "COMP_AUTH_ADMIN_DISCORD_IDS": "24680,99999",
        },
        redis=fake_redis,
    ) as client:
        import fast_api_app.routes.ripple_public as ripple_public_mod

        monkeypatch.setattr(
            ripple_public_mod,
            "_load_admin_player_payload_from_db",
            _fake_db_profile,
        )
        _login_comp_user(client, monkeypatch, "24680")
        res = client.get("/api/ripple/admin/player/p9")
        assert res.status_code == 200
        data = res.json()
        assert data["player_id"] == "p9"
        assert data["display_name"] == "Fallback Player"
        assert data["history_record_count"] == 1
        assert data["tournament_history_ranked"][0]["tournament_name"] == "Fallback Cup"


def test_admin_player_profile_returns_404_when_cache_and_db_miss(
    client_factory, fake_redis, monkeypatch
):
    async def _fake_db_profile(_player_id):
        return None

    with client_factory(
        env={
            "COMP_LEADERBOARD_ENABLED": "true",
            "COMP_AUTH_SESSION_SECRET": "test-comp-session-secret",
            "COMP_DISCORD_CLIENT_ID": "discord-client-id",
            "COMP_DISCORD_CLIENT_SECRET": "discord-client-secret",
            "COMP_DISCORD_REDIRECT_URI": (
                "http://localhost:5000/api/comp-auth/discord/callback"
            ),
            "COMP_AUTH_FRONTEND_URL": "http://comp.localhost:3000",
            "COMP_AUTH_ADMIN_DISCORD_IDS": "24680,99999",
        },
        redis=fake_redis,
    ) as client:
        import fast_api_app.routes.ripple_public as ripple_public_mod

        monkeypatch.setattr(
            ripple_public_mod,
            "_load_admin_player_payload_from_db",
            _fake_db_profile,
        )
        _login_comp_user(client, monkeypatch, "24680")
        res = client.get("/api/ripple/admin/player/missing")
        assert res.status_code == 404
        assert res.json()["detail"] == "Player not found in competition index"


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
        assert data["viewer_can_view_results"] is False
        assert "match_loo_generated_at_ms" not in data
        assert "match_loo_record_count" not in data
        assert "match_loo_max_records" not in data
        assert "match_loo_impacts" not in data
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
        assert (
            'http-equiv="refresh" content="0;url=http://testserver/u/p1"'
            in body
        )


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
