import React from "react";
import CompetitionLayout from "./CompetitionLayout";
import StableLeaderboardView from "./StableLeaderboardView";
import DangerWatch from "./DangerWatch";
import useCompetitionSnapshot from "../../hooks/useCompetitionSnapshot";

const CompetitionApp = () => {
  const { loading, error, disabled, stable, danger, meta, refresh } =
    useCompetitionSnapshot();

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

  return (
    <CompetitionLayout
      generatedAtMs={generatedAtMs}
      stale={stale}
      loading={loading}
      onRefresh={refresh}
    >
      {error && (
        <div className="mb-6 rounded-md border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
          {error}
        </div>
      )}

      <div className="grid gap-8 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <StableLeaderboardView
            rows={stable?.data}
            loading={loading}
            error={error}
          />
        </div>
        <div className="lg:col-span-1">
          <DangerWatch
            rows={danger?.data}
            loading={loading}
            error={error}
          />
          {meta && (
            <aside className="mt-6 rounded-lg border border-slate-800 bg-slate-900/80 p-4 text-sm text-slate-300">
              <p className="text-xs uppercase tracking-wide text-slate-500">
                Snapshot details
              </p>
              <ul className="mt-2 space-y-1">
                <li>Stable rows: {meta.stable_record_count ?? "—"}</li>
                <li>Danger rows: {meta.danger_record_count ?? "—"}</li>
                <li>Build version: {meta.build_version ?? "—"}</li>
              </ul>
            </aside>
          )}
        </div>
      </div>
    </CompetitionLayout>
  );
};

export default CompetitionApp;
