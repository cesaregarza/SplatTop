#!/usr/bin/env python3
"""Query linked sendou accounts that crossed a regional X Power threshold."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
from pathlib import Path

import psycopg2

REGION_BOOL_BY_LABEL = {
    "Tentatek": False,
    "Takoroka": True,
}


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
        "--mapping",
        default="/tmp/sendou_linked_players.json",
        help="Path to the sendou-linked player mapping JSON.",
    )
    parser.add_argument(
        "--region",
        choices=sorted(REGION_BOOL_BY_LABEL),
        required=True,
        help="Which division to query.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        required=True,
        help="Minimum peak X Power to keep.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="JSON or CSV output path.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=10,
        help="Number of linked IDs per indexed query chunk.",
    )
    parser.add_argument(
        "--shard-index",
        type=int,
        default=0,
        help="Zero-based shard index.",
    )
    parser.add_argument(
        "--shard-count",
        type=int,
        default=1,
        help="Total number of shards.",
    )
    return parser.parse_args()


def load_mapping(path_str: str) -> list[dict]:
    payload = json.loads(Path(path_str).read_text())
    return payload["players"]


def shard_rows(
    rows: list[dict], shard_index: int, shard_count: int
) -> list[dict]:
    if shard_count <= 0:
        raise ValueError("shard_count must be positive")
    if shard_index < 0 or shard_index >= shard_count:
        raise ValueError("shard_index must be within shard_count")
    return rows[shard_index::shard_count]


def query_accounts(
    database_url: str,
    mapping_rows: list[dict],
    *,
    region: str,
    threshold: float,
    chunk_size: int,
) -> list[dict]:
    region_bool = REGION_BOOL_BY_LABEL[region]
    sendou_by_npln = {row["npln_id"]: row for row in mapping_rows}
    linked_ids = [row["npln_id"] for row in mapping_rows]

    query = """
WITH player_peaks AS (
    SELECT
        p.player_id,
        p.season_number,
        p.mode,
        MAX(p.x_power) AS peak_x_power
    FROM xscraper.players p
    WHERE p.updated
      AND p.region = %s
      AND p.player_id = ANY(%s)
    GROUP BY p.player_id, p.season_number, p.mode
    HAVING MAX(p.x_power) >= %s
),
best_peak AS (
    SELECT DISTINCT ON (player_id)
        player_id,
        season_number,
        mode,
        peak_x_power
    FROM player_peaks
    ORDER BY player_id, peak_x_power DESC, season_number DESC, mode ASC
)
SELECT
    b.player_id,
    peak_row.splashtag,
    peak_row.name,
    peak_row.name_id,
    b.mode AS peak_mode,
    b.season_number AS peak_season_number,
    b.peak_x_power,
    peak_row.rank AS peak_rank,
    peak_row.timestamp AS peak_timestamp,
    ARRAY_AGG(DISTINCT pp.mode ORDER BY pp.mode) AS qualifying_modes,
    ARRAY_AGG(DISTINCT pp.season_number ORDER BY pp.season_number DESC) AS qualifying_seasons
FROM best_peak b
JOIN player_peaks pp
    ON pp.player_id = b.player_id
JOIN LATERAL (
    SELECT splashtag, name, name_id, rank, timestamp
    FROM xscraper.players p
    WHERE p.updated
      AND p.region = %s
      AND p.player_id = b.player_id
      AND p.season_number = b.season_number
      AND p.mode = b.mode
      AND p.x_power = b.peak_x_power
    ORDER BY p.timestamp ASC
    LIMIT 1
) AS peak_row ON TRUE
GROUP BY
    b.player_id,
    peak_row.splashtag,
    peak_row.name,
    peak_row.name_id,
    b.mode,
    b.season_number,
    b.peak_x_power,
    peak_row.rank,
    peak_row.timestamp
ORDER BY b.peak_x_power DESC, b.player_id ASC
"""

    records: list[dict] = []
    with psycopg2.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SET enable_seqscan = off")
            for start in range(0, len(linked_ids), chunk_size):
                chunk = linked_ids[start : start + chunk_size]
                cur.execute(
                    query,
                    (region_bool, chunk, threshold, region_bool),
                )
                for (
                    player_id,
                    splashtag,
                    name,
                    name_id,
                    peak_mode,
                    peak_season_number,
                    peak_x_power,
                    peak_rank,
                    peak_timestamp,
                    qualifying_modes,
                    qualifying_seasons,
                ) in cur.fetchall():
                    linked = sendou_by_npln[player_id]
                    records.append(
                        {
                            "player_id": player_id,
                            "splashtag": splashtag,
                            "name": name,
                            "name_id": name_id,
                            "peak_mode": peak_mode,
                            "peak_season_number": int(peak_season_number),
                            "peak_x_power": float(peak_x_power),
                            "peak_rank": int(peak_rank),
                            "peak_timestamp": peak_timestamp.isoformat(),
                            "qualifying_modes": list(qualifying_modes),
                            "qualifying_seasons": list(qualifying_seasons),
                            "sendou_player_id": linked["sendou_player_id"],
                            "sendou_custom_url": linked["sendou_custom_url"],
                            "sendou_discord_id": linked["sendou_discord_id"],
                            "sendou_user_url": linked["sendou_user_url"],
                        }
                    )
                print(
                    f"chunk {start // chunk_size + 1}/"
                    f"{math.ceil(len(linked_ids) / chunk_size)}",
                    flush=True,
                )

    records.sort(key=lambda row: (-row["peak_x_power"], row["player_id"]))
    return records


def write_output(path_str: str, records: list[dict]) -> None:
    path = Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.suffix.lower() == ".json":
        payload = {
            "stats": {
                "account_count": len(records),
            },
            "accounts": records,
        }
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return

    if path.suffix.lower() != ".csv":
        raise ValueError(f"Unsupported output format: {path}")

    fieldnames = [
        "player_id",
        "splashtag",
        "name",
        "name_id",
        "peak_mode",
        "peak_season_number",
        "peak_x_power",
        "peak_rank",
        "peak_timestamp",
        "qualifying_modes",
        "qualifying_seasons",
        "sendou_player_id",
        "sendou_custom_url",
        "sendou_discord_id",
        "sendou_user_url",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            row = record.copy()
            row["qualifying_modes"] = ";".join(row["qualifying_modes"])
            row["qualifying_seasons"] = ";".join(
                str(value) for value in row["qualifying_seasons"]
            )
            writer.writerow(row)


def main() -> int:
    args = parse_args()
    if not args.database_url:
        raise SystemExit(
            "database URL is required via --database-url or DATABASE_URL"
        )

    mapping_rows = load_mapping(args.mapping)
    shard_mapping_rows = shard_rows(
        mapping_rows, args.shard_index, args.shard_count
    )
    records = query_accounts(
        args.database_url,
        shard_mapping_rows,
        region=args.region,
        threshold=args.threshold,
        chunk_size=args.chunk_size,
    )
    write_output(args.output, records)
    print(
        f"wrote {len(records)} accounts to {args.output} "
        f"(shard {args.shard_index + 1}/{args.shard_count})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
