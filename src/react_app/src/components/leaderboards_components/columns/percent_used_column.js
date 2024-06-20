export const id = "percent_used";
export const title_key = "column_percent_used_title";
export const isVisible = true;
export const headerClasses = null;
export const cellClasses = null;
export const render = (player, t) =>
  `${(player.percent_used * 100).toFixed(1)}%`;
