import React from "react";
import { Link } from "react-router-dom";

const formatTimestamp = (ts) => {
  if (!ts) return "—";
  const date = new Date(ts);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString();
};

const CompetitionLayout = ({
  children,
  generatedAtMs,
  stale,
  loading,
  onRefresh,
  faqLinkHref,
  faqLinkLabel = "FAQ",
  top500Href = "/top500",
}) => {
  const lastUpdated = formatTimestamp(generatedAtMs);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-900/90">
        <div className="max-w-6xl mx-auto px-6 pt-6 pb-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <a
                href={top500Href}
                className="rounded-md bg-white/10 px-2.5 py-1 text-xs font-semibold tracking-wide text-white ring-1 ring-white/15 hover:bg-white/15"
                title="Open Top 500"
              >
                splat.top
              </a>
              <div className="h-4 w-px bg-white/20" />
              <span className="text-white/80 text-sm">Top 500</span>
              <span className="text-white/30">/</span>
              <span className="text-white text-sm font-medium">Competition</span>
            </div>
          </div>

          <h1 className="mt-5 text-3xl sm:text-5xl font-semibold tracking-tight">
            Competition Ripple Leaderboard
          </h1>
          <p className="mt-2 max-w-3xl text-slate-300">
            A stable snapshot of the Ripple rankings, refreshed once daily at
            12:15 UTC—snappy visuals, zero mid-day volatility.
          </p>
        </div>
      </header>

      <section className="bg-slate-900/80 border-b border-slate-800">
        <div className="max-w-6xl mx-auto px-6 py-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-400">Last updated</p>
            <div className="mt-1 flex items-center gap-3">
              <span className="text-lg font-medium">{lastUpdated}</span>
              {stale && (
                <span className="inline-flex items-center rounded-full bg-amber-500/15 px-3 py-1 text-xs font-medium text-amber-300 ring-1 ring-amber-300/20">
                  Stale — queued for refresh
                </span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-3">
            {faqLinkHref && (
              <Link
                to={faqLinkHref}
                className="rounded-md bg-white/10 px-4 py-2 text-sm font-medium text-white ring-1 ring-white/10 hover:bg-white/15 transition"
              >
                {faqLinkLabel}
              </Link>
            )}
            {onRefresh && (
              <>
                {loading && (
                  <span className="text-sm text-slate-400">Refreshing…</span>
                )}
                <button
                  type="button"
                  className="rounded-md bg-fuchsia-600 px-4 py-2 text-sm font-medium text-white ring-1 ring-white/10 hover:bg-fuchsia-500 transition disabled:opacity-60"
                  onClick={onRefresh}
                  disabled={loading}
                >
                  Refresh snapshot
                </button>
              </>
            )}
          </div>
        </div>
      </section>

      <main className="max-w-6xl mx-auto px-6 py-10">{children}</main>
    </div>
  );
};

export default CompetitionLayout;
