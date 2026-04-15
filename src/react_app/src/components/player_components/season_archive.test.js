import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import SeasonArchive from "./season_archive";

jest.mock("../utils/season_utils", () => ({
  calculateSeasonNow: () => 9,
  getSeasonName: (seasonNumber) => `Season ${seasonNumber}`,
}));

jest.mock("react-i18next", () => ({
  useTranslation: (ns) => ({
    t: (key) =>
      (
        {
          player: {
            "sections.season_archive": "Season Archive",
            "archive.title": "Progression by season",
            "archive.selected_hint": "Selected: %SEASON%",
            "archive.empty_hint":
              "Choose a season with data to inspect the full run.",
            "archive.selected": "Selected",
            "xchart.live_indicator": "Live",
            "archive.row_hint": "Click to inspect this season.",
            "archive.no_mode_data": "No data for this mode in this season.",
            "archive.table.season": "Season",
            "archive.table.peak_xp": "Peak XP",
            "archive.table.finish": "Finish",
            "archive.table.progression": "Progression",
            "archive.show_more": "Show archive (%COUNT%)",
            "archive.hide_more": "Hide archive",
          },
          game: {
            spring: "Fresh",
            summer: "Sizzle",
            autumn: "Drizzle",
            winter: "Chill",
            format_short: "%SEASON% %YEAR%",
          },
        }
      )[ns]?.[key] || key,
  }),
}));

describe("SeasonArchive", () => {
  it("shows a compact recent set and expands hidden archive rows on demand", () => {
    const onSeasonChange = jest.fn();

    render(
      <SeasonArchive
        data={{
          player_data: [
            {
              mode: "Rainmaker",
              season_number: 4,
              region: false,
              timestamp: "2025-11-01T00:00:00.000Z",
              x_power: 2550,
            },
            {
              mode: "Rainmaker",
              season_number: 5,
              region: false,
              timestamp: "2026-02-01T00:00:00.000Z",
              x_power: 2600,
            },
            {
              mode: "Rainmaker",
              season_number: 5,
              region: false,
              timestamp: "2026-02-15T00:00:00.000Z",
              x_power: 2700,
            },
            {
              mode: "Rainmaker",
              season_number: 6,
              region: true,
              timestamp: "2026-04-10T00:00:00.000Z",
              x_power: 2750,
            },
            {
              mode: "Rainmaker",
              season_number: 7,
              region: true,
              timestamp: "2026-07-10T00:00:00.000Z",
              x_power: 2810,
            },
            {
              mode: "Rainmaker",
              season_number: 8,
              region: false,
              timestamp: "2026-10-10T00:00:00.000Z",
              x_power: 2860,
            },
            {
              mode: "Rainmaker",
              season_number: 9,
              region: true,
              timestamp: "2026-03-01T00:00:00.000Z",
              x_power: 2730,
            },
          ],
          aggregated_data: {
            season_results: [
              {
                season_number: 10,
                region: true,
                mode: "Rainmaker",
                rank: 4,
              },
              {
                season_number: 9,
                region: false,
                mode: "Rainmaker",
                rank: 12,
              },
              {
                season_number: 8,
                region: false,
                mode: "Rainmaker",
                rank: 18,
              },
              {
                season_number: 7,
                region: true,
                mode: "Rainmaker",
                rank: 31,
              },
              {
                season_number: 6,
                region: true,
                mode: "Rainmaker",
                rank: 48,
              },
              {
                season_number: 5,
                region: false,
                mode: "Splat Zones",
                rank: 12,
              },
            ],
            aggregate_season_data: [
              {
                season_number: 5,
                mode: "Rainmaker",
                peak_x_power: 2730,
              },
            ],
          },
        }}
        mode="Rainmaker"
        activeSeason={5}
        onSeasonChange={onSeasonChange}
      />
    );

    expect(screen.getByText("Progression by season")).toBeInTheDocument();
    expect(screen.getByText("Selected")).toBeInTheDocument();
    expect(screen.getByText("Live")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Show archive (2)" })).toBeInTheDocument();

    const seasonButtons = screen
      .getAllByRole("button")
      .filter((button) => button.textContent.includes("Season"));

    expect(seasonButtons).toHaveLength(4);
    expect(seasonButtons[0]).toHaveTextContent("Season 9");
    expect(seasonButtons[1]).toHaveTextContent("Season 8");
    expect(seasonButtons[2]).toHaveTextContent("Season 7");
    expect(seasonButtons[3]).toHaveTextContent("Season 4");
    expect(screen.getByText("Season 4")).toBeInTheDocument();
    expect(screen.queryByText("Season 6")).not.toBeInTheDocument();
    expect(screen.queryByText("Season 5")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Show archive (2)" }));

    expect(screen.getByRole("button", { name: "Hide archive" })).toBeInTheDocument();
    expect(
      screen.getByTestId("season-archive-scroll-region")
    ).toBeInTheDocument();
    expect(screen.getByText("Season 6")).toBeInTheDocument();
    expect(screen.getByText("Season 5")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Season 6"));
    expect(onSeasonChange).toHaveBeenCalledWith(7);

    fireEvent.click(screen.getByText("Season 5"));
    expect(onSeasonChange).toHaveBeenCalledWith(6);
  });

  it("shows unknown instead of Tentatek when a season has no region data", () => {
    render(
      <SeasonArchive
        data={{
          player_data: [
            {
              mode: "Rainmaker",
              season_number: 5,
              timestamp: "2026-02-15T00:00:00.000Z",
              x_power: 2700,
            },
          ],
          aggregated_data: {
            season_results: [],
            aggregate_season_data: [],
            latest_data: [],
          },
        }}
        mode="Rainmaker"
        activeSeason={6}
      />
    );

    expect(screen.getByLabelText("Unknown region")).toBeInTheDocument();
    expect(screen.queryByAltText("Tentatek")).not.toBeInTheDocument();
  });
});
