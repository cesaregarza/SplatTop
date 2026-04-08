import React from "react";
import { render, screen } from "@testing-library/react";
import RegionSelector from "./region_selector";

jest.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key) => key,
  }),
}));

jest.mock("../../../assets/icons/takoroka.png", () => "takoroka.png");
jest.mock("../../../assets/icons/tentatek.png", () => "tentatek.png");

describe("RegionSelector", () => {
  it("supports utility buttons with labels", () => {
    render(
      <RegionSelector
        selectedRegion="Takoroka"
        setSelectedRegion={() => {}}
        showTitle={false}
        showLabels={true}
        buttonVariant="utility"
        buttonPadding="px-3 py-2"
        imageWidth="w-8"
        imageHeight="h-8"
        baseClass="w-full"
      />
    );

    const takorokaButton = screen.getByRole("button", { name: "Takoroka" });
    const tentatekButton = screen.getByRole("button", { name: "Tentatek" });

    expect(takorokaButton.className).toContain("border-purple-500/60");
    expect(tentatekButton.className).toContain("border-gray-800");
    expect(screen.getByText("Takoroka")).toBeInTheDocument();
    expect(screen.getByText("Tentatek")).toBeInTheDocument();
  });
});
