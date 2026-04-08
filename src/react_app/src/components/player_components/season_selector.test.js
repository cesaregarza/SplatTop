import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import SeasonSelector from "./season_selector";

const mockTranslations = {
  player: {
    "controller.select_season": "Select Seasons (Weapons)",
    "controller.weapon_seasons": "Weapon Seasons",
    "controller.select_all": "Select all",
    "controller.clear_all": "Clear all",
    "controller.no_seasons_available": "No seasons available",
    "controller.all_seasons_shown": "All seasons shown",
    "controller.all_available_seasons": "All available seasons",
    "controller.one_season_selected": "1 season selected",
    "controller.many_seasons_selected": "%COUNT% seasons selected",
  },
  game: {
    winter: "Chill",
    spring: "Fresh",
    summer: "Sizzle",
    autumn: "Drizzle",
    format_short: "%SEASON% %YEAR%",
  },
};

jest.mock("react-i18next", () => ({
  useTranslation: (ns) => ({
    t: (key) => mockTranslations[ns]?.[key] || key,
  }),
}));

describe("SeasonSelector", () => {
  it("shows current selection state and supports select-all / clear-all actions", async () => {
    const onSeasonChange = jest.fn();

    render(
      <SeasonSelector
        data={{
          weapon_counts: [
            { mode: "Rainmaker", season_number: 1 },
            { mode: "Rainmaker", season_number: 2 },
          ],
        }}
        mode="Rainmaker"
        onSeasonChange={onSeasonChange}
      />
    );

    await waitFor(() => {
      expect(onSeasonChange).toHaveBeenCalledWith([1, 2]);
    });

    expect(screen.getByText("All available seasons")).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", { name: /Select Seasons \(Weapons\)/ })
    );

    const enabledCheckboxes = screen
      .getAllByRole("checkbox")
      .filter((checkbox) => !checkbox.disabled);

    fireEvent.click(enabledCheckboxes[0]);

    expect(screen.getByText("1 season selected")).toBeInTheDocument();
    expect(onSeasonChange).toHaveBeenLastCalledWith([2]);

    fireEvent.click(screen.getByRole("button", { name: "Clear all" }));
    expect(screen.getByText("All seasons shown")).toBeInTheDocument();
    expect(onSeasonChange).toHaveBeenLastCalledWith([]);

    fireEvent.click(screen.getByRole("button", { name: "Select all" }));
    expect(screen.getByText("All available seasons")).toBeInTheDocument();
    expect(onSeasonChange).toHaveBeenLastCalledWith([1, 2]);
  });

  it("hydrates available seasons when weapon data arrives after the initial render", async () => {
    const onSeasonChange = jest.fn();
    const { rerender } = render(
      <SeasonSelector
        data={{ weapon_counts: [] }}
        mode="Rainmaker"
        onSeasonChange={onSeasonChange}
        compact={true}
        disabled={true}
        loadingLabel="Loading chart"
      />
    );

    expect(screen.getByText("Loading chart")).toBeInTheDocument();

    rerender(
      <SeasonSelector
        data={{
          weapon_counts: [
            { mode: "Rainmaker", season_number: 1 },
            { mode: "Rainmaker", season_number: 2 },
          ],
        }}
        mode="Rainmaker"
        onSeasonChange={onSeasonChange}
        compact={true}
      />
    );

    await waitFor(() => {
      expect(onSeasonChange).toHaveBeenLastCalledWith([1, 2]);
    });
    expect(screen.getByText("All available seasons")).toBeInTheDocument();
  });
});
