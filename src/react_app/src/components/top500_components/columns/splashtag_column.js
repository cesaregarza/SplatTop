export const id = "splashtag";
export const title_key = "column_splashtag_title";
export const isVisible = true;
export const headerClasses =
  "w-[16rem] px-4 py-2.5 text-left text-[0.68rem] font-semibold uppercase tracking-[0.16em] text-gray-300";
export const cellClasses =
  "w-[16rem] px-4 py-2.5 text-left align-middle text-sm font-medium text-white";
export const render = (player) => (
  <span className="block truncate">{player.splashtag}</span>
);
