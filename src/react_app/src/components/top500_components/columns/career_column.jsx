import React from "react";

export const id = "career";
export const title_key = "column_career_title";
export const isVisible = true;
export const headerClasses =
  "w-[17rem] px-4 py-2.5 text-left text-[0.68rem] font-semibold uppercase tracking-[0.16em] text-gray-300";
export const cellClasses =
  "w-[17rem] px-4 py-2.5 text-left align-middle text-sm text-gray-300";

export const render = (player, t) => {
  const parts = [];

  if (player.diamond_x_count > 0) {
    parts.push({
      key: "diamond",
      value: player.diamond_x_count,
      label:
        player.diamond_x_count === 1
          ? t("career.all_mode_top10_season")
          : t("career.all_mode_top10_seasons"),
    });
  }

  if (player.gold_x_count > 0) {
    parts.push({
      key: "top10",
      value: player.gold_x_count,
      label: t("career.top10"),
    });
  }

  if (player.silver_x_count > 0) {
    parts.push({
      key: "top500",
      value: player.silver_x_count,
      label: t("career.top500"),
    });
  }

  if (parts.length === 0) {
    return <span className="text-gray-500">—</span>;
  }

  return (
    <div className="truncate whitespace-nowrap">
      {parts.map((part, index) => (
        <React.Fragment key={part.key}>
          {index > 0 ? <span className="mx-1.5 text-gray-600">·</span> : null}
          <span>
            <span className="font-medium text-gray-100 tabular-nums">
              {part.value}
            </span>{" "}
            <span>{part.label}</span>
          </span>
        </React.Fragment>
      ))}
    </div>
  );
};
