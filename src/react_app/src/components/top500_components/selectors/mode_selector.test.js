import React from "react";
import { render, screen } from "@testing-library/react";
import ModeSelector, { getAutoFitEqualWidthColumnCount } from "./mode_selector";

jest.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key, options) => options?.defaultValue || key,
  }),
}));

jest.mock("../../../assets/icons/splat_zones.png", () => "sz.png");
jest.mock("../../../assets/icons/tower_control.png", () => "tc.png");
jest.mock("../../../assets/icons/rainmaker.png", () => "rm.png");
jest.mock("../../../assets/icons/clam_blitz.png", () => "cb.png");
jest.mock("../../../assets/icons/all_modes.png", () => "all.png");

describe("ModeSelector", () => {
  it("supports equal-width utility buttons for localized labels", () => {
    const { container } = render(
      <ModeSelector
        selectedMode="Rainmaker"
        setSelectedMode={() => {}}
        showTitle={false}
        showLabels={true}
        buttonVariant="utility"
        equalWidthButtons={true}
      />
    );

    const buttonGrid = container.querySelector(".grid.grid-cols-2");
    expect(buttonGrid).toBeTruthy();

    const buttons = screen.getAllByRole("button");
    expect(buttons).toHaveLength(4);
    buttons.forEach((button) => {
      expect(button.className).toContain("w-full");
      expect(button.className).toContain("min-h-[3.5rem]");
    });
  });

  it("supports a balanced responsive grid for four labeled modes", () => {
    expect(
      getAutoFitEqualWidthColumnCount({
        buttonCount: 4,
        containerWidth: 720,
        contentWidths: [102, 118, 134, 120],
        chromeWidth: 26,
      })
    ).toBe(4);

    expect(
      getAutoFitEqualWidthColumnCount({
        buttonCount: 4,
        containerWidth: 560,
        contentWidths: [102, 118, 134, 120],
        chromeWidth: 26,
      })
    ).toBe(2);

    expect(
      getAutoFitEqualWidthColumnCount({
        buttonCount: 5,
        containerWidth: 900,
        contentWidths: [80, 80, 80, 80, 80],
        chromeWidth: 26,
      })
    ).toBe(2);
  });

  it("starts from a balanced two-column grid when auto-fit is enabled", () => {
    const { container } = render(
      <ModeSelector
        selectedMode="Rainmaker"
        setSelectedMode={() => {}}
        showTitle={false}
        showLabels={true}
        buttonVariant="utility"
        equalWidthButtons={true}
        autoFitEqualWidth={true}
      />
    );

    const buttonGrid = container.querySelector(".grid.grid-cols-2");
    expect(buttonGrid).toBeTruthy();
  });
});
