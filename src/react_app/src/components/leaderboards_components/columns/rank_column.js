export const id = "rank";
export const title_key = "column_rank_title";
export const isVisible = true;
export const headerClasses =
  "w-14 px-3 py-2.5 text-center text-xs font-semibold uppercase tracking-[0.18em] text-gray-400";
export const cellClasses =
  "w-14 px-3 py-3 text-center text-sm font-semibold text-white";
export const render = (player, t) => player.rank;
