import React from "react";
import { render, screen } from "@testing-library/react";
import SeasonResults from "./season_results";

jest.mock("chroma-js", () => ({
  __esModule: true,
  default: {
    lab: (...args) => ({
      hex: () =>
        typeof args[0] === "string"
          ? args[0]
          : `#${(Math.abs(Math.round((args[0] || 0) * 1000)) % 0xffffff)
              .toString(16)
              .padStart(6, "0")}`,
      lab: () => (Array.isArray(args[0]) ? args[0] : args),
    }),
  },
}));

jest.mock("react-i18next", () => ({
  useTranslation: (ns) => ({
    t: (key) =>
      ({
        player: {
          "sections.season_snapshot": "Season Snapshot",
          "results.title": "Season Results",
          "results.archive": "Archive",
          "results.status.live": "Live season snapshot",
          "results.status.final": "Final season results",
          "results.table.mode": "Mode",
          "results.table.rank": "Rank",
          "results.table.current_xp": "Current XP",
          "results.table.final_xp": "Final XP",
          "results.table.peak_xp": "Peak XP",
          "results.table.current_weapon": "Current Weapon",
          "results.table.final_weapon": "Final Weapon",
          "results.table.most_used_weapon": "Most Used Weapon",
          "xchart.live_indicator": "LIVE",
        },
        game: {
          sz: "Splat Zones",
          tc: "Tower Control",
          rm: "Rainmaker",
          cb: "Clam Blitz",
        },
      })[ns]?.[key] || key,
  }),
}));

jest.mock("../utils/season_utils", () => ({
  calculateSeasonNow: () => 5,
  getSeasonName: (seasonNumber) => `Season ${seasonNumber}`,
}));

describe("SeasonResults", () => {
  it("renders header controls and overflows older seasons into the archive selector", () => {
    render(
      <SeasonResults
        data={{
          aggregated_data: {
            weapon_counts: [],
            aggregate_season_data: [],
            latest_data: [],
            season_results: [
              { season_number: 6, mode: "Rainmaker", rank: 1, x_power: 3000 },
              { season_number: 5, mode: "Rainmaker", rank: 2, x_power: 2900 },
              { season_number: 4, mode: "Rainmaker", rank: 3, x_power: 2800 },
              { season_number: 3, mode: "Rainmaker", rank: 4, x_power: 2700 },
              { season_number: 2, mode: "Rainmaker", rank: 5, x_power: 2600 },
            ],
          },
        }}
        weaponReferenceData={null}
        headerControls={<div>HEADER_CONTROLS</div>}
      />
    );

    expect(screen.getByText("HEADER_CONTROLS")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Season 5/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Season 4/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Season 3/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Season 2/i })).toBeInTheDocument();
    expect(screen.getByRole("combobox")).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Season 1" })).toBeInTheDocument();
  });

  it("keeps an archive-selected season active even when the results table has no rows for it", () => {
    const onSeasonChange = jest.fn();

    render(
      <SeasonResults
        data={{
          player_data: [
            {
              mode: "Rainmaker",
              season_number: 6,
              timestamp: "2026-01-01T00:00:00.000Z",
              x_power: 2710,
            },
          ],
          aggregated_data: {
            weapon_counts: [],
            aggregate_season_data: [],
            latest_data: [],
            season_results: [
              { season_number: 6, mode: "Rainmaker", rank: 1, x_power: 3000 },
            ],
          },
        }}
        weaponReferenceData={null}
        activeSeason={7}
        onSeasonChange={onSeasonChange}
      />
    );

    expect(onSeasonChange).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: /Season 6/i })).toBeInTheDocument();
    expect(screen.getAllByText("--").length).toBeGreaterThan(0);
  });
});
