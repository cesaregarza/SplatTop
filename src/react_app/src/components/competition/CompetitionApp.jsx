import React, { useMemo } from "react";
import CompetitionLayout from "./CompetitionLayout";
import StableLeaderboardView from "./StableLeaderboardView";
import useCompetitionSnapshot from "../../hooks/useCompetitionSnapshot";

const CompetitionApp = () => {
  const { loading, error, disabled, stable, danger, refresh } =
    useCompetitionSnapshot();

  const mergedRows = useMemo(() => {
    const stableRows = Array.isArray(stable?.data) ? stable.data : [];
    const dangerRows = Array.isArray(danger?.data) ? danger.data : [];
    const dangerById = new Map(dangerRows.map((row) => [row.player_id, row]));
    return stableRows.map((row) => {
      const dangerRow = dangerById.get(row.player_id);
      return {
        ...row,
        danger_days_left: dangerRow?.days_left ?? null,
        danger_next_expiry_ms: dangerRow?.next_expiry_ms ?? null,
        danger_oldest_in_window_ms: dangerRow?.oldest_in_window_ms ?? null,
        // Prefer danger's live window count; otherwise use stable payload's
        // window count when available. Do NOT fall back to total tournaments,
        // as that incorrectly implies all tournaments occurred in the window.
        window_tournament_count:
          dangerRow?.window_tournament_count ?? row.window_tournament_count ?? null,
      };
    });
  }, [stable?.data, danger?.data]);

  if (disabled) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center px-6">
        <div className="max-w-lg text-center">
          <h1 className="text-3xl font-semibold">Competition leaderboard disabled</h1>
          <p className="mt-4 text-slate-400">
            The public competition leaderboard is currently turned off. Check
            back later or contact an administrator if you believe this is a
            mistake.
          </p>
        </div>
      </div>
    );
  }

  const stale = Boolean(stable?.stale || danger?.stale);
  const generatedAtMs = stable?.generated_at_ms ?? danger?.generated_at_ms;

  const windowDays = stable?.query_params?.tournament_window_days ?? null;

  return (
    <CompetitionLayout
      generatedAtMs={generatedAtMs}
      stale={stale}
      loading={loading}
      onRefresh={refresh}
      top500Href="/top500"
    >
      {error && (
        <div className="mb-6 rounded-md border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
          {error}
        </div>
      )}

      <div className="grid gap-8">
        <StableLeaderboardView
          rows={mergedRows}
          loading={loading}
          error={error}
          windowDays={windowDays}
        />
      </div>
    </CompetitionLayout>
  );
};

export default CompetitionApp;
