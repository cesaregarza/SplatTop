import React, { forwardRef, memo, useMemo } from "react";
import {
  CRACKLE_PURPLE,
  DISPLAY_GRADE_SCALE,
  gradeChipClass,
  isXX,
  rateFor,
} from "./stableLeaderboardUtils";

const StableLeaderboardFooterComponent = ({
  pageCount,
  currentPage,
  totalPlayers,
  allRows,
  pageSize,
  onPageSizeChange,
  onGotoPage,
  onPaginate,
  jumpGrade,
  onGotoGrade,
  jumpPlayerId,
  onJumpPlayerChange,
  onJumpPlayerSubmit,
  onJumpToTop,
}, ref) => {
  const handlePageSizeChange = (event) => {
    const value = Number(event.target.value);
    if (value === pageSize) return;
    onPaginate?.();
    onPageSizeChange(value);
  };

  const handleGotoPage = (page) => {
    if (page === currentPage) return;
    if (page < 1 || page > pageCount) return;
    onPaginate?.();
    onGotoPage(page);
  };

  const visibleGrades = useMemo(() => {
    const present = new Set(allRows.map((row) => row._grade).filter((value) => value && value !== "—"));
    return DISPLAY_GRADE_SCALE.map(([, label]) => label)
      .slice()
      .reverse()
      .filter((label) => present.has(label));
  }, [allRows]);

  return (
    <section
      ref={ref}
      className="mt-8 space-y-4"
      aria-label="Leaderboard controls"
    >
      <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-6 shadow-md space-y-6">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="mt-1 text-sm text-slate-300">
              Page <span className="font-semibold text-slate-100">{currentPage}</span> of {pageCount}
              <span className="mx-2 text-slate-600">•</span>
              <span className="font-semibold text-slate-100">{totalPlayers}</span> players
            </p>
          </div>
          <div className="flex items-center gap-3">
            <label htmlFor="rows-per-page" className="text-sm text-slate-300">
              Rows per page
            </label>
            <select
              id="rows-per-page"
              className="rounded-lg bg-slate-950/80 px-3 py-2 text-sm text-slate-100 ring-1 ring-slate-700 focus:ring-2 focus:ring-fuchsia-500/60"
              value={pageSize}
              onChange={handlePageSizeChange}
            >
              {[10, 25, 50, 100].map((size) => (
                <option key={size} value={size}>
                  {size}
                </option>
              ))}
            </select>
          </div>
        </div>

        <nav className="flex flex-wrap items-center justify-center gap-2" aria-label="Pagination">
          <button
            className="rounded-full border border-slate-800 bg-slate-950/80 px-3 py-1.5 text-sm font-medium text-slate-200 transition hover:bg-slate-900 disabled:opacity-50 disabled:hover:bg-slate-950/80"
            onClick={() => handleGotoPage(currentPage - 1)}
            disabled={currentPage <= 1}
            type="button"
          >
            Prev
          </button>
          {(() => {
            const pages = new Set([1, pageCount]);
            const windowSize = 2;
            for (let p = currentPage - windowSize; p <= currentPage + windowSize; p++) {
              if (p >= 1 && p <= pageCount) pages.add(p);
            }
            const sorted = Array.from(pages).sort((a, b) => a - b);
            const items = [];
            for (let i = 0; i < sorted.length; i++) {
              const page = sorted[i];
              const previous = i > 0 ? sorted[i - 1] : null;
              if (previous && page - previous > 1) {
                items.push(
                  <span key={`gap-${previous}`} className="px-1 text-slate-500">
                    …
                  </span>
                );
              }
              const active = page === currentPage;
              items.push(
                <button
                  key={page}
                  type="button"
                  className={`rounded-full border border-slate-800 px-3 py-1.5 text-sm font-medium transition ${
                    active
                      ? "bg-slate-200 text-slate-900 shadow-sm"
                      : "bg-slate-950/80 text-slate-200 hover:bg-slate-900"
                  }`}
                  aria-current={active ? "page" : undefined}
                  onClick={() => handleGotoPage(page)}
                >
                  {page}
                </button>
              );
            }
            return items;
          })()}
          <button
            className="rounded-full border border-slate-800 bg-slate-950/80 px-3 py-1.5 text-sm font-medium text-slate-200 transition hover:bg-slate-900 disabled:opacity-50 disabled:hover:bg-slate-950/80"
            onClick={() => handleGotoPage(currentPage + 1)}
            disabled={currentPage >= pageCount}
            type="button"
          >
            Next
          </button>
        </nav>

        {visibleGrades.length > 0 && (
          <div className="space-y-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400 text-center sm:text-left">
              Jump to grade
            </p>
            <nav
              className="flex flex-wrap items-center justify-center gap-2"
              aria-label="Jump to grade"
            >
              {visibleGrades.map((label) => {
                const active = jumpGrade === label;
                const crackleClass = isXX(label) ? "crackle" : "";
                const rate = isXX(label) ? rateFor(label) : undefined;
                return (
                  <button
                    key={label}
                    type="button"
                    aria-pressed={active}
                    className={`${gradeChipClass(label, active)} ${crackleClass}`}
                    data-color={CRACKLE_PURPLE}
                    {...(rate ? { "data-rate": rate } : {})}
                    onClick={() => onGotoGrade(label)}
                  >
                    {label}
                  </button>
                );
              })}
            </nav>
          </div>
        )}

        <div className="space-y-3 sm:flex sm:items-end sm:justify-between sm:space-y-0">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              Jump to player
            </p>
            <p className="mt-1 text-sm text-slate-400">
              Enter a Sendou ID to focus their row.
            </p>
          </div>
          <form
            className="flex flex-col gap-2 sm:flex-row sm:items-center"
            onSubmit={onJumpPlayerSubmit}
          >
            <label className="sr-only" htmlFor="leaderboard-jump-player">
              Player ID
            </label>
            <input
              id="leaderboard-jump-player"
              type="text"
              inputMode="text"
              placeholder="Jump to player ID"
              value={jumpPlayerId}
              onChange={(event) => onJumpPlayerChange(event.target.value)}
              className="w-full rounded-lg bg-slate-950/80 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 ring-1 ring-slate-700 focus:ring-2 focus:ring-fuchsia-500/60 sm:w-64"
            />
            <button
              type="submit"
              className="rounded-lg px-4 py-2 text-sm font-semibold bg-fuchsia-600 text-white shadow-sm transition hover:bg-fuchsia-500 focus:outline-none focus:ring-2 focus:ring-fuchsia-400/70"
            >
              Go
            </button>
          </form>
        </div>
      </div>

      {onJumpToTop && (
        <div className="flex justify-center">
          <button
            type="button"
            onClick={onJumpToTop}
            className="inline-flex items-center gap-2 rounded-full border border-slate-800 bg-slate-900/70 px-4 py-2 text-sm font-medium text-slate-100 shadow-sm transition hover:bg-slate-900"
          >
            Back to top
          </button>
        </div>
      )}
    </section>
  );
};

StableLeaderboardFooterComponent.displayName = "StableLeaderboardFooter";

const StableLeaderboardFooter = memo(forwardRef(StableLeaderboardFooterComponent));
StableLeaderboardFooter.displayName = "StableLeaderboardFooter";

export default StableLeaderboardFooter;
