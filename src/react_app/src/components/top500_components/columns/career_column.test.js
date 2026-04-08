import React from "react";
import { render, screen } from "@testing-library/react";
import { render as renderCareer } from "./career_column";

const t = (key) => {
  const labels = {
    "career.all_mode_top10_season": "all-mode T10 season",
    "career.all_mode_top10_seasons": "all-mode T10 seasons",
    "career.top10": "Top 10",
    "career.top500": "Top 500",
  };

  return labels[key] || key;
};

describe("career column", () => {
  const hasExactText = (text) => (_, node) => node?.textContent === text;

  it("renders plain-text career counts on one line", () => {
    render(
      renderCareer(
        {
          diamond_x_count: 1,
          gold_x_count: 12,
          silver_x_count: 34,
        },
        t
      )
    );

    expect(
      screen.getByText(hasExactText("1 all-mode T10 season"))
    ).toBeInTheDocument();
    expect(screen.getByText(hasExactText("12 Top 10"))).toBeInTheDocument();
    expect(screen.getByText(hasExactText("34 Top 500"))).toBeInTheDocument();
  });

  it("renders a dash when no career counts exist", () => {
    render(
      renderCareer(
        {
          diamond_x_count: 0,
          gold_x_count: 0,
          silver_x_count: 0,
        },
        t
      )
    );

    expect(screen.getByText("—")).toBeInTheDocument();
  });
});
