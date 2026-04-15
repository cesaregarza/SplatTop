from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Any, Sequence

import httpx

from shared_lib.turbo_stream import decode_turbo_stream

FETCH_TIMEOUT_SECONDS = 30.0
POWER_TOLERANCE = 1e-6

XSCRAPER_TO_SENDOU_MODE = {
    "Splat Zones": "SZ",
    "Tower Control": "TC",
    "Rainmaker": "RM",
    "Clam Blitz": "CB",
}

XSCRAPER_TO_SENDOU_REGION = {
    False: "WEST",
    True: "JPN",
}

SENDOU_REGION_LABELS = {
    "WEST": "Tentatek",
    "JPN": "Takoroka",
}


class SendouAlignmentError(ValueError):
    """Raised when xscraper and sendou rows fail alignment checks."""


@dataclass(frozen=True)
class SeasonMonthYear:
    season_number: int
    month: int
    year: int


def map_seasons_to_sendou_month_years(
    season_numbers: Sequence[int],
    available_month_years: Sequence[dict[str, int]],
) -> list[SeasonMonthYear]:
    ordered_seasons = sorted(set(season_numbers), reverse=True)
    if len(ordered_seasons) != len(available_month_years):
        raise SendouAlignmentError(
            "Season counts do not match sendou month/year buckets: "
            f"{len(ordered_seasons)} vs {len(available_month_years)}"
        )

    return [
        SeasonMonthYear(
            season_number=season_number,
            month=int(month_year["month"]),
            year=int(month_year["year"]),
        )
        for season_number, month_year in zip(
            ordered_seasons, available_month_years
        )
    ]


def season_map_to_payload(
    seasons: Sequence[SeasonMonthYear],
) -> list[dict[str, int]]:
    return [asdict(season) for season in seasons]


def build_sendou_user_url(
    *, custom_url: str | None, discord_id: str | None
) -> str | None:
    identifier = custom_url or discord_id
    if not identifier:
        return None
    return f"https://sendou.ink/u/{identifier}"


def fetch_sendou_available_month_years(
    client: httpx.Client,
) -> list[dict[str, int]]:
    route_data = _fetch_xsearch_route_data(
        client, "https://sendou.ink/xsearch.data"
    )
    available_month_years = route_data.get("availableMonthYears")
    if not isinstance(available_month_years, list):
        raise SendouAlignmentError(
            "sendou xsearch payload is missing availableMonthYears"
        )
    return available_month_years


def fetch_sendou_placements(
    client: httpx.Client,
    *,
    season: SeasonMonthYear,
    mode: str,
    region: bool,
) -> list[dict[str, Any]]:
    sendou_mode = XSCRAPER_TO_SENDOU_MODE[mode]
    sendou_region = XSCRAPER_TO_SENDOU_REGION[region]
    url = (
        "https://sendou.ink/xsearch.data"
        f"?month={season.month}&year={season.year}"
        f"&mode={sendou_mode}&region={sendou_region}"
    )
    route_data = _fetch_xsearch_route_data(client, url)
    placements = route_data.get("placements")
    if not isinstance(placements, list):
        raise SendouAlignmentError(
            f"sendou xsearch payload is missing placements for {url}"
        )
    return placements


def validate_and_join_rows(
    xscraper_rows: Sequence[dict[str, Any]],
    sendou_rows: Sequence[dict[str, Any]],
    *,
    season: SeasonMonthYear,
    mode: str,
    region: bool,
) -> list[dict[str, Any]]:
    if len(xscraper_rows) != len(sendou_rows):
        raise SendouAlignmentError(
            "Bucket length mismatch for "
            f"season={season.season_number} mode={mode} region={region}: "
            f"{len(xscraper_rows)} vs {len(sendou_rows)}"
        )

    sendou_region = XSCRAPER_TO_SENDOU_REGION[region]
    region_label = SENDOU_REGION_LABELS[sendou_region]
    joined_rows: list[dict[str, Any]] = []

    for index, (xscraper_row, sendou_row) in enumerate(
        zip(xscraper_rows, sendou_rows),
        start=1,
    ):
        _validate_rank(index, xscraper_row, sendou_row, season, mode, region)
        _validate_power(index, xscraper_row, sendou_row, season, mode, region)
        _validate_weapon(index, xscraper_row, sendou_row, season, mode, region)

        custom_url = _as_optional_str(sendou_row.get("customUrl"))
        discord_id = _as_optional_str(sendou_row.get("discordId"))
        linked = bool(custom_url or discord_id)

        joined_rows.append(
            {
                "season_number": season.season_number,
                "month": season.month,
                "year": season.year,
                "mode": mode,
                "region": region_label,
                "rank": int(xscraper_row["rank"]),
                "x_power": float(xscraper_row["x_power"]),
                "weapon_id": int(xscraper_row["weapon_id"]),
                "npln_id": str(xscraper_row["player_id"]),
                "sendou_player_id": int(sendou_row["playerId"]),
                "sendou_discord_id": discord_id,
                "sendou_custom_url": custom_url,
                "sendou_user_url": build_sendou_user_url(
                    custom_url=custom_url,
                    discord_id=discord_id,
                ),
                "linked": linked,
            }
        )

    return joined_rows


def summarize_linked_players(
    evidence_rows: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    linked_rows = [row for row in evidence_rows if row.get("linked")]

    npln_to_sendou: dict[str, set[int]] = defaultdict(set)
    sendou_to_npln: dict[int, set[str]] = defaultdict(set)
    grouped_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in linked_rows:
        npln_id = str(row["npln_id"])
        sendou_player_id = int(row["sendou_player_id"])
        npln_to_sendou[npln_id].add(sendou_player_id)
        sendou_to_npln[sendou_player_id].add(npln_id)
        grouped_rows[npln_id].append(row)

    conflicting_npln = sorted(
        npln_id
        for npln_id, sendou_ids in npln_to_sendou.items()
        if len(sendou_ids) > 1
    )
    if conflicting_npln:
        raise SendouAlignmentError(
            "NPLN IDs mapped to multiple sendou player IDs: "
            + ", ".join(conflicting_npln[:5])
        )

    conflicting_sendou = sorted(
        str(sendou_player_id)
        for sendou_player_id, npln_ids in sendou_to_npln.items()
        if len(npln_ids) > 1
    )
    if conflicting_sendou:
        raise SendouAlignmentError(
            "sendou player IDs mapped to multiple NPLN IDs: "
            + ", ".join(conflicting_sendou[:5])
        )

    summary_rows: list[dict[str, Any]] = []
    for npln_id, rows in grouped_rows.items():
        first_row = rows[0]
        summary_rows.append(
            {
                "npln_id": npln_id,
                "sendou_player_id": int(first_row["sendou_player_id"]),
                "sendou_discord_id": _first_present(rows, "sendou_discord_id"),
                "sendou_custom_url": _first_present(rows, "sendou_custom_url"),
                "sendou_user_url": _first_present(rows, "sendou_user_url"),
                "evidence_count": len(rows),
                "season_numbers": sorted(
                    {int(row["season_number"]) for row in rows},
                    reverse=True,
                ),
                "modes": sorted({str(row["mode"]) for row in rows}),
                "regions": sorted({str(row["region"]) for row in rows}),
                "best_rank": min(int(row["rank"]) for row in rows),
                "best_x_power": max(float(row["x_power"]) for row in rows),
            }
        )

    summary_rows.sort(
        key=lambda row: (
            row["sendou_custom_url"] is None,
            row["sendou_custom_url"] or "",
            row["sendou_player_id"],
        )
    )
    return summary_rows


def _fetch_xsearch_route_data(client: httpx.Client, url: str) -> dict[str, Any]:
    response = client.get(url)
    response.raise_for_status()
    decoded = decode_turbo_stream(response.content)
    route_data = decoded.get("features/top-search/routes/xsearch")
    if not isinstance(route_data, dict):
        raise SendouAlignmentError(f"sendou xsearch route not found for {url}")
    data = route_data.get("data")
    if not isinstance(data, dict):
        raise SendouAlignmentError(
            f"sendou xsearch route data not found for {url}"
        )
    return data


def _validate_rank(
    index: int,
    xscraper_row: dict[str, Any],
    sendou_row: dict[str, Any],
    season: SeasonMonthYear,
    mode: str,
    region: bool,
) -> None:
    expected = int(xscraper_row["rank"])
    actual = int(sendou_row["rank"])
    if expected != actual:
        raise SendouAlignmentError(
            "Rank mismatch at bucket position "
            f"{index} for season={season.season_number} mode={mode} "
            f"region={region}: {expected} vs {actual}"
        )


def _validate_power(
    index: int,
    xscraper_row: dict[str, Any],
    sendou_row: dict[str, Any],
    season: SeasonMonthYear,
    mode: str,
    region: bool,
) -> None:
    expected = float(xscraper_row["x_power"])
    actual = float(sendou_row["power"])
    if abs(expected - actual) > POWER_TOLERANCE:
        raise SendouAlignmentError(
            "Power mismatch at bucket position "
            f"{index} for season={season.season_number} mode={mode} "
            f"region={region}: {expected} vs {actual}"
        )


def _validate_weapon(
    index: int,
    xscraper_row: dict[str, Any],
    sendou_row: dict[str, Any],
    season: SeasonMonthYear,
    mode: str,
    region: bool,
) -> None:
    expected = int(xscraper_row["weapon_id"])
    actual = int(sendou_row["weaponSplId"])
    if expected != actual:
        raise SendouAlignmentError(
            "Weapon mismatch at bucket position "
            f"{index} for season={season.season_number} mode={mode} "
            f"region={region}: {expected} vs {actual}"
        )


def _as_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _first_present(
    rows: Sequence[dict[str, Any]], field_name: str
) -> str | None:
    for row in rows:
        value = _as_optional_str(row.get(field_name))
        if value is not None:
            return value
    return None
