import React from "react";

export const id = "splashtag";
export const title_key = "column_splashtag_title";
export const isVisible = true;
export const headerClasses =
  "grow px-4 py-3 text-left text-[0.68rem] font-semibold uppercase tracking-[0.16em] text-gray-300";
export const cellClasses = "grow px-4 py-3 text-left align-middle";

const getOriginRegion = (player) =>
  player.prev_season_region ? "Takoroka" : "Tentatek";

const buildSummaryItems = (player, t, tableContext = {}) => {
  const items = [];
  const originRegion = getOriginRegion(player);

  if (player.diamond_x_count > 0) {
    items.push({
      key: "diamond",
      label: t("highlights.diamond"),
      value: player.diamond_x_count,
    });
  }

  if (player.gold_x_count > 0) {
    items.push({
      key: "top10",
      label: t("highlights.top10"),
      value: player.gold_x_count,
    });
  }

  if (player.silver_x_count > 0) {
    items.push({
      key: "top500",
      label: t("highlights.top500"),
      value: player.silver_x_count,
    });
  }

  if (
    !tableContext.selectedRegion ||
    tableContext.selectedRegion !== originRegion
  ) {
    items.push({
      key: "origin",
      label: t("highlights.origin"),
      textValue: originRegion,
    });
  }

  return items;
};

export const render = (player, t, tableContext = {}) => {
  const summaryItems = buildSummaryItems(player, t, tableContext);

  return (
    <div className="min-w-0">
      <div className="truncate text-sm font-medium text-white sm:text-[0.95rem]">
        {player.splashtag}
      </div>
      {summaryItems.length > 0 ? (
        <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-gray-400">
          {summaryItems.map((item, index) => (
            <React.Fragment key={item.key}>
              {index > 0 ? <span className="text-gray-600">·</span> : null}
              <span>
                {item.label}{" "}
                <span className="font-medium text-gray-200 tabular-nums">
                  {item.textValue ?? `×${item.value}`}
                </span>
              </span>
            </React.Fragment>
          ))}
        </div>
      ) : null}
    </div>
  );
};
