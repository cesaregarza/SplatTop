import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import SeasonArchive from "./season_archive";

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
            "archive.row_hint": "Click to inspect this season.",
            "archive.no_mode_data": "No data for this mode in this season.",
            "archive.table.season": "Season",
            "archive.table.peak_xp": "Peak XP",
            "archive.table.finish": "Finish",
            "archive.table.progression": "Progression",
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
  it("renders archive rows and only allows selecting seasons with mode data", () => {
    const onSeasonChange = jest.fn();

    render(
      <SeasonArchive
        data={{
          player_data: [
            {
              mode: "Rainmaker",
              season_number: 5,
              timestamp: "2026-02-01T00:00:00.000Z",
              x_power: 2600,
            },
            {
              mode: "Rainmaker",
              season_number: 5,
              timestamp: "2026-02-15T00:00:00.000Z",
              x_power: 2700,
            },
            {
              mode: "Rainmaker",
              season_number: 5,
              timestamp: "2026-03-01T00:00:00.000Z",
              x_power: 2730,
            },
          ],
          aggregated_data: {
            season_results: [
              {
                season_number: 6,
                region: true,
                mode: "Rainmaker",
                rank: 4,
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
        activeSeason={6}
        onSeasonChange={onSeasonChange}
      />
    );

    expect(screen.getByText("Progression by season")).toBeInTheDocument();
    expect(screen.getByText("Selected")).toBeInTheDocument();

    const [activeRow, disabledRow] = screen.getAllByRole("button");

    fireEvent.click(activeRow);
    expect(onSeasonChange).toHaveBeenCalledWith(6);

    expect(disabledRow).toBeDisabled();
  });
});
