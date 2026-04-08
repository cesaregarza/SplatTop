import React from "react";
import { render, screen } from "@testing-library/react";
import { render as renderSplashtag } from "./splashtag_column";

const t = (key) => {
  const labels = {
    "highlights.origin": "Origin",
    "highlights.diamond": "Diamond",
    "highlights.top10": "Top 10",
    "highlights.top500": "Top 500",
  };

  return labels[key] || key;
};

describe("splashtag column", () => {
  const hasExactText = (text) => (_, node) => node?.textContent === text;

  it("renders career history as a muted metadata line under the player name", () => {
    const player = {
      splashtag: "ぐーぐー★かめお#1153",
      prev_season_region: true,
      diamond_x_count: 1,
      gold_x_count: 12,
      silver_x_count: 34,
    };

    render(
      renderSplashtag(player, t, {
        selectedRegion: "Takoroka",
      })
    );

    expect(screen.getByText("ぐーぐー★かめお#1153")).toBeInTheDocument();
    expect(screen.getByText(hasExactText("Diamond ×1"))).toBeInTheDocument();
    expect(screen.getByText(hasExactText("Top 10 ×12"))).toBeInTheDocument();
    expect(screen.getByText(hasExactText("Top 500 ×34"))).toBeInTheDocument();
    expect(screen.queryByText(/Origin/)).not.toBeInTheDocument();
  });

  it("includes origin when it differs from the current page filter", () => {
    const player = {
      splashtag: "あ#1142c",
      prev_season_region: true,
      diamond_x_count: 0,
      gold_x_count: 9,
      silver_x_count: 32,
    };

    render(
      renderSplashtag(player, t, {
        selectedRegion: "Tentatek",
      })
    );

    expect(screen.getByText(hasExactText("Origin Takoroka"))).toBeInTheDocument();
  });
});
