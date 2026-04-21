import asyncio
import importlib
import sys
from contextlib import asynccontextmanager

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError


class _RaisingSession:
    def __init__(self, exc):
        self._exc = exc

    async def execute(self, *args, **kwargs):
        raise self._exc


class _FakeMappingsResult:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return self

    def all(self):
        return list(self._rows)

    def first(self):
        return self._rows[0] if self._rows else None


class _FakeSession:
    def __init__(self, rows):
        self._rows = rows
        self.calls = 0
        self.last_query = None
        self.last_params = None

    async def execute(self, *args, **kwargs):
        self.calls += 1
        self.last_query = args[0] if args else None
        self.last_params = args[1] if len(args) > 1 else kwargs
        return _FakeMappingsResult(self._rows)


class _CountingSession:
    def __init__(self, rows):
        self._rows = rows
        self.calls = 0

    async def execute(self, *args, **kwargs):
        self.calls += 1
        return _FakeMappingsResult(self._rows)


def _empty_summary_for(team_ids: list[int], team_names: list[str] | None = None):
    names = team_names or [f"Team {team_id}" for team_id in team_ids]
    primary_team_id = team_ids[0] if team_ids else None
    primary_team_name = names[0] if names else None
    return {
        "primary_team_id": primary_team_id,
        "primary_team_name": primary_team_name,
        "team_ids": team_ids,
        "team_names": names,
        "selected_team_count": len(team_ids),
        "total_matches": 0,
        "wins": 0,
        "losses": 0,
        "unresolved_matches": 0,
        "decided_matches": 0,
        "win_rate": 0.0,
        "tournaments": 0,
        "tournament_tier_distribution": {
            "X": 0,
            "S+": 0,
            "S": 0,
            "A+": 0,
            "A": 0,
            "A-": 0,
            "Unscored": 0,
        },
        "tournament_tier_match_distribution": {
            "X": 0,
            "S+": 0,
            "S": 0,
            "A+": 0,
            "A": 0,
            "A-": 0,
            "Unscored": 0,
        },
    }


def _load_analytics_module(monkeypatch):
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_USER", "user")
    monkeypatch.setenv("DB_PASSWORD", "pass")
    monkeypatch.setenv("DB_NAME", "db")
    monkeypatch.setenv("RANKINGS_DB_NAME", "db")
    module_name = "fast_api_app.routes.analytics"
    if module_name in sys.modules:
        return importlib.reload(sys.modules[module_name])
    return importlib.import_module(module_name)


def test_parse_team_ids_is_permissive_and_dedupes(monkeypatch):
    analytics_mod = _load_analytics_module(monkeypatch)

    assert analytics_mod._parse_team_ids("team=1, alias[3] / 3 / 004", 9) == [
        1,
        3,
        4,
    ]
    assert analytics_mod._parse_team_ids(None, 7) == [7]


def test_normalize_id_sequence_handles_nested_lists(monkeypatch):
    analytics_mod = _load_analytics_module(monkeypatch)

    assert analytics_mod._normalize_id_sequence([[1, "2"], 3, [2, 4]]) == [
        1,
        2,
        3,
        4,
    ]


def test_build_team_matches_payload_normalizes_subject_side_and_fallbacks(
    monkeypatch,
):
    analytics_mod = _load_analytics_module(monkeypatch)

    payload = analytics_mod._build_team_matches_payload(
        snapshot_id=7,
        team_ids=[1, 3],
        rows=[
            {
                "match_id": 11,
                "tournament_id": 101,
                "team1_id": 2,
                "team2_id": 1,
                "winner_team_id": None,
                "team1_score": 1.0,
                "team2_score": 3.0,
                "tournament_name": "Older Event",
                "tournament_mode": "Tower Control",
                "map_picking_style": "counterpick",
                "tournament_tags": ["regional"],
                "event_time_ms": 1_000,
            },
            {
                "match_id": 12,
                "tournament_id": 102,
                "team1_id": 3,
                "team2_id": 4,
                "winner_team_id": 4,
                "team1_score": 2.0,
                "team2_score": 3.0,
                "tournament_name": "Newer Event",
                "tournament_mode": "Splat Zones",
                "map_picking_style": "neutral",
                "tournament_tags": ["major"],
                "event_time_ms": 2_000,
            },
        ],
        team_names={
            1: "Alpha",
            3: "Alpha Prime",
            2: "Bravo",
            4: "Charlie",
        },
        rosters={
            (11, 101, 1): [{"player_id": 101, "player_name": "Player A"}],
            (11, 101, 2): [{"player_id": 201, "player_name": "Player B"}],
            (12, 102, 3): [{"player_id": 102, "player_name": "Player C"}],
            (12, 102, 4): [{"player_id": 202, "player_name": "Player D"}],
        },
        match_rounds={},
        tournament_scores={101: 8.0, 102: 30.0},
    )

    assert payload["snapshot_id"] == 7
    assert payload["summary"]["team_ids"] == [1, 3]
    assert payload["summary"]["team_names"] == ["Alpha", "Alpha Prime"]
    assert payload["summary"]["total_matches"] == 2
    assert payload["summary"]["wins"] == 1
    assert payload["summary"]["losses"] == 1
    assert payload["summary"]["unresolved_matches"] == 0
    assert payload["summary"]["decided_matches"] == 2
    assert payload["summary"]["win_rate"] == 0.5
    assert payload["summary"]["tournaments"] == 2
    assert set(payload["summary"]["tournament_tier_distribution"]) == {
        "X",
        "S+",
        "S",
        "A+",
        "A",
        "A-",
        "Unscored",
    }
    assert set(payload["summary"]["tournament_tier_match_distribution"]) == {
        "X",
        "S+",
        "S",
        "A+",
        "A",
        "A-",
        "Unscored",
    }

    newer_match = payload["matches"][0]
    older_match = payload["matches"][1]

    assert newer_match["match_id"] == 12
    assert newer_match["team_id"] == 3
    assert newer_match["team_name"] == "Alpha Prime"
    assert newer_match["opponent_team_id"] == 4
    assert newer_match["opponent_team_name"] == "Charlie"
    assert newer_match["winner_side"] == "opponent"
    assert newer_match["team_is_winner"] is False
    assert newer_match["opponent_is_winner"] is True

    assert older_match["match_id"] == 11
    assert older_match["team_id"] == 1
    assert older_match["team_name"] == "Alpha"
    assert older_match["opponent_team_id"] == 2
    assert older_match["opponent_team_name"] == "Bravo"
    assert older_match["winner_side"] == "team"
    assert older_match["team_is_winner"] is True
    assert older_match["opponent_is_winner"] is False
    assert older_match["team_roster"] == [
        {"player_id": 101, "player_name": "Player A"}
    ]
    assert older_match["opponent_roster"] == [
        {"player_id": 201, "player_name": "Player B"}
    ]
    assert older_match["match_rounds"] == [
        {
            "round_no": None,
            "maps_count": None,
            "map_index": 1,
            "map_name": None,
            "map_mode": None,
            "team_a_score": 3.0,
            "team_b_score": 1.0,
            "winner_team_id": None,
            "winner_side": "team",
        }
    ]


def test_build_team_matches_payload_treats_near_equal_scores_as_unresolved(
    monkeypatch,
):
    analytics_mod = _load_analytics_module(monkeypatch)

    payload = analytics_mod._build_team_matches_payload(
        snapshot_id=7,
        team_ids=[1],
        rows=[
            {
                "match_id": 21,
                "tournament_id": 201,
                "team1_id": 1,
                "team2_id": 2,
                "winner_team_id": None,
                "team1_score": 3.0,
                "team2_score": 3.0 + 1e-12,
                "event_time_ms": 1_000,
            }
        ],
        team_names={1: "Alpha", 2: "Bravo"},
    )

    assert payload["summary"]["wins"] == 0
    assert payload["summary"]["losses"] == 0
    assert payload["summary"]["unresolved_matches"] == 1
    assert payload["summary"]["decided_matches"] == 0
    assert payload["matches"][0]["winner_side"] is None
    assert payload["matches"][0]["team_is_winner"] is False
    assert payload["matches"][0]["opponent_is_winner"] is False


def test_tournament_tier_boundaries(monkeypatch):
    analytics_mod = _load_analytics_module(monkeypatch)

    assert analytics_mod._tournament_tier(5.0) == {
        "tier_id": "x",
        "tier_label": "X",
    }
    assert analytics_mod._tournament_tier(160.0) == {
        "tier_id": "a_minus",
        "tier_label": "A-",
    }
    assert analytics_mod._tournament_tier(161.0) == {
        "tier_id": "a_minus",
        "tier_label": "A-",
    }


def test_get_table_columns_map_returns_empty_sets_on_error(monkeypatch):
    analytics_mod = _load_analytics_module(monkeypatch)

    result = asyncio.run(
        analytics_mod._get_table_columns_map(
            _RaisingSession(RuntimeError("boom")),
            "comp_rankings",
            ["matches", "players"],
        )
    )

    assert result == {"matches": set(), "players": set()}


def test_get_table_columns_map_uses_ttl_cache(monkeypatch):
    analytics_mod = _load_analytics_module(monkeypatch)

    session = _CountingSession(
        [{"table_name": "matches", "column_name": "match_id"}]
    )
    first = asyncio.run(
        analytics_mod._get_table_columns_map(
            session,
            "comp_rankings",
            ["matches"],
        )
    )
    second = asyncio.run(
        analytics_mod._get_table_columns_map(
            session,
            "comp_rankings",
            ["matches"],
        )
    )

    assert first == {"matches": {"match_id"}}
    assert second == {"matches": {"match_id"}}
    assert session.calls == 1


def test_missing_error_helpers_do_not_overlap(monkeypatch):
    analytics_mod = _load_analytics_module(monkeypatch)

    column_exc = Exception('column "foo" does not exist')
    relation_exc = Exception('relation "foo" does not exist')

    assert analytics_mod._is_missing_column_error(column_exc) is True
    assert analytics_mod._is_missing_relation_error(column_exc) is False
    assert analytics_mod._is_missing_relation_error(relation_exc) is True
    assert analytics_mod._is_missing_column_error(relation_exc) is False


def test_normalize_tournament_tags(monkeypatch):
    analytics_mod = _load_analytics_module(monkeypatch)

    assert analytics_mod._normalize_tournament_tags(None) is None
    assert analytics_mod._normalize_tournament_tags(" major ") == ["major"]
    assert analytics_mod._normalize_tournament_tags(
        ["major", "major", "regional", ""]
    ) == ["major", "regional"]
    assert analytics_mod._normalize_tournament_tags({"b", "a"}) == ["a", "b"]


def test_team_matches_cache_key_canonicalizes_alias_order(monkeypatch):
    analytics_mod = _load_analytics_module(monkeypatch)

    key_a = analytics_mod._team_matches_cache_key(
        schema="comp_rankings",
        snapshot_id=7,
        team_ids=[1, 3, 5],
        limit=25,
    )
    key_b = analytics_mod._team_matches_cache_key(
        schema="comp_rankings",
        snapshot_id=7,
        team_ids=[1, 5, 3],
        limit=25,
    )

    assert key_a == key_b


def test_fetch_match_rows_returns_empty_when_query_unavailable(monkeypatch):
    analytics_mod = _load_analytics_module(monkeypatch)

    result = asyncio.run(
        analytics_mod._fetch_match_rows(
            _RaisingSession(SQLAlchemyError("undefinedtable")),
            schema="comp_rankings",
            team_ids=[1],
            limit=25,
            match_columns={"match_id", "team1_id", "team2_id"},
            tournament_columns=set(),
        )
    )

    assert result == []


def test_fetch_match_rows_returns_empty_on_access_error(monkeypatch):
    analytics_mod = _load_analytics_module(monkeypatch)

    result = asyncio.run(
        analytics_mod._fetch_match_rows(
            _RaisingSession(SQLAlchemyError("permission denied")),
            schema="comp_rankings",
            team_ids=[1],
            limit=25,
            match_columns={"match_id", "team1_id", "team2_id"},
            tournament_columns=set(),
        )
    )

    assert result == []


def test_fetch_match_rounds_uses_placeholder_maps_without_scores(monkeypatch):
    analytics_mod = _load_analytics_module(monkeypatch)

    result = asyncio.run(
        analytics_mod._fetch_match_rounds(
            _FakeSession(
                [
                    {
                        "match_id": 11,
                        "round_id": 1,
                        "round_no": 2,
                        "maps_count": 3,
                        "map_mode": "Tower Control",
                    }
                ]
            ),
            schema="comp_rankings",
            rows=[
                {
                    "match_id": 11,
                    "tournament_id": 101,
                    "team1_id": 1,
                    "team2_id": 2,
                    "winner_team_id": 1,
                    "team1_score": 3.0,
                    "team2_score": 1.0,
                }
            ],
            selected_team_ids=[1],
            match_columns={"round_id"},
            round_columns={"round_id", "number", "maps_count", "maps_type"},
        )
    )

    rounds = result[(11, 101)]
    assert len(rounds) == 3
    assert [round_row["map_index"] for round_row in rounds] == [1, 2, 3]
    assert all(round_row["team_a_score"] is None for round_row in rounds)
    assert all(round_row["team_b_score"] is None for round_row in rounds)
    assert all(round_row["winner_team_id"] is None for round_row in rounds)
    assert all(round_row["winner_side"] is None for round_row in rounds)


def test_fetch_tournament_scores_dedupes_ids_and_maps_results(monkeypatch):
    analytics_mod = _load_analytics_module(monkeypatch)

    session = _FakeSession(
        [
            {"tournament_id": 101, "tournament_score": 10.0},
            {"tournament_id": 202, "tournament_score": 25.0},
        ]
    )
    result = asyncio.run(
        analytics_mod._fetch_tournament_scores(
            session,
            schema="comp_rankings",
            tournament_ids=[101, 101, 202],
            rankings_columns={"player_id", "score"},
            pat_columns={"tournament_id", "player_id"},
        )
    )

    assert result == {101: 10.0, 202: 25.0}
    assert session.last_params == {"tournament_ids": [101, 202]}


def test_fetch_team_matches_payload_degrades_on_enrichment_timeout(
    monkeypatch,
):
    analytics_mod = _load_analytics_module(monkeypatch)

    async def fake_get_table_columns_map(session, schema, tables):
        return {
            "matches": set(),
            "tournaments": set(),
            "player_appearance_teams": set(),
            "players": set(),
            "rounds": set(),
            "player_rankings": set(),
        }

    async def fake_fetch_match_rows(*args, **kwargs):
        return [
            {
                "match_id": 11,
                "tournament_id": 101,
                "team1_id": 1,
                "team2_id": 2,
                "winner_team_id": None,
                "team1_score": 3.0,
                "team2_score": 1.0,
                "event_time_ms": 1000,
            }
        ]

    async def fake_fetch_team_name_map(*args, **kwargs):
        return {1: "Alpha", 2: "Bravo"}

    async def fake_slow_enrichment(**kwargs):
        await asyncio.sleep(0.01)
        return {"slow": "value"}

    monkeypatch.setattr(
        analytics_mod,
        "_get_table_columns_map",
        fake_get_table_columns_map,
        raising=False,
    )
    monkeypatch.setattr(
        analytics_mod,
        "_fetch_match_rows",
        fake_fetch_match_rows,
        raising=False,
    )
    monkeypatch.setattr(
        analytics_mod,
        "_fetch_team_name_map",
        fake_fetch_team_name_map,
        raising=False,
    )
    monkeypatch.setattr(
        analytics_mod,
        "_fetch_match_rosters_in_new_session",
        fake_slow_enrichment,
        raising=False,
    )
    monkeypatch.setattr(
        analytics_mod,
        "_fetch_match_rounds_in_new_session",
        fake_slow_enrichment,
        raising=False,
    )
    monkeypatch.setattr(
        analytics_mod,
        "_fetch_tournament_scores_in_new_session",
        fake_slow_enrichment,
        raising=False,
    )
    monkeypatch.setattr(
        analytics_mod,
        "_TEAM_MATCHES_ENRICH_TIMEOUT_SECONDS",
        0.0,
        raising=False,
    )

    payload = asyncio.run(
        analytics_mod._fetch_team_matches_payload(
            object(),
            snapshot_id=7,
            team_ids=[1],
            limit=25,
        )
    )

    assert payload["summary"]["total_matches"] == 1
    assert payload["matches"][0]["team_name"] == "Alpha"
    assert payload["matches"][0]["opponent_team_name"] == "Bravo"
    assert payload["matches"][0]["team_roster"] == []
    assert payload["matches"][0]["opponent_roster"] == []
    assert payload["matches"][0]["tournament_score"] is None


def test_team_matches_route_uses_cached_latest_snapshot_payload(
    client, fake_redis, monkeypatch
):
    analytics_mod = _load_analytics_module(monkeypatch)
    monkeypatch.setenv("TRUST_PROXY_HEADERS", "1")
    monkeypatch.setattr(analytics_mod, "redis_conn", fake_redis, raising=False)

    schema = analytics_mod.ripple_queries.schema_name()
    latest_snapshot_key = analytics_mod._latest_snapshot_cache_key(schema)
    payload_cache_key = analytics_mod._team_matches_cache_key(
        schema=schema,
        snapshot_id=9,
        team_ids=[1, 3],
        limit=17,
    )
    fake_redis.setex(latest_snapshot_key, 30, "9")
    fake_redis.setex(
        payload_cache_key,
        120,
        analytics_mod.orjson.dumps(
            {
                "snapshot_id": 9,
                "summary": {
                    "primary_team_id": 1,
                    "primary_team_name": "Alpha",
                    "team_ids": [1, 3],
                    "team_names": ["Alpha", "Alpha Prime"],
                    "selected_team_count": 2,
                    "total_matches": 0,
                    "wins": 0,
                    "losses": 0,
                    "unresolved_matches": 0,
                    "decided_matches": 0,
                    "win_rate": 0.0,
                    "tournaments": 0,
                    "tournament_tier_distribution": {
                        "X": 0,
                        "S+": 0,
                        "S": 0,
                        "A+": 0,
                        "A": 0,
                        "A-": 0,
                        "Unscored": 0,
                    },
                    "tournament_tier_match_distribution": {
                        "X": 0,
                        "S+": 0,
                        "S": 0,
                        "A+": 0,
                        "A": 0,
                        "A-": 0,
                        "Unscored": 0,
                    },
                },
                "matches": [],
            }
        ),
    )

    @asynccontextmanager
    async def fail_session():
        raise AssertionError("DB session should not be opened for hot cache")
        yield object()

    monkeypatch.setattr(
        analytics_mod, "rankings_async_session", fail_session, raising=False
    )

    response = client.get(
        "/api/analytics/team/1/matches?team_ids=1,3&limit=17",
        headers={"x-forwarded-for": "203.0.113.10"},
    )

    assert response.status_code == 200
    assert response.json()["snapshot_id"] == 9
    assert response.json()["summary"]["team_ids"] == [1, 3]


def test_team_matches_route_prepends_path_team_id(
    client, fake_redis, monkeypatch
):
    analytics_mod = _load_analytics_module(monkeypatch)
    monkeypatch.setenv("TRUST_PROXY_HEADERS", "1")
    monkeypatch.setattr(analytics_mod, "redis_conn", fake_redis, raising=False)
    seen = {}

    @asynccontextmanager
    async def fake_session():
        yield object()

    async def fake_resolve_snapshot_id(session, snapshot_id):
        seen["snapshot_id_input"] = snapshot_id
        return 7

    async def fake_fetch_team_matches_payload(
        session,
        *,
        snapshot_id,
        team_ids,
        limit,
    ):
        seen["resolved_snapshot_id"] = snapshot_id
        seen["team_ids"] = team_ids
        seen["limit"] = limit
        return {
            "snapshot_id": snapshot_id,
            "summary": _empty_summary_for(team_ids),
            "matches": [],
        }

    monkeypatch.setattr(
        analytics_mod, "rankings_async_session", fake_session, raising=False
    )
    monkeypatch.setattr(
        analytics_mod,
        "_resolve_snapshot_id",
        fake_resolve_snapshot_id,
        raising=False,
    )
    monkeypatch.setattr(
        analytics_mod,
        "_fetch_team_matches_payload",
        fake_fetch_team_matches_payload,
        raising=False,
    )

    response = client.get(
        "/api/analytics/team/1/matches?team_ids=3,1,5&limit=200",
        headers={"x-forwarded-for": "203.0.113.11"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "snapshot_id": 7,
        "summary": _empty_summary_for([1, 3, 5]),
        "matches": [],
    }
    assert seen == {
        "snapshot_id_input": None,
        "resolved_snapshot_id": 7,
        "team_ids": [1, 3, 5],
        "limit": 200,
    }


def test_team_matches_route_returns_503_when_snapshot_unavailable(
    client, fake_redis, monkeypatch
):
    analytics_mod = _load_analytics_module(monkeypatch)
    monkeypatch.setenv("TRUST_PROXY_HEADERS", "1")
    monkeypatch.setattr(analytics_mod, "redis_conn", fake_redis, raising=False)

    @asynccontextmanager
    async def fake_session():
        yield object()

    async def fake_resolve_snapshot_id(session, snapshot_id):
        raise HTTPException(
            status_code=503,
            detail="No completed team-search snapshot available yet.",
        )

    monkeypatch.setattr(
        analytics_mod, "rankings_async_session", fake_session, raising=False
    )
    monkeypatch.setattr(
        analytics_mod,
        "_resolve_snapshot_id",
        fake_resolve_snapshot_id,
        raising=False,
    )

    response = client.get(
        "/api/analytics/team/1/matches",
        headers={"x-forwarded-for": "203.0.113.12"},
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "No completed team-search snapshot available yet."
    }


def test_team_matches_route_rejects_too_many_team_ids(
    client, fake_redis, monkeypatch
):
    analytics_mod = _load_analytics_module(monkeypatch)
    monkeypatch.setenv("TRUST_PROXY_HEADERS", "1")
    monkeypatch.setattr(analytics_mod, "redis_conn", fake_redis, raising=False)

    response = client.get(
        "/api/analytics/team/1/matches?team_ids=2,3,4,5,6,7,8,9,10,11",
        headers={"x-forwarded-for": "203.0.113.14"},
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "At most 10 team IDs are allowed per request."
    }


def test_team_matches_route_caches_explicit_snapshot_requests(
    client, fake_redis, monkeypatch
):
    analytics_mod = _load_analytics_module(monkeypatch)
    monkeypatch.setenv("TRUST_PROXY_HEADERS", "1")
    monkeypatch.setattr(analytics_mod, "redis_conn", fake_redis, raising=False)

    seen = {"session_entries": 0, "fetch_calls": 0}

    @asynccontextmanager
    async def fake_session():
        seen["session_entries"] += 1
        yield object()

    async def fake_fetch_team_matches_payload(
        session,
        *,
        snapshot_id,
        team_ids,
        limit,
    ):
        seen["fetch_calls"] += 1
        return {
            "snapshot_id": snapshot_id,
            "summary": _empty_summary_for(team_ids),
            "matches": [
                {
                    "match_id": 11,
                    "team_id": 1,
                    "team_name": "Alpha",
                    "opponent_team_id": 2,
                    "opponent_team_name": "Bravo",
                    "tournament_id": None,
                    "tournament_name": None,
                    "tournament_mode": None,
                    "map_picking_style": None,
                    "tournament_tags": None,
                    "tournament_score": None,
                    "tournament_score_tier_id": "unscored",
                    "tournament_score_tier": "Unscored",
                    "winner_team_id": None,
                    "winner_side": None,
                    "team_score": None,
                    "opponent_score": None,
                    "team_roster": [],
                    "opponent_roster": [],
                    "event_time_ms": None,
                    "match_rounds": [],
                    "team_is_winner": False,
                    "opponent_is_winner": False,
                }
            ],
        }

    monkeypatch.setattr(
        analytics_mod, "rankings_async_session", fake_session, raising=False
    )
    monkeypatch.setattr(
        analytics_mod,
        "_fetch_team_matches_payload",
        fake_fetch_team_matches_payload,
        raising=False,
    )

    response_one = client.get(
        "/api/analytics/team/1/matches?team_ids=1,3&snapshot_id=7&limit=17",
        headers={"x-forwarded-for": "203.0.113.13"},
    )
    response_two = client.get(
        "/api/analytics/team/1/matches?team_ids=1,3&snapshot_id=7&limit=17",
        headers={"x-forwarded-for": "203.0.113.13"},
    )

    expected_payload = {
        "snapshot_id": 7,
        "summary": _empty_summary_for([1, 3]),
        "matches": [
            {
                "match_id": 11,
                "team_id": 1,
                "team_name": "Alpha",
                "opponent_team_id": 2,
                "opponent_team_name": "Bravo",
                "tournament_id": None,
                "tournament_name": None,
                "tournament_mode": None,
                "map_picking_style": None,
                "tournament_tags": None,
                "tournament_score": None,
                "tournament_score_tier_id": "unscored",
                "tournament_score_tier": "Unscored",
                "winner_team_id": None,
                "winner_side": None,
                "team_score": None,
                "opponent_score": None,
                "team_roster": [],
                "opponent_roster": [],
                "event_time_ms": None,
                "match_rounds": [],
                "team_is_winner": False,
                "opponent_is_winner": False,
            }
        ],
    }
    assert response_one.status_code == 200
    assert response_two.status_code == 200
    assert response_one.json() == expected_payload
    assert response_two.json() == expected_payload
    assert seen == {"session_entries": 1, "fetch_calls": 1}
