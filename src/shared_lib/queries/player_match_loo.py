"""Bound match-impact enrichment to the rows published for each player."""

from sqlalchemy import BigInteger, bindparam, text
from sqlalchemy.sql.elements import TextClause


def build_player_match_loo_query(schema: str) -> TextClause:
    """Select balanced impact rows before loading team names and rosters.

    Reserve half the slots for each signed direction, then fill with the
    strongest remaining signed impacts before considering neutral rows.
    This matches the snapshot's Python selector, including odd limits and
    missing absolute deltas; a simple absolute-delta LIMIT would not.
    """
    schema_sql = '"' + schema.replace('"', '""') + '"'
    return text(f"""
        WITH ranked_impacts AS (
            SELECT
                impacts.player_id::text AS player_id,
                impacts.match_id,
                impacts.tournament_id,
                impacts.player_rank,
                impacts.player_score,
                impacts.is_win,
                impacts.exact_score_delta,
                impacts.exact_abs_delta,
                ROW_NUMBER() OVER (
                    PARTITION BY impacts.player_id::text,
                        CASE
                            WHEN impacts.exact_score_delta > 0 THEN 1
                            WHEN impacts.exact_score_delta < 0 THEN -1
                            ELSE 0
                        END
                    ORDER BY ABS(impacts.exact_score_delta) DESC NULLS LAST,
                             impacts.exact_abs_delta DESC NULLS LAST,
                             COALESCE(impacts.match_id, -1) DESC
                ) AS side_row_num
            FROM {schema_sql}.player_match_loo_impacts impacts
            WHERE impacts.player_id::text = ANY(:player_ids)
              AND impacts.calculated_at_ms = :calculated_at_ms
              AND (
                CAST(:match_any_build_version AS BOOLEAN) IS TRUE
                OR (
                    CAST(:build_version AS TEXT) IS NULL
                    AND impacts.build_version IS NULL
                )
                OR impacts.build_version = CAST(:build_version AS TEXT)
              )
        ),
        prioritized_impacts AS (
            SELECT ranked_impacts.*,
                ROW_NUMBER() OVER (
                    PARTITION BY player_id
                    ORDER BY
                        CASE
                            WHEN exact_score_delta <> 0
                                AND side_row_num <= :max_per_player / 2 THEN 0
                            WHEN exact_score_delta <> 0 THEN 1
                            ELSE 2
                        END,
                        exact_abs_delta DESC NULLS LAST,
                        exact_score_delta DESC NULLS LAST,
                        COALESCE(match_id, -1) DESC
                ) AS selection_row_num
            FROM ranked_impacts
        ),
        selected_impacts AS (
            SELECT *
            FROM prioritized_impacts
            WHERE selection_row_num <= :max_per_player
        ),
        player_match_team AS (
            SELECT
                pat.player_id::text AS player_id,
                pat.match_id,
                pat.tournament_id,
                MAX(pat.team_id)::bigint AS player_team_id
            FROM {schema_sql}.player_appearance_teams pat
            WHERE EXISTS (
                SELECT 1
                FROM selected_impacts impacts
                WHERE impacts.player_id = pat.player_id::text
                  AND impacts.match_id = pat.match_id
                  AND impacts.tournament_id = pat.tournament_id
            )
            GROUP BY pat.player_id::text, pat.match_id, pat.tournament_id
        ),
        base_ids AS (
            SELECT
                impacts.player_id::text AS player_id,
                impacts.match_id,
                impacts.tournament_id,
                tournaments.name::text AS tournament_name,
                CASE
                    WHEN matches.last_game_finished_at_ms IS NULL THEN
                        CASE
                            WHEN tournaments.start_time_ms IS NULL THEN NULL
                            WHEN tournaments.start_time_ms < 1000000000000
                                THEN tournaments.start_time_ms * 1000
                            ELSE tournaments.start_time_ms
                        END
                    WHEN matches.last_game_finished_at_ms < 1000000000000
                        THEN matches.last_game_finished_at_ms * 1000
                    ELSE matches.last_game_finished_at_ms
                END::bigint AS event_ms,
                impacts.player_rank,
                impacts.player_score,
                impacts.is_win,
                impacts.exact_score_delta,
                impacts.exact_abs_delta,
                COALESCE(
                    player_match_team.player_team_id,
                    CASE
                        WHEN impacts.is_win IS TRUE THEN matches.winner_team_id
                        WHEN impacts.is_win IS FALSE THEN matches.loser_team_id
                        ELSE NULL
                    END
                )::bigint AS player_team_id,
                matches.team1_id,
                matches.team1_score,
                matches.team2_id,
                matches.team2_score
            FROM selected_impacts impacts
            LEFT JOIN {schema_sql}.tournaments tournaments
              ON tournaments.tournament_id = impacts.tournament_id
            LEFT JOIN {schema_sql}.matches matches
              ON matches.match_id = impacts.match_id
             AND matches.tournament_id = impacts.tournament_id
            LEFT JOIN player_match_team
              ON player_match_team.player_id = impacts.player_id::text
             AND player_match_team.match_id = impacts.match_id
             AND player_match_team.tournament_id = impacts.tournament_id
        ),
        base AS (
            SELECT
                base_ids.player_id,
                base_ids.match_id,
                base_ids.tournament_id,
                base_ids.tournament_name,
                base_ids.event_ms,
                base_ids.player_rank,
                base_ids.player_score,
                base_ids.is_win,
                base_ids.exact_score_delta,
                base_ids.exact_abs_delta,
                base_ids.player_team_id,
                CASE
                    WHEN base_ids.player_team_id = base_ids.team1_id
                        THEN base_ids.team2_id
                    WHEN base_ids.player_team_id = base_ids.team2_id
                        THEN base_ids.team1_id
                    ELSE NULL
                END::bigint AS opponent_team_id,
                CASE
                    WHEN base_ids.player_team_id = base_ids.team1_id
                        THEN base_ids.team1_score
                    WHEN base_ids.player_team_id = base_ids.team2_id
                        THEN base_ids.team2_score
                    ELSE NULL
                END::int AS player_team_score,
                CASE
                    WHEN base_ids.player_team_id = base_ids.team1_id
                        THEN base_ids.team2_score
                    WHEN base_ids.player_team_id = base_ids.team2_id
                        THEN base_ids.team1_score
                    ELSE NULL
                END::int AS opponent_team_score
            FROM base_ids
        ),
        roster_keys AS (
            SELECT DISTINCT
                base.tournament_id,
                base.match_id,
                base.player_team_id AS team_id
            FROM base
            WHERE base.player_team_id IS NOT NULL
            UNION
            SELECT DISTINCT
                base.tournament_id,
                base.match_id,
                base.opponent_team_id AS team_id
            FROM base
            WHERE base.opponent_team_id IS NOT NULL
        ),
        team_rosters AS (
            SELECT
                roster_keys.tournament_id,
                roster_keys.match_id,
                roster_keys.team_id,
                COALESCE(
                    ARRAY_AGG(
                        DISTINCT COALESCE(
                            NULLIF(BTRIM(players.display_name::text), ''),
                            pat.player_id::text
                        )
                        ORDER BY COALESCE(
                            NULLIF(BTRIM(players.display_name::text), ''),
                            pat.player_id::text
                        )
                    ) FILTER (WHERE pat.player_id IS NOT NULL),
                    ARRAY[]::text[]
                ) AS player_names
            FROM roster_keys
            LEFT JOIN {schema_sql}.player_appearance_teams pat
              ON pat.tournament_id = roster_keys.tournament_id
             AND pat.match_id = roster_keys.match_id
             AND pat.team_id = roster_keys.team_id
            LEFT JOIN {schema_sql}.players players
              ON players.player_id = pat.player_id
            GROUP BY
                roster_keys.tournament_id,
                roster_keys.match_id,
                roster_keys.team_id
        ),
        enriched AS (
            SELECT
                base.*,
                player_team.name::text AS player_team_name,
                opponent_team.name::text AS opponent_team_name,
                player_roster.player_names AS player_team_players,
                opponent_roster.player_names AS opponent_team_players
            FROM base
            LEFT JOIN {schema_sql}.tournament_teams player_team
              ON player_team.tournament_id = base.tournament_id
             AND player_team.team_id = base.player_team_id
            LEFT JOIN {schema_sql}.tournament_teams opponent_team
              ON opponent_team.tournament_id = base.tournament_id
             AND opponent_team.team_id = base.opponent_team_id
            LEFT JOIN team_rosters player_roster
              ON player_roster.tournament_id = base.tournament_id
             AND player_roster.match_id = base.match_id
             AND player_roster.team_id = base.player_team_id
            LEFT JOIN team_rosters opponent_roster
              ON opponent_roster.tournament_id = base.tournament_id
             AND opponent_roster.match_id = base.match_id
             AND opponent_roster.team_id = base.opponent_team_id
        )
        SELECT
            player_id,
            match_id,
            tournament_id,
            tournament_name,
            event_ms,
            player_rank,
            player_score,
            is_win,
            exact_score_delta,
            exact_abs_delta,
            player_team_id,
            player_team_name,
            opponent_team_id,
            opponent_team_name,
            player_team_score,
            opponent_team_score,
            player_team_players,
            opponent_team_players
        FROM enriched
        ORDER BY
            player_id,
            exact_abs_delta DESC NULLS LAST,
            exact_score_delta DESC NULLS LAST,
            match_id DESC NULLS LAST
        """).bindparams(bindparam("max_per_player", type_=BigInteger))
