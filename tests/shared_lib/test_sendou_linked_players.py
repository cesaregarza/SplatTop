from shared_lib.sendou_linked_players import (
    SeasonMonthYear,
    SendouAlignmentError,
    map_seasons_to_sendou_month_years,
    summarize_linked_players,
    validate_and_join_rows,
)


def test_map_seasons_to_sendou_month_years_requires_matching_counts():
    try:
        map_seasons_to_sendou_month_years(
            [14, 13], [{"month": 3, "year": 2026}]
        )
    except SendouAlignmentError as exc:
        assert "Season counts do not match" in str(exc)
    else:
        raise AssertionError("Expected SendouAlignmentError")


def test_validate_and_join_rows_extracts_linked_fields():
    season = SeasonMonthYear(season_number=14, month=3, year=2026)
    xscraper_rows = [
        {
            "rank": 1,
            "player_id": "u-example",
            "x_power": 3000.0,
            "weapon_id": 220,
        }
    ]
    sendou_rows = [
        {
            "rank": 1,
            "power": 3000.0,
            "weaponSplId": 220,
            "playerId": 364,
            "customUrl": "sendou",
            "discordId": "79237403620945920",
        }
    ]

    rows = validate_and_join_rows(
        xscraper_rows,
        sendou_rows,
        season=season,
        mode="Splat Zones",
        region=False,
    )

    assert rows == [
        {
            "season_number": 14,
            "month": 3,
            "year": 2026,
            "mode": "Splat Zones",
            "region": "Tentatek",
            "rank": 1,
            "x_power": 3000.0,
            "weapon_id": 220,
            "npln_id": "u-example",
            "sendou_player_id": 364,
            "sendou_discord_id": "79237403620945920",
            "sendou_custom_url": "sendou",
            "sendou_user_url": "https://sendou.ink/u/sendou",
            "linked": True,
        }
    ]


def test_validate_and_join_rows_rejects_mismatched_weapon():
    season = SeasonMonthYear(season_number=14, month=3, year=2026)
    xscraper_rows = [
        {
            "rank": 1,
            "player_id": "u-example",
            "x_power": 3000.0,
            "weapon_id": 220,
        }
    ]
    sendou_rows = [
        {
            "rank": 1,
            "power": 3000.0,
            "weaponSplId": 221,
            "playerId": 364,
            "customUrl": None,
            "discordId": None,
        }
    ]

    try:
        validate_and_join_rows(
            xscraper_rows,
            sendou_rows,
            season=season,
            mode="Splat Zones",
            region=False,
        )
    except SendouAlignmentError as exc:
        assert "Weapon mismatch" in str(exc)
    else:
        raise AssertionError("Expected SendouAlignmentError")


def test_summarize_linked_players_rejects_conflicts():
    evidence_rows = [
        {
            "linked": True,
            "npln_id": "u-example",
            "sendou_player_id": 10,
            "sendou_discord_id": "1",
            "sendou_custom_url": None,
            "sendou_user_url": "https://sendou.ink/u/1",
            "season_number": 14,
            "mode": "Splat Zones",
            "region": "Tentatek",
            "rank": 1,
            "x_power": 3000.0,
        },
        {
            "linked": True,
            "npln_id": "u-example",
            "sendou_player_id": 11,
            "sendou_discord_id": "2",
            "sendou_custom_url": None,
            "sendou_user_url": "https://sendou.ink/u/2",
            "season_number": 13,
            "mode": "Rainmaker",
            "region": "Takoroka",
            "rank": 2,
            "x_power": 2990.0,
        },
    ]

    try:
        summarize_linked_players(evidence_rows)
    except SendouAlignmentError as exc:
        assert "multiple sendou player IDs" in str(exc)
    else:
        raise AssertionError("Expected SendouAlignmentError")
