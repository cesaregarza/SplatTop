import React from "react";
import { render, screen } from "@testing-library/react";
import Achievements from "./achievements";

jest.mock("react-i18next", () => ({
  useTranslation: (ns) => ({
    t: (key) =>
      (
        {
          player: {
            "highlights.title": "Career Highlights",
            "highlights.subtitle": "Best finishes and notable seasons.",
            "highlights.metrics.top10": "Top 10",
            "highlights.metrics.top500": "Top 500",
            "highlights.metrics.diamonds": "Diamonds",
            "highlights.metrics.best_finish": "Best Finish",
            "highlights.metrics.best_mode": "Best Mode",
            "highlights.notable_title": "Notable Seasons",
            "highlights.no_notable": "No Top 500 seasons yet.",
          },
          game: {
            sz: "Splat Zones",
            tc: "Tower Control",
            rm: "Rainmaker",
            cb: "Clam Blitz",
            spring: "Fresh",
            summer: "Sizzle",
            autumn: "Drizzle",
            winter: "Chill",
            format_short: "%SEASON% %YEAR%",
          },
        }
      )[ns]?.[key] || key,
  }),
}));

describe("Achievements", () => {
  it("renders compact career highlights and notable seasons", () => {
    render(
      <Achievements
        data={{
          aggregated_data: {
            season_results: [
              {
                season_number: 8,
                region: true,
                mode: "Splat Zones",
                rank: 1,
              },
              {
                season_number: 8,
                region: true,
                mode: "Tower Control",
                rank: 21,
              },
              {
                season_number: 7,
                region: false,
                mode: "Splat Zones",
                rank: 5,
              },
              {
                season_number: 7,
                region: false,
                mode: "Tower Control",
                rank: 7,
              },
              {
                season_number: 7,
                region: false,
                mode: "Rainmaker",
                rank: 8,
              },
              {
                season_number: 7,
                region: false,
                mode: "Clam Blitz",
                rank: 9,
              },
            ],
          },
        }}
      />
    );

    expect(screen.getByText("Career Highlights")).toBeInTheDocument();
    expect(
      screen.getByText("Best finishes and notable seasons.")
    ).toBeInTheDocument();
    expect(screen.getByText("Top 10")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByText("Top 500")).toBeInTheDocument();
    expect(screen.getByText("6")).toBeInTheDocument();
    expect(screen.getByText("Diamonds")).toBeInTheDocument();
    expect(screen.getByText("1")).toBeInTheDocument();
    expect(screen.getByText("Best Finish")).toBeInTheDocument();
    expect(screen.getByText("#1")).toBeInTheDocument();
    expect(screen.getByText("Best Mode")).toBeInTheDocument();
    expect(screen.getByText("Splat Zones")).toBeInTheDocument();
    expect(screen.getByText("SZ #1 · TC #21")).toBeInTheDocument();
  });
});
