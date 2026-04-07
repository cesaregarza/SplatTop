import React from "react";
import { render, screen, within } from "@testing-library/react";
import WeaponsChart from "./weapons";

jest.mock("react-i18next", () => ({
  useTranslation: (ns) => ({
    t: (key) =>
      ({
        player: {
          "weaponchart.title": "%MODE% Weapon Usage",
          "weaponchart.subtitle": "All weapon data is approximate",
          "weaponchart.other": "Other",
          "weaponchart.inner.title": "Total Weapon Usage",
          "weaponchart.outer.title": "Detailed Weapon Usage",
          "weaponchart.point.format":
            "<span>{point.name}</span>: <b>{point.y:.2f}%</b>",
          no_data: "No data available",
        },
        game: {
          rm: "Rainmaker",
        },
      })[ns]?.[key] || key,
  }),
}));

jest.mock("highcharts-react-official", () => () => (
  <div data-testid="highcharts-react" />
));

jest.mock("highcharts", () => ({}));

jest.mock("highcharts/modules/drilldown", () => () => () => null);

jest.mock("chroma-js", () => ({
  __esModule: true,
  default: {
    lab: (...args) => ({
      hex: () =>
        typeof args[0] === "string"
          ? args[0]
          : `#${(Math.abs(Math.round((args[0] || 0) * 1000)) % 0xffffff)
              .toString(16)
              .padStart(6, "0")}`,
      lab: () => (Array.isArray(args[0]) ? args[0] : args),
    }),
  },
}));

describe("WeaponsChart", () => {
  it("renders a sorted side legend for weapon usage", () => {
    render(
      <WeaponsChart
        data={{
          weapon_winrate: [
            { mode: "Rainmaker", weapon_id: 1, total_count: 40, sum: 20 },
            { mode: "Rainmaker", weapon_id: 2, total_count: 30, sum: 15 },
            { mode: "Rainmaker", weapon_id: 3, total_count: 20, sum: 10 },
          ],
        }}
        mode="Rainmaker"
        weaponTranslations={{
          WeaponName_Main: {
            Shooter_Base: "Splattershot",
            Shooter_Neo: "Sploosh-o-matic",
            Roller_Base: "Carbon Roller",
          },
          WeaponTypeName: {
            Shooter: "Shooter",
            Roller: "Roller",
          },
        }}
        weaponReferenceData={{
          1: { class: "Shooter", kit: "Base", reference_kit: "Base" },
          2: { class: "Shooter", kit: "Neo", reference_kit: "Neo" },
          3: { class: "Roller", kit: "Base", reference_kit: "Base" },
        }}
      />
    );

    expect(screen.getByTestId("highcharts-react")).toBeInTheDocument();

    const legend = screen
      .getByRole("heading", { name: "Detailed Weapon Usage" })
      .closest("aside");
    const rows = within(legend)
      .getAllByText(/%$/)
      .map((entry) => entry.closest("div").textContent);

    expect(rows[0]).toContain("Splattershot");
    expect(rows[0]).toContain("44.4%");
    expect(rows[1]).toContain("Sploosh-o-matic");
    expect(rows[1]).toContain("33.3%");
    expect(rows[2]).toContain("Carbon Roller");
    expect(rows[2]).toContain("22.2%");
  });
});
