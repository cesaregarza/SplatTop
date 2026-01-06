import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import axios from "axios";

import SearchBar from "./searchbar";

jest.mock("axios");

jest.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key) => key }),
}));

describe("Searchbar", () => {
  afterEach(() => {
    jest.useRealTimers();
  });

  it("debounces API calls on rapid typing", async () => {
    jest.useFakeTimers();
    axios.get.mockResolvedValue({ data: [] });
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });

    render(<SearchBar />);
    const input = screen.getByRole("textbox");

    await user.type(input, "test");

    expect(axios.get).not.toHaveBeenCalled();

    jest.advanceTimersByTime(400);

    await waitFor(() => {
      expect(axios.get).toHaveBeenCalledTimes(1);
    });

    jest.useRealTimers();
  });
});
