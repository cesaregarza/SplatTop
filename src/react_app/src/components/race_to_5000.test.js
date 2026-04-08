import React from "react";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import RaceTo5000 from "./race_to_5000";
import useFetchWithCache from "./top500_components/fetch_with_cache";

jest.mock("./top500_components/fetch_with_cache");

jest.mock("./utils", () => ({
  getBaseApiUrl: () => "",
}));

jest.mock("./misc_components/loading", () => ({
  __esModule: true,
  default: ({ text }) => <div>{text}</div>,
}));

jest.mock("highcharts-react-official", () => ({
  __esModule: true,
  default: ({ options }) => (
    <div>
      <div data-testid="race-chart">{options.series.length} series</div>
      {options.series.map((series) => (
        <div key={series.name}>{series.name}</div>
      ))}
    </div>
  ),
}));

jest.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key, options = {}) => {
      const translations = {
        spring: "Fresh",
        summer: "Sizzle",
        autumn: "Drizzle",
        winter: "Chill",
        format_short: "%SEASON% %YEAR%",
        sz: "Splat Zones",
        tc: "Tower Control",
        rm: "Rainmaker",
        cb: "Clam Blitz",
      };

      let value = translations[key] || options.defaultValue || key;
      Object.entries(options).forEach(([placeholder, replacement]) => {
        value = value.replace(
          new RegExp(`%${placeholder}%`, "g"),
          String(replacement)
        );
      });
      return value;
    },
  }),
}));

describe("RaceTo5000", () => {
  it("renders the race chart and current contenders table", async () => {
    useFetchWithCache.mockReturnValue({
      data: {
        current_season: 10,
        current_threshold: 4000,
        historical_threshold: 5000,
        updated_at: "2026-04-07T12:00:00Z",
        current_runs: [
          {
            run_id: "p1:10:Rainmaker:0",
            player_id: "p1",
            splashtag: "Alpha#1111",
            season_number: 10,
            mode: "Rainmaker",
            region: "Tentatek",
            current_x_power: 4310.4,
            peak_x_power: 4331.8,
            last_updated: "2026-04-07T12:00:00Z",
            points: [
              {
                timestamp: "2026-03-10T00:00:00Z",
                x_power: 4012.2,
              },
              {
                timestamp: "2026-04-07T12:00:00Z",
                x_power: 4310.4,
              },
            ],
          },
        ],
        historical_runs: [
          {
            run_id: "p2:9:Splat Zones:1",
            player_id: "p2",
            splashtag: "Beta#2222",
            season_number: 9,
            mode: "Splat Zones",
            region: "Takoroka",
            current_x_power: 5010.1,
            peak_x_power: 5098.6,
            last_updated: "2025-12-01T00:00:00Z",
            points: [
              {
                timestamp: "2025-09-10T00:00:00Z",
                x_power: 4702.2,
              },
              {
                timestamp: "2025-11-10T00:00:00Z",
                x_power: 5098.6,
              },
            ],
          },
        ],
      },
      error: null,
      isLoading: false,
    });

    render(
      <MemoryRouter>
        <RaceTo5000 />
      </MemoryRouter>
    );

    expect(screen.getByText("Race to 5000")).toBeInTheDocument();
    expect(screen.getByTestId("race-chart")).toHaveTextContent("2 series");
    expect(
      screen.getByText(
        /Fresh 2025 · 1 contenders over 4000 XP · 1 historical 5000\+ runs/
      )
    ).toBeInTheDocument();
    expect(await screen.findByText("Alpha#1111")).toBeInTheDocument();
    expect(screen.getByText("Rainmaker")).toBeInTheDocument();
    expect(screen.getByText("Tentatek")).toBeInTheDocument();
    expect(screen.getByText("Beta#2222 · Chill 2024")).toBeInTheDocument();
    expect(screen.getByText("4310.4")).toBeInTheDocument();
    expect(screen.getByText("4331.8")).toBeInTheDocument();
  });

  it("renders the API error cleanly", async () => {
    useFetchWithCache.mockReturnValue({
      data: null,
      error: new Error("Data is not available yet, please wait."),
      isLoading: false,
    });

    render(
      <MemoryRouter>
        <RaceTo5000 />
      </MemoryRouter>
    );

    expect(
      await screen.findByText("Data is not available yet, please wait.")
    ).toBeInTheDocument();
  });
});
