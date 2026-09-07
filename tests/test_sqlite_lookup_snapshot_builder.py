import pytest

from shared_lib.sqlite_lookup_snapshot import (
    create_lookup_snapshot_database,
    populate_lookup_snapshot_database,
)


@pytest.mark.parametrize("count", [0, 3])
def test_populate_accepts_one_shot_iterators_and_counts_inserted_rows(
    tmp_path, count
):
    connection = create_lookup_snapshot_database(tmp_path / "lookup.sqlite3")
    try:
        counts = populate_lookup_snapshot_database(
            connection,
            aliases=(
                {"splashtag": f"Player {i}", "player_id": f"p{i}"}
                for i in range(count)
            ),
            weapon_rows=(
                {
                    "player_id": f"p{i}",
                    "season_number": 1,
                    "mode": "Splat Zones",
                    "region": False,
                    "weapon_id": 101,
                    "max_x_power": 2500.0,
                    "games_played": 50,
                    "percent_games_played": 0.75,
                }
                for i in range(count + 1)
            ),
            season_rows=(
                {
                    "player_id": f"p{i}",
                    "season_number": 1,
                    "mode": "Splat Zones",
                    "region": False,
                    "weapon_id": 101,
                    "x_power": 2500.0,
                    "rank": i + 1,
                }
                for i in range(count + 2)
            ),
        )
        assert counts == {
            "aliases": count,
            "weapon_leaderboard_peak": count + 1,
            "season_results": count + 2,
        }
        assert connection.execute(
            "SELECT alias, player_id FROM aliases ORDER BY player_id"
        ).fetchall() == [(f"Player {i}", f"p{i}") for i in range(count)]
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM weapon_leaderboard_peak"
            ).fetchone()[0]
            == count + 1
        )
        assert connection.execute(
            "SELECT SUM(rank) FROM season_results"
        ).fetchone()[0] == sum(range(1, count + 3))

        # Counts describe inserted rows, excluding deletion of the old snapshot.
        empty_counts = populate_lookup_snapshot_database(
            connection,
            aliases=iter(()),
            weapon_rows=iter(()),
            season_rows=iter(()),
        )
        assert empty_counts == dict.fromkeys(counts, 0)
        assert (
            connection.execute("SELECT COUNT(*) FROM aliases").fetchone()[0]
            == 0
        )
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM weapon_leaderboard_peak"
            ).fetchone()[0]
            == 0
        )
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM season_results"
            ).fetchone()[0]
            == 0
        )
    finally:
        connection.close()
