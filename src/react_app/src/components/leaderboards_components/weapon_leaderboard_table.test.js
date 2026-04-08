import React from "react";
import { render, screen } from "@testing-library/react";

import WeaponLeaderboardTable from "./weapon_leaderboard_table";

const mockNavigate = jest.fn();

jest.mock("react-router-dom", () => ({
  useNavigate: () => mockNavigate,
}));

jest.mock("react-i18next", () => ({
  useTranslation: (ns) => ({
    t: (key) =>
      (
        {
          undefined: {
            column_rank_title: "Rank",
            column_weapon_title: "Weapon",
            column_splashtag_title: "Splashtag",
            column_peak_xpower_title: "Peak X Power",
            column_percent_games_played_title: "Usage",
            column_season_number_title: "Season",
            column_weapon_not_supported: "Weapon",
          },
          game: {
            "Fresh Season": "Fresh Season",
          },
        }
      )[String(ns)]?.[key] || key,
  }),
}));

jest.mock("../player_components/xchart_helper_functions", () => ({
  getSeasonName: (seasonNumber) => `Season ${seasonNumber}`,
}));

describe("WeaponLeaderboardTable", () => {
  const players = [
    {
      player_id: "player-1",
      alias: "mL Shadow #3141",
      rank: 1,
      max_x_power: 3474.4,
      percent_games_played: 0.643,
      season_number: 12,
      weapon_id: 40,
      weapon_image: "/weapon.png",
    },
  ];

  it("hides the weapon column when compare mode is off", () => {
    render(
      <WeaponLeaderboardTable
        players={players}
        isFinal={false}
        showWeaponColumn={false}
      />
    );

    expect(screen.queryByText("Weapon")).not.toBeInTheDocument();
    expect(screen.getByText("Usage")).toBeInTheDocument();
    expect(screen.getByText("mL Shadow #3141")).toBeInTheDocument();
  });

  it("shows the weapon column when compare mode is on", () => {
    render(
      <WeaponLeaderboardTable
        players={players}
        isFinal={false}
        showWeaponColumn={true}
      />
    );

    expect(screen.getByText("Weapon")).toBeInTheDocument();
  });
});
