import React from "react";

const formatTimestamp = (ts) => {
  if (!ts) return "—";
  const date = new Date(ts);
  if (Number.isNaN(date.getTime())) {
    return "—";
  }
  return date.toLocaleString();
};

const CompetitionLayout = ({
  children,
  generatedAtMs,
  stale,
  loading,
  onRefresh,
}) => {
  const lastUpdated = formatTimestamp(generatedAtMs);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="bg-[#ab5ab7] text-white py-12">
        <div className="max-w-6xl mx-auto px-6">
          <h1 className="text-3xl sm:text-5xl font-semibold tracking-tight">
            Splat Top Competition Ripple Leaderboard
          </h1>
          <p className="mt-4 max-w-3xl text-lg text-fuchsia-100">
            A stable snapshot of the Ripple rankings, refreshed once daily at
            12:15 UTC, so your tournament standings stay predictable for the
            entire competition run.
          </p>
        </div>
      </header>

      <section className="bg-slate-900 border-b border-slate-800">
        <div className="max-w-6xl mx-auto px-6 py-5 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm uppercase tracking-wide text-slate-400">
              Last updated
            </p>
            <div className="mt-1 flex items-center gap-3">
              <span className="text-lg font-medium text-slate-100">
                {lastUpdated}
              </span>
              {stale && (
                <span className="inline-flex items-center rounded-full bg-amber-500/20 px-3 py-1 text-xs font-medium text-amber-300">
                  Stale — queued for refresh
                </span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-3">
            {loading && (
              <span className="text-sm text-slate-400">Refreshing…</span>
            )}
            <button
              type="button"
              className="rounded-md bg-[#ab5ab7] px-4 py-2 text-sm font-medium text-white shadow hover:bg-fuchsia-500 transition"
              onClick={onRefresh}
              disabled={loading}
            >
              Refresh snapshot
            </button>
          </div>
        </div>
      </section>

      <main className="max-w-6xl mx-auto px-6 py-10">
        {children}
      </main>
    </div>
  );
};

export default CompetitionLayout;
