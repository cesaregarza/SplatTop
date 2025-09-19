import React, { useMemo } from "react";

const numberFormatter = new Intl.NumberFormat(undefined, {
  maximumFractionDigits: 2,
});

const formatScore = (value) => {
  if (value === null || value === undefined) {
    return "—";
  }
  return numberFormatter.format(value);
};

const formatDate = (ms) => {
  if (!ms) return "—";
  const date = new Date(ms);
  if (Number.isNaN(date.getTime())) {
    return "—";
  }
  return date.toLocaleDateString();
};

const StableLeaderboardView = ({ rows, loading, error }) => {
  const content = useMemo(() => {
    if (loading) {
      return <p className="text-slate-400">Loading stable standings…</p>;
    }
    if (error) {
      return (
        <p className="text-rose-300">
          Unable to load the stable leaderboard right now: {error}
        </p>
      );
    }
    if (!rows || rows.length === 0) {
      return (
        <p className="text-slate-400">
          No players are available for this snapshot yet. Check back soon!
        </p>
      );
    }

    return (
      <div className="overflow-x-auto rounded-lg border border-slate-800 shadow-lg shadow-fuchsia-900/20">
        <table className="min-w-full divide-y divide-slate-800">
          <thead className="bg-slate-900/60 text-left text-xs font-semibold uppercase tracking-wider text-slate-400">
            <tr>
              <th className="px-4 py-3">Rank</th>
              <th className="px-4 py-3">Player</th>
              <th className="px-4 py-3">Display Score</th>
              <th className="px-4 py-3">Tournaments</th>
              <th className="px-4 py-3">Last Active</th>
              <th className="px-4 py-3">Last Tournament</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800 text-sm">
            {rows.map((row) => (
              <tr key={row.player_id} className="hover:bg-slate-900/70">
                <td className="px-4 py-3 font-semibold text-fuchsia-200">
                  {row.stable_rank ?? "—"}
                </td>
                <td className="px-4 py-3">
                  <div className="flex flex-col">
                    <span className="font-medium text-slate-100">
                      {row.display_name}
                    </span>
                    <span className="text-xs text-slate-500">
                      {row.player_id}
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3 text-slate-100">
                  {formatScore(row.display_score)}
                </td>
                <td className="px-4 py-3 text-slate-200">
                  {row.tournament_count ?? "—"}
                </td>
                <td className="px-4 py-3 text-slate-300">
                  {formatDate(row.last_active_ms)}
                </td>
                <td className="px-4 py-3 text-slate-300">
                  {formatDate(row.last_tournament_ms)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }, [rows, loading, error]);

  return (
    <section>
      <header className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-slate-100">
            Stable leaderboard
          </h2>
          <p className="mt-1 text-sm text-slate-400">
            Rankings only change when a player records a new tournament. No
            mid-day volatility.
          </p>
        </div>
      </header>
      {content}
    </section>
  );
};

export default StableLeaderboardView;
