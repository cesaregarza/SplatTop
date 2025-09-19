import React, { useMemo } from "react";

const formatDaysLeft = (value) => {
  if (value === null || value === undefined) return "—";
  if (value < 0) return "Expired";
  const rounded = Math.max(value, 0).toFixed(1);
  return `${rounded} days`;
};

const DangerWatch = ({ rows, loading, error }) => {
  const content = useMemo(() => {
    if (loading) {
      return <p className="text-slate-400">Loading danger window…</p>;
    }
    if (error) {
      return (
        <p className="text-rose-300">
          Unable to load danger data right now: {error}
        </p>
      );
    }
    if (!rows || rows.length === 0) {
      return (
        <p className="text-slate-400">Everyone is safely within their window.</p>
      );
    }

    return (
      <div className="space-y-3">
        {rows.map((row) => (
          <div
            key={row.player_id}
            className="rounded-lg border border-slate-800 bg-slate-900/80 p-4 shadow-md shadow-fuchsia-900/10"
          >
            <div className="flex items-center justify-between gap-2">
              <div>
                <p className="text-sm uppercase tracking-wide text-slate-500">
                  Rank {row.rank ?? "?"}
                </p>
                <h3 className="text-lg font-semibold text-slate-100">
                  {row.display_name}
                </h3>
              </div>
              <div className="text-right">
                <p className="text-xs text-slate-400">Display score</p>
                <p className="text-lg font-semibold text-fuchsia-200">
                  {row.display_score?.toFixed(2)}
                </p>
              </div>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-3 text-sm text-slate-300">
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">
                  Tournament count
                </p>
                <p>{row.window_tournament_count ?? "—"}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">
                  Days left in window
                </p>
                <p className="font-medium text-amber-200">
                  {formatDaysLeft(row.days_left)}
                </p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">
                  Oldest tournament
                </p>
                <p>
                  {row.oldest_in_window_ms
                    ? new Date(row.oldest_in_window_ms).toLocaleDateString()
                    : "—"}
                </p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">
                  Next expiry
                </p>
                <p>
                  {row.next_expiry_ms
                    ? new Date(row.next_expiry_ms).toLocaleDateString()
                    : "—"}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }, [rows, loading, error]);

  return (
    <section>
      <header className="mb-4">
        <h2 className="text-xl font-semibold text-slate-100">Danger watch</h2>
        <p className="mt-1 text-sm text-slate-400">
          Track who risks expiry next so you can plan tournament entries before
          their score drops out of the window.
        </p>
      </header>
      {content}
    </section>
  );
};

export default DangerWatch;
