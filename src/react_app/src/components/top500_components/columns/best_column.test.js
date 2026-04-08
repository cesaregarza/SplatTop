import React from "react";
import { render, screen } from "@testing-library/react";
import { render as renderBest } from "./best_column";

const t = (key) => {
  const labels = {
    "best.all_mode_top10": "All-mode T10",
    "best.top10": "Top 10",
    "best.top500": "Top 500",
  };

  return labels[key] || key;
};

describe("best column", () => {
  it("renders the strongest recorded tier for a player", () => {
    render(
      renderBest(
        {
          diamond_x_count: 1,
          gold_x_count: 9,
          silver_x_count: 32,
        },
        t
      )
    );

    expect(screen.getByText("All-mode T10")).toBeInTheDocument();
  });

  it("falls back through top 10 and top 500 tiers", () => {
    const { rerender } = render(
      renderBest(
        {
          diamond_x_count: 0,
          gold_x_count: 4,
          silver_x_count: 18,
        },
        t
      )
    );
    expect(screen.getByText("Top 10")).toBeInTheDocument();

    rerender(
      renderBest(
        {
          diamond_x_count: 0,
          gold_x_count: 0,
          silver_x_count: 2,
        },
        t
      )
    );
    expect(screen.getByText("Top 500")).toBeInTheDocument();
  });
});
