import { getSeasonName } from "../../player_components/xchart_helper_functions";

export const id = "season_number";
export const title_key = "column_season_number_title";
export const isVisible = true;
export const headerClasses =
  "w-32 px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-[0.18em] text-gray-400";
export const cellClasses = "w-32 px-4 py-3 text-left text-sm text-gray-300";
export const render = (player, t) => (
  <span className="block truncate">{getSeasonName(player.season_number, t)}</span>
);
