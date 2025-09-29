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
  jumpGrade,
  onGotoGrade,
  jumpPlayerId,
  onJumpPlayerChange,
  onJumpPlayerSubmit,
}, ref) => {
  const handlePageSizeChange = (event) => {
    const value = Number(event.target.value);
    onPageSizeChange(value);
  };

  const visibleGrades = useMemo(() => {
    const present = new Set(allRows.map((row) => row._grade).filter((value) => value && value !== "—"));
    return DISPLAY_GRADE_SCALE.map(([, label]) => label)
      .slice()
      .reverse()
      .filter((label) => present.has(label));
  }, [allRows]);

  return (
    <div ref={ref} className="mt-4 space-y-3">
      <div className="flex flex-col gap-2 text-sm text-slate-400 sm:flex-row sm:flex-wrap sm:items-center">
        <span>Rows per page</span>
        <select
          className="rounded-md bg-slate-900/80 px-2 py-1 text-slate-100 ring-1 ring-white/10"
          value={pageSize}
          onChange={handlePageSizeChange}
        >
          {[10, 25, 50, 100].map((size) => (
            <option key={size} value={size}>
              {size}
            </option>
          ))}
        </select>
        <span className="sm:ml-3">
          Page {currentPage} of {pageCount} • {totalPlayers} players
        </span>
      </div>

      <nav className="flex flex-wrap items-center justify-center gap-1">
        <button
          className="rounded-md px-3 py-1.5 text-sm bg-slate-900/70 ring-1 ring-white/10 text-slate-200 disabled:opacity-50"
          onClick={() => onGotoPage(currentPage - 1)}
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
                className={`rounded-md px-3 py-1.5 text-sm ring-1 ring-white/10 ${
                  active ? "bg-slate-200 text-slate-900" : "bg-slate-900/70 text-slate-200"
                }`}
                onClick={() => onGotoPage(page)}
              >
                {page}
              </button>
            );
          }
          return items;
        })()}
        <button
          className="rounded-md px-3 py-1.5 text-sm bg-slate-900/70 ring-1 ring-white/10 text-slate-200 disabled:opacity-50"
          onClick={() => onGotoPage(currentPage + 1)}
          disabled={currentPage >= pageCount}
          type="button"
        >
          Next
        </button>
      </nav>

      {visibleGrades.length > 0 && (
        <nav className="flex flex-wrap items-center justify-center gap-2">
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
      )}

      <form
        className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-center"
        onSubmit={onJumpPlayerSubmit}
      >
        <input
          type="text"
          inputMode="text"
          placeholder="Jump to player ID"
          value={jumpPlayerId}
          onChange={(event) => onJumpPlayerChange(event.target.value)}
          className="w-full rounded-md bg-slate-900/80 px-2 py-1 text-slate-100 placeholder:text-slate-500 ring-1 ring-white/10 sm:w-56"
        />
        <button
          type="submit"
          className="rounded-md px-3 py-1.5 text-sm bg-fuchsia-600 text-white ring-1 ring-white/10 hover:bg-fuchsia-500"
        >
          Go
        </button>
      </form>
    </div>
  );
};

StableLeaderboardFooterComponent.displayName = "StableLeaderboardFooter";

const StableLeaderboardFooter = memo(forwardRef(StableLeaderboardFooterComponent));
StableLeaderboardFooter.displayName = "StableLeaderboardFooter";

export default StableLeaderboardFooter;
