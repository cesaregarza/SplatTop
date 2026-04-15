import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import LegacyLeaderboards from "./legacy_leaderboards";
import { getCache } from "../utils/cache_utils";

jest.mock("react-i18next", () => ({
  useTranslation: (ns) => ({
    t: (key) =>
      (
        {
          main_page: {
            column_season_number_title: "Season",
            search_placeholder: "Search",
            loading: "Loading...",
            no_data: "No data",
          },
          game: {
            spring: "Fresh",
            summer: "Sizzle",
            autumn: "Drizzle",
            winter: "Chill",
            format_short: "%SEASON% %YEAR%",
          },
          weapon_leaderboard: {
            all_seasons: "All seasons",
          },
        }
      )[ns]?.[key] || key,
  }),
}));

jest.mock("../utils", () => ({
  getBaseApiUrl: () => "",
  buildEndpointWithQueryParams: (_baseUrl, endpoint, params) => {
    const url = new URL(endpoint, "https://example.com");
    Object.entries(params).forEach(([key, value]) => {
      url.searchParams.append(key, value);
    });
    return `${url.pathname}${url.search}`;
  },
}));

jest.mock("../utils/cache_utils", () => ({
  getCache: jest.fn(() => null),
  setCache: jest.fn(),
}));

jest.mock("../utils/season_utils", () => ({
  calculateSeasonNow: () => 4,
  getSeasonName: (season) =>
    (
      {
        1: "Chill 2022",
        2: "Fresh 2023",
        3: "Sizzle 2023",
        4: "Drizzle 2023",
      }
    )[season] || `Season ${season}`,
}));

jest.mock("../top500_components/player_table", () => ({
  __esModule: true,
  default: () => <div>PlayerTable</div>,
}));

jest.mock("../top500_components/pagination", () => ({
  __esModule: true,
  default: () => <div>Pagination</div>,
}));

jest.mock("../top500_components/selectors/region_selector", () => ({
  __esModule: true,
  default: ({ selectedRegion }) => <div>Region: {selectedRegion}</div>,
}));

jest.mock("../top500_components/selectors/mode_selector", () => ({
  __esModule: true,
  default: ({ selectedMode }) => <div>Mode: {selectedMode}</div>,
}));

describe("LegacyLeaderboards", () => {
  beforeEach(() => {
    getCache.mockImplementation((key) =>
      key === "legacy.selectedSeason" ? "2" : null
    );
    global.fetch = jest.fn();
  });

  afterEach(() => {
    jest.resetAllMocks();
  });

  it("shows fallback season options while the initial request is still loading", async () => {
    global.fetch.mockImplementationOnce(() => new Promise(() => {}));

    render(<LegacyLeaderboards />);

    const seasonButton = await screen.findByRole("button", {
      name: /fresh/i,
    });
    expect(seasonButton).not.toBeDisabled();

    fireEvent.click(seasonButton);

    expect(
      screen.getByRole("option", {
        name: /chill/i,
      })
    ).toBeInTheDocument();
  });

  it("updates the season selector immediately while the next request is loading", async () => {
    const initialPayload = {
      players: {
        splashtag: ["fresh-tag"],
        rank: [1],
        x_power: [2500.1],
        weapon_image: ["/weapon.png"],
      },
      season_number: 2,
      available_seasons: [2, 1],
    };

    global.fetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => initialPayload,
      })
      .mockImplementationOnce(() => new Promise(() => {}));

    render(<LegacyLeaderboards />);

    const seasonButton = await screen.findByRole("button", {
      name: /fresh/i,
    });
    await waitFor(() => expect(seasonButton).not.toBeDisabled());
    expect(screen.getByText("Season 2 · Fresh 2023")).toBeInTheDocument();

    fireEvent.click(seasonButton);

    const seasonOneOption = screen.getByRole("option", {
      name: /chill/i,
    });
    expect(seasonOneOption).toBeInTheDocument();

    fireEvent.click(seasonOneOption);

    expect(screen.getByText("Season 1 · Chill 2022")).toBeInTheDocument();
    expect(global.fetch).toHaveBeenLastCalledWith(
      expect.stringContaining("season=1"),
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    );
  });
});
