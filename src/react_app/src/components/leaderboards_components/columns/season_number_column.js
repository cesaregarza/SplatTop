import { getSeasonName } from "../../player_components/xchart_helper_functions";

export const id = "season_number";
export const title_key = "column_season_number_title";
export const isVisible = true;
export const headerClasses = null;
export const cellClasses = null;
export const render = (player, t) => getSeasonName(player.season_number, t);
