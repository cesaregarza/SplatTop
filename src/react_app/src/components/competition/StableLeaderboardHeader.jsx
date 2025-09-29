import React, { memo } from "react";

const StableLeaderboardHeader = ({ query, onQueryChange, onScrollToControls }) => (
  <header className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
    <div>
      <h2 className="text-2xl font-semibold text-slate-100">Stable leaderboard</h2>
      <p className="mt-1 text-sm text-slate-400">
        Rankings only change when a player records a new tournament. Danger status is integrated below.
      </p>
    </div>
    <div className="w-full sm:w-80">
      <label className="sr-only" htmlFor="leaderboard-search">
        Search players
      </label>
      <div className="relative">
        <input
          id="leaderboard-search"
          type="text"
          placeholder="Search player or ID…"
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          className="w-full rounded-md bg-slate-900/70 pl-9 pr-3 py-2 text-slate-100 placeholder:text-slate-500 ring-1 ring-white/10 focus:ring-2 focus:ring-fuchsia-500/60 outline-none"
        />
        <span className="absolute left-3 top-2.5 text-slate-500">🔎</span>
      </div>
    </div>
    {onScrollToControls && (
      <button
        type="button"
        onClick={onScrollToControls}
        className="inline-flex items-center gap-2 self-start rounded-md bg-slate-800/80 px-3 py-1.5 text-sm font-medium text-slate-100 ring-1 ring-white/10 hover:bg-slate-800 md:hidden"
      >
        Jump to controls
      </button>
    )}
  </header>
);

StableLeaderboardHeader.displayName = "StableLeaderboardHeader";

export default memo(StableLeaderboardHeader);
