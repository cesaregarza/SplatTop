import React, { memo } from "react";

const StableLeaderboardHeader = () => (
  <header className="mb-4">
    <h2 className="text-2xl font-semibold text-slate-100">Competitive rankings</h2>
    <p className="mt-1 text-sm text-slate-400">
      Auto refresh at 00:15 UTC. Players stay listed so long as they log a ranked event at least every 120 days.
    </p>
  </header>
);

StableLeaderboardHeader.displayName = "StableLeaderboardHeader";

export default memo(StableLeaderboardHeader);
