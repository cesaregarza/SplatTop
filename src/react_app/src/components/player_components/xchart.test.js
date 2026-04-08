import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import XChart from "./xchart";

const capturedOptions = [];

jest.mock("react-i18next", () => ({
  useTranslation: (ns) => ({
    t: (key) =>
      (
        {
          player: {
            "xchart.title": "%MODE% X Power",
            "xchart.xaxis.title": "% of Season Elapsed",
            "xchart.xaxis.start": "Start",
            "xchart.xaxis.end": "End",
            "xchart.yaxis.title": "X Power",
            "xchart.live_indicator": "LIVE",
            "xchart.now": "Now",
            "analysis.legend.selected_run": "Selected run",
            "analysis.legend.historical_range": "Historical range",
            "analysis.stats.current_xp": "Current XP",
            "analysis.stats.peak_xp": "Peak XP",
            "analysis.stats.rank": "Current Rank",
            "analysis.stats.season_elapsed": "Season Elapsed",
            "analysis.stats.tracked_updates": "Tracked Updates",
            no_data: "No data available",
          },
          game: {
            rm: "Rainmaker",
            spring: "Fresh",
            summer: "Sizzle",
            autumn: "Drizzle",
            winter: "Chill",
            format_short: "Season %YEAR% %SEASON%",
          },
        }
      )[ns]?.[key] || key,
  }),
}));

jest.mock("highcharts-react-official", () => (props) => {
  capturedOptions.push(props.options);
  return <div data-testid="highcharts-react" />;
});

jest.mock("highcharts/highstock", () => ({}));
jest.mock("highcharts/highcharts-more", () => () => null);

jest.mock("./splatfest_retriever", () => jest.fn(() => Promise.resolve([])));

jest.mock("../utils/season_utils", () => ({
  getPercentageInSeason: (timestamp) => {
    if (timestamp instanceof Date) {
      return 25;
    }

    return (
      {
        "season-7-start": 0,
        "season-7-mid": 50,
        "season-7-end": 100,
        "season-8-start": 0,
        "season-8-mid": 50,
        "season-8-end": 100,
        "season-9-start": 0,
        "season-9-now": 15,
      }[timestamp] ?? 0
    );
  },
  calculateSeasonNow: () => 9,
  calculateSeasonByTimestamp: () => 9,
  getSeasonName: (seasonNumber) => `Season ${seasonNumber}`,
}));

describe("XChart", () => {
  beforeEach(() => {
    capturedOptions.length = 0;
  });

  it("renders a shorter sparse live chart with a historical range band and no in-plot title", async () => {
    render(
      <XChart
        data={[
          { mode: "Rainmaker", season_number: 7, timestamp: "season-7-start", x_power: 2400 },
          { mode: "Rainmaker", season_number: 7, timestamp: "season-7-mid", x_power: 2600 },
          { mode: "Rainmaker", season_number: 7, timestamp: "season-7-end", x_power: 2500 },
          { mode: "Rainmaker", season_number: 8, timestamp: "season-8-start", x_power: 2500 },
          { mode: "Rainmaker", season_number: 8, timestamp: "season-8-mid", x_power: 2700 },
          { mode: "Rainmaker", season_number: 8, timestamp: "season-8-end", x_power: 2800 },
          { mode: "Rainmaker", season_number: 9, timestamp: "season-9-start", x_power: 2720.2 },
          { mode: "Rainmaker", season_number: 9, timestamp: "season-9-now", x_power: 2765.5 },
        ]}
        mode="Rainmaker"
        colorMode="Seasonal"
        selectedSeason={10}
        analysisSummary={{
          currentXp: 2765.5,
          isCurrent: true,
          isSparse: true,
          peakXp: 2780.1,
          rank: 7,
          seasonElapsed: 25,
          trackedUpdates: 2,
        }}
      />
    );

    await waitFor(() =>
      expect(screen.getByText("Tracked Updates")).toBeInTheDocument()
    );

    const options = capturedOptions[capturedOptions.length - 1];

    expect(screen.getByText("Current XP")).toBeInTheDocument();
    expect(screen.getByText("2765.5")).toBeInTheDocument();
    expect(screen.getByText("Historical range")).toBeInTheDocument();
    expect(screen.getByTestId("highcharts-react")).toBeInTheDocument();
    expect(options.title.text).toBeNull();
    expect(options.subtitle.text).toBeNull();
    expect(options.chart.height).toBe(260);
    expect(options.xAxis.max).toBe(100);
    expect(options.xAxis.plotLines[0].value).toBe(25);
    expect(options.series[0].type).toBe("arearange");
    expect(options.series[0].fillOpacity).toBe(0.3);
    expect(options.series[0].lineWidth).toBe(1);
    expect(options.series[0].lineColor).toBe("rgba(226, 232, 240, 0.45)");
    expect(options.series[1].name).toBe("Season 9");
  });

  it("does not crash when the selected season has no chart points for the current mode", async () => {
    render(
      <XChart
        data={[
          { mode: "Rainmaker", season_number: 7, timestamp: "season-7-start", x_power: 2400 },
          { mode: "Rainmaker", season_number: 7, timestamp: "season-7-mid", x_power: 2600 },
          { mode: "Rainmaker", season_number: 7, timestamp: "season-7-end", x_power: 2500 },
          { mode: "Rainmaker", season_number: 8, timestamp: "season-8-start", x_power: 2500 },
          { mode: "Rainmaker", season_number: 8, timestamp: "season-8-mid", x_power: 2700 },
          { mode: "Rainmaker", season_number: 8, timestamp: "season-8-end", x_power: 2800 },
        ]}
        mode="Rainmaker"
        colorMode="Seasonal"
        selectedSeason={10}
        analysisSummary={{
          currentXp: null,
          isCurrent: false,
          isSparse: false,
          peakXp: null,
          rank: null,
          seasonElapsed: 100,
          trackedUpdates: 0,
        }}
      />
    );

    await waitFor(() =>
      expect(screen.getByTestId("highcharts-react")).toBeInTheDocument()
    );

    const options = capturedOptions[capturedOptions.length - 1];

    expect(options.xAxis.max).toBe(100);
    expect(options.title.text).toBeNull();
    expect(options.series).toHaveLength(1);
    expect(options.series[0].type).toBe("arearange");
  });
});
