export const id = "percent_games_played";
export const title_key = "column_percent_games_played_title";
export const isVisible = true;
export const headerClasses = null;
export const cellClasses = null;
export const render = (player, t) =>
  `${(player.percent_games_played * 100).toFixed(1)}%`;
