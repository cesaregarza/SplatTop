export const id = "best";
export const title_key = "column_best_title";
export const isVisible = true;
export const headerClasses =
  "w-24 px-3 py-2.5 text-center text-[0.68rem] font-semibold uppercase tracking-[0.16em] text-gray-300";
export const cellClasses =
  "w-24 px-3 py-2.5 text-center align-middle text-sm font-semibold text-gray-100";

export const render = (player, t) => {
  if (player.diamond_x_count > 0) {
    return t("best.all_mode_top10");
  }

  if (player.gold_x_count > 0) {
    return t("best.top10");
  }

  if (player.silver_x_count > 0) {
    return t("best.top500");
  }

  return "—";
};
