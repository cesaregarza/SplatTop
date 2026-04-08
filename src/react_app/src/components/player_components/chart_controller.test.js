import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import ChartController from "./chart_controller";

const mockXChartSpy = jest.fn();
const mockWeaponsChartSpy = jest.fn();

jest.mock("react-i18next", () => ({
  useTranslation: (ns) => ({
    t: (key) =>
      ({
        player: {
          "controller.mode": "Mode",
          "controller.color": "Color",
          "controller.seasonal": "Seasonal",
          "controller.accessible": "Accessible",
          "controller.weapon_seasons": "Weapon Seasons",
          "controller.color_hint": "Changes chart colors only.",
          "sections.mode_analysis": "Mode Analysis",
          load_chart: "Loading chart",
          load_results: "Loading results",
          no_data: "No data",
        },
        game: {
          spring: "Fresh",
          summer: "Sizzle",
          autumn: "Drizzle",
          winter: "Chill",
          format_short: "%SEASON% %YEAR%",
          rm: "Rainmaker",
          cb: "Clam Blitz",
          sz: "Splat Zones",
          tc: "Tower Control",
        },
      })[ns]?.[key] || key,
  }),
}));

jest.mock("../top500_components/selectors/mode_selector", () => (props) => (
  <div>MODE_SELECTOR:{props.selectedMode}</div>
));

jest.mock("./season_selector", () => () => <div>SEASON_SELECTOR</div>);

jest.mock("./season_results", () => () => <div>SEASON_RESULTS</div>);

jest.mock("./season_archive", () => (props) => (
  <button type="button" onClick={() => props.onSeasonChange(5)}>
    SEASON_ARCHIVE
  </button>
));

jest.mock("./xchart", () => (props) => {
  mockXChartSpy(props);
  return <div>XCHART:{props.mode}</div>;
});

jest.mock("./weapons", () => (props) => {
  mockWeaponsChartSpy(props);
  return <div>WEAPONS_CHART:{props.mode}</div>;
});

describe("ChartController", () => {
  beforeEach(() => {
    mockXChartSpy.mockClear();
    mockWeaponsChartSpy.mockClear();
  });

  it("defaults to the first available mode and season, keeps archive ahead of charts, and preserves archive seasons without mode data", async () => {
    const { container } = render(
      <ChartController
        data={{
          player_data: [
            { mode: "Rainmaker", season_number: 5 },
            { mode: "Clam Blitz", season_number: 4 },
          ],
          aggregated_data: {
            weapon_counts: [],
            weapon_winrate: [],
            season_results: [],
            aggregate_season_data: [],
            latest_data: [],
          },
        }}
        modes={["Splat Zones", "Tower Control", "Rainmaker", "Clam Blitz"]}
        weaponTranslations={{}}
        weaponReferenceData={{}}
        analysisReady={true}
      />
    );

    expect(mockXChartSpy).toHaveBeenLastCalledWith(
      expect.objectContaining({ mode: "Rainmaker", selectedSeason: 6 })
    );
    expect(mockWeaponsChartSpy).toHaveBeenLastCalledWith(
      expect.objectContaining({ mode: "Rainmaker" })
    );

    const markup = container.textContent;
    expect(markup.indexOf("SEASON_RESULTS")).toBeLessThan(
      markup.indexOf("SEASON_ARCHIVE")
    );
    expect(markup.indexOf("SEASON_ARCHIVE")).toBeLessThan(
      markup.indexOf("XCHART:Rainmaker")
    );
    expect(markup.indexOf("XCHART:Rainmaker")).toBeLessThan(
      markup.indexOf("WEAPONS_CHART:Rainmaker")
    );

    fireEvent.click(screen.getByRole("button", { name: "SEASON_ARCHIVE" }));

    await waitFor(() => {
      expect(mockXChartSpy).toHaveBeenLastCalledWith(
        expect.objectContaining({ mode: "Rainmaker", selectedSeason: 5 })
      );
    });
  });

  it("keeps season snapshot available while analysis is still loading", () => {
    render(
      <ChartController
        data={{
          player_data: [],
          aggregated_data: {
            weapon_counts: [],
            weapon_winrate: [],
            season_results: [{ season_number: 6, mode: "Rainmaker", rank: 3 }],
            aggregate_season_data: [],
            latest_data: [],
          },
        }}
        modes={["Splat Zones", "Tower Control", "Rainmaker", "Clam Blitz"]}
        weaponTranslations={{}}
        weaponReferenceData={{}}
        analysisReady={false}
        analysisLoading={true}
      />
    );

    expect(screen.getByText("SEASON_RESULTS")).toBeInTheDocument();
    expect(screen.getByText("SEASON_ARCHIVE")).toBeInTheDocument();
    expect(screen.getByText("Loading chart")).toBeInTheDocument();
    expect(screen.getByText("Loading results")).toBeInTheDocument();
    expect(mockXChartSpy).not.toHaveBeenCalled();
  });
});
