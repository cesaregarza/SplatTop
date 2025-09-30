import React, { memo } from "react";
import { Link } from "react-router-dom";

const ROW_OPTIONS = [25, 50, 100];

const StableLeaderboardControls = ({
  query,
  onQueryChange,
  grades,
  selectedGrade,
  onSelectGrade,
  pageSize,
  onPageSizeChange,
  onRefresh,
  refreshing,
}) => {
  const hasGrades = Array.isArray(grades) && grades.length > 0;
  const rowOptions = ROW_OPTIONS.includes(pageSize)
    ? ROW_OPTIONS
    : [...ROW_OPTIONS, pageSize].sort((a, b) => a - b);

  const handleQueryChange = (event) => {
    onQueryChange(event.target.value);
  };

  const handleGradeChange = (event) => {
    const value = event.target.value;
    onSelectGrade(value);
  };

  const handlePageSizeChange = (event) => {
    const value = Number(event.target.value);
    if (!Number.isFinite(value)) return;
    onPageSizeChange(value);
  };

  return (
    <section
      className="mb-4 rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2 shadow-sm"
      aria-label="Leaderboard controls"
    >
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative flex-1 min-w-[220px]">
          <label className="sr-only" htmlFor="stable-leaderboard-search">
            Search players
          </label>
          <input
            id="stable-leaderboard-search"
            type="search"
            placeholder="Search player or ID…"
            value={query}
            onChange={handleQueryChange}
            className="w-full rounded-md bg-slate-950/70 pl-9 pr-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 ring-1 ring-white/10 focus:ring-2 focus:ring-fuchsia-500/60 outline-none"
          />
          <span className="pointer-events-none absolute left-3 top-2.5 text-slate-500" aria-hidden>
            🔎
          </span>
        </div>

        {hasGrades && (
          <div>
            <label className="sr-only" htmlFor="stable-leaderboard-grade">
              Jump to grade
            </label>
            <select
              id="stable-leaderboard-grade"
              className="rounded-md bg-slate-950/80 px-3 py-2 text-sm text-slate-100 ring-1 ring-slate-700 focus:ring-2 focus:ring-fuchsia-500/60"
              value={selectedGrade}
              onChange={handleGradeChange}
            >
              <option value="">All grades</option>
              {grades.map((label) => (
                <option key={label} value={label}>
                  {label}
                </option>
              ))}
            </select>
          </div>
        )}

        <div>
          <label className="sr-only" htmlFor="stable-leaderboard-rows">
            Rows per page
          </label>
          <div className="flex items-center gap-2 rounded-md bg-slate-950/80 px-3 py-2 text-sm text-slate-200 ring-1 ring-slate-700">
            <span className="text-slate-400">Rows</span>
            <select
              id="stable-leaderboard-rows"
              value={pageSize}
              onChange={handlePageSizeChange}
              className="bg-transparent text-slate-100 focus:outline-none"
            >
              {rowOptions.map((size) => (
                <option key={size} value={size}>
                  {size}
                </option>
              ))}
            </select>
          </div>
        </div>

        <Link
          to="/faq"
          className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-700 bg-slate-950/70 text-lg text-slate-200 transition hover:bg-slate-900"
          aria-label="How rankings work"
        >
          ?
        </Link>

        {onRefresh && (
          <button
            type="button"
            onClick={onRefresh}
            className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-700 bg-slate-950/70 text-lg text-slate-200 transition hover:bg-slate-900 disabled:opacity-50"
            aria-label="Refresh snapshot"
            disabled={refreshing}
          >
            ⟳
          </button>
        )}
      </div>
    </section>
  );
};

StableLeaderboardControls.displayName = "StableLeaderboardControls";

export default memo(StableLeaderboardControls);
