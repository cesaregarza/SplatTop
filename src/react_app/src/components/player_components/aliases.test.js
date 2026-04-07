import React from "react";
import { render, screen, within } from "@testing-library/react";
import Aliases from "./aliases";

jest.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key) =>
      ({
        "aliases.title": "Aliases",
        "aliases.splashtag": "Splashtag",
        "aliases.last_seen": "Last Seen",
        "aliases.current": "Latest",
      })[key] || key,
  }),
}));

describe("Aliases", () => {
  it("sorts aliases by last seen and highlights the latest entry", () => {
    render(
      <Aliases
        data={[
          {
            splashtag: "Older#1111",
            latest_updated_timestamp: "2024-01-01T00:00:00.000Z",
          },
          {
            splashtag: "FreshName",
            latest_updated_timestamp: "2024-04-01T00:00:00.000Z",
          },
        ]}
      />
    );

    const rows = screen.getAllByRole("row");

    expect(within(rows[1]).getByText("FreshName")).toBeInTheDocument();
    expect(within(rows[1]).getByText("Latest")).toBeInTheDocument();
    expect(screen.getByText("Older")).toBeInTheDocument();
    expect(screen.getByText("#1111")).toBeInTheDocument();
  });
});
