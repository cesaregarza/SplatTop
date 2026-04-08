import React from "react";
import { render, screen } from "@testing-library/react";
import TopWeapons from "./weapon_leaderboard";
import useFetchWithCache from "./top500_components/fetch_with_cache";

jest.mock("./top500_components/fetch_with_cache");

jest.mock("./utils", () => ({
  getBaseApiUrl: () => "",
  buildEndpointWithQueryParams: () => "/api/weapon-leaderboard/40",
}));

jest.mock("./utils/cache_utils", () => ({
  getCache: jest.fn(() => null),
  setCache: jest.fn(),
}));

jest.mock("react-i18next", () => ({
  useTranslation: (ns) => ({
    t: (key) =>
      (
        {
          weapon_leaderboard: {
            weapon_title: "Top Weapon Wielders",
            loading: "Loading...",
            "errors.503": "Service Unavailable, please try again later.",
            "header.kicker": "WEAPON EXPLORER",
            "header.meta":
              "Top wielders · %region% · %mode% · %metric% · ≥%threshold%% usage",
            "header.compare_separator": "vs",
            "results.title": "Top wielders",
            "results.summary":
              "Showing %start%–%end% of %total% qualifying entries",
          },
          game: {
            splat_zones: "Splat Zones",
          },
          player: {
            data_lang_key: "USen",
          },
        }
      )[ns]?.[key] || key,
  }),
}));

jest.mock("./utils/weaponAndTranslation", () => ({
  WeaponAndTranslationProvider: ({ children }) => <>{children}</>,
  useWeaponAndTranslation: () => ({
    weaponReferenceData: null,
    weaponTranslations: null,
    isLoading: false,
    error: null,
  }),
}));

jest.mock("./player_components/weapon_helper_functions", () => ({
  getImageFromId: () => null,
  createTranslator: () => ({
    translateWeaponId: () => "Splattershot",
  }),
}));

jest.mock("./leaderboards_components/weapon_leaderboard_table", () => ({
  __esModule: true,
  default: () => <div>WeaponLeaderboardTable</div>,
}));

jest.mock("./top500_components/pagination", () => ({
  __esModule: true,
  default: () => <div>Pagination</div>,
}));

jest.mock("./leaderboards_components/weapon_controls", () => ({
  __esModule: true,
  default: () => <div>WeaponLeaderboardControls</div>,
}));

describe("TopWeapons", () => {
  it("renders the friendly 503 message instead of crashing", async () => {
    useFetchWithCache.mockReturnValue({
      data: null,
      error: {
        status: 503,
        message: "Data is not available yet, please wait.",
      },
      isLoading: false,
    });

    render(<TopWeapons />);

    expect(await screen.findByText("Top Weapon Wielders")).toBeInTheDocument();
    expect(
      await screen.findByText("Service Unavailable, please try again later.")
    ).toBeInTheDocument();
  });
});
