import React from "react";
import { render, screen } from "@testing-library/react";
import Top500 from "./top500";
import useFetchWithCache from "./top500_components/fetch_with_cache";

jest.mock("./top500_components/fetch_with_cache");

jest.mock("./utils", () => ({
  getBaseApiUrl: () => "",
}));

jest.mock("./utils/cache_utils", () => ({
  getCache: jest.fn(() => null),
  setCache: jest.fn(),
  deleteCache: jest.fn(),
}));

jest.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key, options = {}) => {
      const translations = {
        title: "Top 500",
        loading: "Loading...",
        loading_top500: "Loading Top 500...",
        search_placeholder: "Search...",
        "header.kicker": "Leaderboard",
        "header.metadata": "%region% Region · %mode% · %count% players",
        "controls.region": "Region",
        "controls.mode": "Mode",
        "controls.search": "Search",
        "controls.columns": "Columns",
        "controls.page": "Page",
        "results.title": "Top 500 Rankings",
        "results.summary": "Showing %start%-%end% of %total% players",
        no_results: "No results!",
        all_modes: "All Modes",
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

jest.mock("./top500_components/player_table", () => ({
  __esModule: true,
  default: ({ players }) => <div>PlayerTable {players.length}</div>,
}));

jest.mock("./top500_components/all_modes_table", () => ({
  __esModule: true,
  default: ({ players }) => <div>AllModesTable {players.length}</div>,
}));

jest.mock("./top500_components/selectors/column_selector", () => ({
  __esModule: true,
  default: () => <div>ColumnSelector</div>,
}));

jest.mock("./top500_components/selectors/region_selector", () => ({
  __esModule: true,
  default: () => <div>RegionSelector</div>,
}));

jest.mock("./top500_components/selectors/mode_selector", () => ({
  __esModule: true,
  default: () => <div>ModeSelector</div>,
}));

jest.mock("./top500_components/pagination", () => ({
  __esModule: true,
  default: ({ currentPage }) => <div>Pagination {currentPage}</div>,
}));

describe("Top500", () => {
  it("renders a compact leaderboard header and results summary", async () => {
    useFetchWithCache.mockReturnValue({
      data: {
        players: {
          player_id: ["1", "2"],
          rank: [1, 2],
          splashtag: ["Alpha", "Beta"],
          weapon_image: ["a.png", "b.png"],
          prev_season_region: [false, true],
          diamond_x_count: [0, 1],
          gold_x_count: [1, 0],
          silver_x_count: [2, 1],
          x_power: [3012.3, 2990.1],
        },
      },
      error: null,
      isLoading: false,
    });

    render(<Top500 />);

    expect(await screen.findByText("Leaderboard")).toBeInTheDocument();
    expect(screen.getByText("Tentatek Region · Splat Zones · 2 players")).toBeInTheDocument();
    expect(screen.getByText("Top 500 Rankings")).toBeInTheDocument();
    expect(screen.getByText("Showing 1-2 of 2 players")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Search...")).toBeInTheDocument();
    expect(await screen.findByText("PlayerTable 2")).toBeInTheDocument();
  });
});
