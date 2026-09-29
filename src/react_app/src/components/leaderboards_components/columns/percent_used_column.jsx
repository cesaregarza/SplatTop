import React from "react";

export const id = "percent_games_played";
export const title_key = "column_percent_games_played_title";
export const isVisible = true;
export const headerClasses =
  "w-28 px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-[0.18em] text-gray-400";
export const cellClasses =
  "w-28 px-4 py-3 text-right text-sm font-medium text-gray-200";
export const render = (player, t) => (
  <span className="tabular-nums">
    {(player.percent_games_played * 100).toFixed(1)}%
  </span>
);
