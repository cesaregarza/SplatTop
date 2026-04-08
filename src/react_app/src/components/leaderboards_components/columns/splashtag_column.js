export const id = "splashtag";
export const title_key = "column_splashtag_title";
export const isVisible = true;
export const headerClasses =
  "min-w-[12rem] px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-[0.18em] text-gray-400";
export const cellClasses =
  "min-w-[12rem] px-4 py-3 text-left text-sm font-medium text-white";
export const render = (player, t) => (
  <span className="block truncate">{player.alias}</span>
);
