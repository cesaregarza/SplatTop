"""SQL parity checks against an explicitly supplied disposable PostgreSQL DB.

Run with SPLAT_TEST_POSTGRES_DSN set. Each test rolls back its unique schema.
The existing Python selector is the reference for the previous full-row path.
"""

from __future__ import annotations

import asyncio
import os
import random
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

for _name, _value in {
    "DB_HOST": "localhost",
    "DB_PORT": "5432",
    "DB_USER": "user",
    "DB_PASSWORD": "pass",
    "DB_NAME": "db",
    "RANKINGS_DB_NAME": "db",
}.items():
    os.environ.setdefault(_name, _value)

from celery_app.tasks import ripple_snapshot as snapshot_mod
from shared_lib.queries.player_match_loo import build_player_match_loo_query


@pytest.fixture
def impact_db(monkeypatch):
    dsn = os.environ.get("SPLAT_TEST_POSTGRES_DSN")
    if not dsn:
        pytest.skip("Set SPLAT_TEST_POSTGRES_DSN to a disposable PostgreSQL DB")
    engine = create_engine(dsn, poolclass=NullPool)
    schema = f"splat_loo_test_{uuid4().hex}"
    try:
        with engine.connect() as conn:
            transaction = conn.begin()
            try:
                conn.execute(text("SET LOCAL statement_timeout = '10s'"))
                conn.execute(text(f'CREATE SCHEMA "{schema}"'))
                definitions = {
                    "player_match_loo_impacts": """
                        player_id text, match_id bigint, tournament_id bigint,
                        calculated_at_ms bigint, build_version text,
                        player_rank int, player_score double precision,
                        is_win boolean, exact_score_delta double precision,
                        exact_abs_delta double precision
                    """,
                    "player_appearance_teams": """
                        player_id text, match_id bigint, tournament_id bigint,
                        team_id bigint
                    """,
                    "tournaments": """
                        tournament_id bigint PRIMARY KEY, name text,
                        start_time_ms bigint
                    """,
                    "matches": """
                        match_id bigint, tournament_id bigint,
                        last_game_finished_at_ms bigint,
                        winner_team_id bigint, loser_team_id bigint,
                        team1_id bigint, team1_score int,
                        team2_id bigint, team2_score int,
                        PRIMARY KEY (match_id, tournament_id)
                    """,
                    "tournament_teams": """
                        tournament_id bigint, team_id bigint, name text,
                        PRIMARY KEY (tournament_id, team_id)
                    """,
                    "players": "player_id text PRIMARY KEY, display_name text",
                }
                for table, columns in definitions.items():
                    conn.execute(
                        text(f'CREATE TABLE "{schema}".{table} ({columns})')
                    )
                monkeypatch.setattr(
                    snapshot_mod.ripple_queries, "_schema", lambda: schema
                )
                yield conn, schema
            finally:
                transaction.rollback()
    finally:
        engine.dispose()


def insert_impacts(conn, schema, rows):
    conn.execute(
        text(f"""
            INSERT INTO "{schema}".player_match_loo_impacts
            (player_id, match_id, tournament_id, calculated_at_ms, build_version,
             player_rank, player_score, is_win, exact_score_delta, exact_abs_delta)
            VALUES (:player_id, :match_id, 42, :calculated_at_ms, :build_version,
                    7, 1.75, true, :exact_score_delta, :exact_abs_delta)
        """),
        rows,
    )


def make_rows(player, deltas, *, timestamp=1234, version="v1"):
    return [
        {
            "player_id": player,
            "match_id": index + 1,
            "exact_score_delta": delta,
            # Intentionally not always abs(delta): selection first balances
            # signed scores, then uses stored absolute impacts for backfill.
            "exact_abs_delta": (
                None if index % 11 == 0 else (index * 7) % 23 / 10
            ),
            "calculated_at_ms": timestamp,
            "build_version": version,
        }
        for index, delta in enumerate(deltas)
    ]


@pytest.mark.parametrize("limit", [1, 2, 3, 7, 20, 51, 250])
def test_query_matches_full_python_selection_and_bounds_rows(impact_db, limit):
    conn, schema = impact_db
    rng = random.Random(17)
    cases = {
        "balanced": [
            rng.choice([-3.0, -0.1, 0, 0.1, 2.0, None]) for _ in range(180)
        ],
        "harmful": [float(index % 9 + 1) for index in range(100)],
        "helpful": [-float(index % 9 + 1) for index in range(100)],
        "neutral": [None, 0.0] * 60,
        "sparse": [4.0, -0.1, 0, None],
        "lopsided": [2.0] * 60 + [-0.01, -0.02] + [0.0] * 30,
        "missing_abs": [1.0, -1.0] * 40,
    }
    by_player = {
        player: make_rows(player, deltas) for player, deltas in cases.items()
    }
    for row in by_player["missing_abs"]:
        row["exact_abs_delta"] = None
    insert_impacts(
        conn, schema, [row for rows in by_player.values() for row in rows]
    )
    # A different build/time must not change the selected rows.
    insert_impacts(
        conn, schema, make_rows("balanced", [1000.0], timestamp=9999)
    )
    insert_impacts(
        conn, schema, make_rows("balanced", [1000.0], version="other")
    )
    actual = (
        conn.execute(
            build_player_match_loo_query(schema),
            {
                "player_ids": list(cases),
                "calculated_at_ms": 1234,
                "build_version": "v1",
                "match_any_build_version": False,
                "max_per_player": limit,
            },
        )
        .mappings()
        .all()
    )
    assert len(actual) <= len(cases) * limit
    for player, full_rows in by_player.items():
        expected = snapshot_mod._select_player_match_loo_rows(
            full_rows, max_per_player=limit
        )
        selected = [row for row in actual if row["player_id"] == player]
        assert [row["match_id"] for row in selected] == [
            row["match_id"] for row in expected
        ]
        assert len(selected) == min(limit, len(full_rows))


@pytest.mark.parametrize("build_version", ["v1", None])
def test_fetch_preserves_fallback_batches_and_roster_enrichment(
    impact_db, monkeypatch, build_version
):
    conn, schema = impact_db
    by_player = {
        "p1": make_rows("p1", [0.4, -0.2, 0.9], version=build_version),
        "p2": make_rows("p2", [0.3, -0.8, 1.2], timestamp=1000, version=None),
        "p3": make_rows("p3", [0.5, -0.1, 1.0], timestamp=900, version="older"),
    }
    insert_impacts(
        conn, schema, [row for rows in by_player.values() for row in rows]
    )
    if build_version is None:
        extra = make_rows("p1", [2.0], version="another")
        extra[0]["match_id"] = 4
        by_player["p1"].extend(extra)
        insert_impacts(conn, schema, extra)
    for statement in [
        f"INSERT INTO {schema}.tournaments VALUES (42, 'Cup', 1000)",
        f"INSERT INTO {schema}.tournament_teams VALUES (42, 10, 'Alpha'), (42, 20, 'Bravo')",
        f"INSERT INTO {schema}.players VALUES ('p1', ' One '), ('mate', 'Mate'), ('foe', 'Opponent')",
        f"""INSERT INTO {schema}.matches
            SELECT n, 42, 2000, 10, 20, 10, 3, 20, 1 FROM generate_series(1, 4) n""",
        f"""INSERT INTO {schema}.player_appearance_teams
            SELECT p, n, 42, t FROM generate_series(1, 4) n
            CROSS JOIN (VALUES ('p1', 10), ('mate', 10), ('foe', 20)) AS v(p, t)""",
    ]:
        conn.execute(text(statement))
    monkeypatch.setattr(snapshot_mod, "PLAYER_MATCH_LOO_CHUNK_SIZE", 2)

    class Session:
        async def execute(self, query, params):
            return conn.execute(query, params)

        async def rollback(self):
            pytest.fail("Query unexpectedly failed")

    result = asyncio.run(
        snapshot_mod._fetch_player_match_loo_impacts(
            Session(),
            ["p1", "p2", "p3", "missing"],
            calculated_at_ms=1234,
            build_version=build_version,
            max_per_player=2,
        )
    )
    assert set(result) == set(by_player)
    for player, rows in by_player.items():
        expected = snapshot_mod._select_player_match_loo_rows(
            rows, max_per_player=2
        )
        assert [row["match_id"] for row in result[player]] == [
            row["match_id"] for row in expected
        ]
        assert all(row["player_team_name"] == "Alpha" for row in result[player])
        assert all(
            row["opponent_team_name"] == "Bravo" for row in result[player]
        )
        assert all(
            row["player_team_players"] == ["Mate", "One"]
            for row in result[player]
        )
        assert all(
            row["opponent_team_players"] == ["Opponent"]
            for row in result[player]
        )
        assert all(row["event_ms"] == 2_000_000 for row in result[player])
