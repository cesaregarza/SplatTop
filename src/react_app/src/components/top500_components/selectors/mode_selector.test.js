import React from "react";
import { render, screen } from "@testing-library/react";
import ModeSelector from "./mode_selector";

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
    });
  });
});
