import React, { memo } from "react";

const StableLeaderboardHeader = () => (
  <header className="mb-4">
    <h2 className="text-2xl font-semibold text-slate-100">Competitive rankings</h2>
    <p className="mt-1 text-sm text-slate-400">
      Archived rankings from the last published update. No new tournament results will be added.
    </p>
  </header>
);

StableLeaderboardHeader.displayName = "StableLeaderboardHeader";

export default memo(StableLeaderboardHeader);
