#!/usr/bin/env python3
"""Scrape sendou-linked players by aligning sendou xsearch rows to NPLN rows.

This joins public sendou xsearch leaderboard rows to
`xscraper.season_results` using the exact final-season ordering that both
sources publish: season/month-year, mode, region, rank, power, and weapon.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
from pathlib import Path
from typing import Any

import httpx
import psycopg2

from shared_lib.sendou_linked_players import (
    FETCH_TIMEOUT_SECONDS,
    XSCRAPER_TO_SENDOU_MODE,
    XSCRAPER_TO_SENDOU_REGION,
    fetch_sendou_available_month_years,
    fetch_sendou_placements,
    map_seasons_to_sendou_month_years,
    season_map_to_payload,
    summarize_linked_players,
    validate_and_join_rows,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL") or os.getenv("XSCRAPER_DATABASE_URL"),
        help=(
            "Postgres connection string for the xscraper database. "
            "Defaults to DATABASE_URL or XSCRAPER_DATABASE_URL."
        ),
    )
    parser.add_argument(
        "--output",
        default="/tmp/sendou_linked_players.json",
        help=(
            "Summary output path. .json writes the full payload; "
            ".csv writes flat summary rows."
        ),
    )
    parser.add_argument(
        "--evidence-output",
        help=(
            "Optional detailed output path for every linked season row. "
            "Supports .json or .csv."
        ),
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=FETCH_TIMEOUT_SECONDS,
        help=f"HTTP timeout in seconds (default: {FETCH_TIMEOUT_SECONDS})",
    )
    return parser.parse_args()


def fetch_xscraper_rows(
    database_url: str,
) -> tuple[list[int], dict[tuple[int, str, bool], list[dict[str, Any]]]]:
    bucketed_rows: dict[tuple[int, str, bool], list[dict[str, Any]]] = {}
    season_numbers: list[int]

    with psycopg2.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT season_number
                FROM xscraper.season_results
                ORDER BY season_number DESC
                """
            )
            season_numbers = [int(row[0]) for row in cur.fetchall()]

            cur.execute(
                """
                SELECT
                    season_number,
                    mode,
                    region,
                    rank,
                    player_id,
                    x_power,
                    weapon_id
                FROM xscraper.season_results
                ORDER BY season_number DESC, mode ASC, region ASC, rank ASC
                """
            )

            grouped: dict[tuple[int, str, bool], list[dict[str, Any]]] = {}
            for (
                season_number,
                mode,
                region,
                rank,
                player_id,
                x_power,
                weapon_id,
            ) in cur.fetchall():
                key = (int(season_number), str(mode), bool(region))
                grouped.setdefault(key, []).append(
                    {
                        "rank": int(rank),
                        "player_id": str(player_id),
                        "x_power": float(x_power),
                        "weapon_id": int(weapon_id),
                    }
                )

            bucketed_rows = grouped

    return season_numbers, bucketed_rows


def write_output(
    path_str: str, rows: list[dict[str, Any]] | dict[str, Any]
) -> None:
    path = Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.suffix.lower() == ".json":
        with path.open("w", encoding="utf-8") as handle:
            json.dump(rows, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        return

    if path.suffix.lower() != ".csv":
        raise ValueError(f"Unsupported output format: {path}")

    if not isinstance(rows, list):
        raise ValueError("CSV output requires a flat list of dictionaries")

    flattened_rows = [_flatten_csv_row(row) for row in rows]
    fieldnames = sorted({key for row in flattened_rows for key in row.keys()})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(flattened_rows)


def _flatten_csv_row(row: dict[str, Any]) -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, list):
            flattened[key] = ";".join(str(item) for item in value)
        else:
            flattened[key] = value
    return flattened


def main() -> int:
    args = parse_args()
    if not args.database_url:
        raise SystemExit(
            "database URL is required via --database-url or DATABASE_URL"
        )

    season_numbers, xscraper_rows = fetch_xscraper_rows(args.database_url)

    with httpx.Client(timeout=args.timeout) as client:
        available_month_years = fetch_sendou_available_month_years(client)
        seasons = map_seasons_to_sendou_month_years(
            season_numbers, available_month_years
        )

        evidence_rows: list[dict[str, Any]] = []
        for season in seasons:
            for mode in XSCRAPER_TO_SENDOU_MODE:
                for region in XSCRAPER_TO_SENDOU_REGION:
                    bucket_key = (season.season_number, mode, region)
                    sendou_rows = fetch_sendou_placements(
                        client,
                        season=season,
                        mode=mode,
                        region=region,
                    )
                    evidence_rows.extend(
                        validate_and_join_rows(
                            xscraper_rows[bucket_key],
                            sendou_rows,
                            season=season,
                            mode=mode,
                            region=region,
                        )
                    )

    linked_evidence_rows = [row for row in evidence_rows if row["linked"]]
    summary_rows = summarize_linked_players(evidence_rows)

    payload = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "stats": {
            "season_count": len(seasons),
            "bucket_count": len(seasons)
            * len(XSCRAPER_TO_SENDOU_MODE)
            * len(XSCRAPER_TO_SENDOU_REGION),
            "row_count": len(evidence_rows),
            "linked_row_count": len(linked_evidence_rows),
            "linked_player_count": len(summary_rows),
        },
        "season_map": season_map_to_payload(seasons),
        "players": summary_rows,
    }

    write_output(
        args.output, payload if args.output.endswith(".json") else summary_rows
    )
    if args.evidence_output:
        evidence_payload: list[dict[str, Any]] | dict[str, Any]
        if args.evidence_output.endswith(".json"):
            evidence_payload = {
                "generated_at": payload["generated_at"],
                "row_count": len(linked_evidence_rows),
                "rows": linked_evidence_rows,
            }
        else:
            evidence_payload = linked_evidence_rows
        write_output(args.evidence_output, evidence_payload)

    print(
        "Wrote "
        f"{len(summary_rows)} linked players from {len(linked_evidence_rows)} "
        f"linked leaderboard rows to {args.output}"
    )
    if args.evidence_output:
        print(f"Wrote detailed evidence rows to {args.evidence_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
