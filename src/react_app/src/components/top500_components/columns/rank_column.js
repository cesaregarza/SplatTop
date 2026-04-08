export const id = "rank";
export const title_key = "column_rank_title";
export const isVisible = true;
export const headerClasses =
  "w-16 px-3 py-2.5 text-center text-[0.68rem] font-semibold uppercase tracking-[0.16em] text-gray-300";
export const cellClasses =
  "w-16 px-3 py-2.5 text-center align-middle text-sm font-medium tabular-nums text-gray-100";
export const render = (player, t) => player.rank;
