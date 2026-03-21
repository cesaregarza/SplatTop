const DELTA_WINDOW_MS = 24 * 60 * 60 * 1000;

const resolveDisplayDelta = (entry) => {
  if (!entry) return null;
  if (typeof entry.display_score_delta === "number") {
    return entry.display_score_delta;
  }
  if (typeof entry.score_delta === "number") {
    return entry.score_delta * 25;
  }
  return null;
};

export const mergeCompetitionSnapshotRows = ({ stable, danger }) => {
  const stableRows = Array.isArray(stable?.data) ? stable.data : [];
  const dangerRows = Array.isArray(danger?.data) ? danger.data : [];
  const deltas = stable?.deltas ?? null;
  const generatedAtMs =
    stable?.generated_at_ms ?? danger?.generated_at_ms ?? null;
  const dangerById = new Map(dangerRows.map((row) => [row.player_id, row]));
  const deltaPlayers = deltas?.players ?? {};
  const hasBaseline = deltas?.baseline_generated_at_ms != null;
  const newcomerIds = new Set(deltas?.newcomers ?? []);

  return stableRows.map((row) => {
    const playerId = row.player_id;
    const dangerRow = dangerById.get(playerId);
    const deltaEntry = playerId != null ? deltaPlayers[playerId] : undefined;
    const rankDelta =
      hasBaseline &&
      deltaEntry &&
      typeof deltaEntry.rank_delta === "number"
        ? deltaEntry.rank_delta
        : null;
    let displayScoreDelta = hasBaseline ? resolveDisplayDelta(deltaEntry) : null;
    const isNewEntry =
      hasBaseline && Boolean(deltaEntry?.is_new || newcomerIds.has(playerId));
    const lastTournamentMs = row.last_tournament_ms ?? null;

    if (
      displayScoreDelta != null &&
      generatedAtMs != null &&
      lastTournamentMs != null &&
      generatedAtMs - lastTournamentMs > DELTA_WINDOW_MS
    ) {
      displayScoreDelta = null;
    }

    return {
      ...row,
      danger_days_left: dangerRow?.days_left ?? null,
      danger_next_expiry_ms: dangerRow?.next_expiry_ms ?? null,
      danger_oldest_in_window_ms: dangerRow?.oldest_in_window_ms ?? null,
      window_tournament_count:
        dangerRow?.window_tournament_count ??
        row.window_tournament_count ??
        null,
      rank_delta: rankDelta,
      display_score_delta: displayScoreDelta,
      delta_is_new: isNewEntry,
      delta_has_baseline: hasBaseline,
      delta_previous_rank:
        deltaEntry && typeof deltaEntry.previous_rank === "number"
          ? deltaEntry.previous_rank
          : null,
      delta_previous_display_score:
        deltaEntry && typeof deltaEntry.previous_display_score === "number"
          ? deltaEntry.previous_display_score
          : null,
    };
  });
};
