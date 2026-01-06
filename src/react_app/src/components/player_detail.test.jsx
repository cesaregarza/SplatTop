import React from "react";
import { render, waitFor } from "@testing-library/react";
import axios from "axios";

import PlayerDetail from "./player_detail";

let mockPathname = "/player/player1";

jest.mock("react-router-dom", () => ({
  ...jest.requireActual("react-router-dom"),
  useLocation: () => ({ pathname: mockPathname }),
}));

const t = (key) => key;

jest.mock("react-i18next", () => ({
  useTranslation: () => ({ t }),
}));

jest.mock("./utils/weaponAndTranslation", () => ({
  WeaponAndTranslationProvider: ({ children }) => <>{children}</>,
  useWeaponAndTranslation: () => ({
    weaponTranslations: {},
    weaponReferenceData: {},
    isLoading: false,
    error: null,
  }),
}));

jest.mock("axios");

class MockWebSocket {
  static instances = [];
  constructor(url) {
    this.url = url;
    this.close = jest.fn();
    MockWebSocket.instances.push(this);
  }
}

describe("PlayerDetail WebSocket cleanup", () => {
  beforeEach(() => {
    MockWebSocket.instances = [];
    global.WebSocket = MockWebSocket;
    axios.get.mockResolvedValue({ data: [{ splashtag: "Tester" }] });
    mockPathname = "/player/player1";
  });

  it("closes old WebSocket when player_id changes", async () => {
    const { rerender } = render(<PlayerDetail />);

    await waitFor(() => expect(MockWebSocket.instances).toHaveLength(1));
    const firstSocket = MockWebSocket.instances[0];

    mockPathname = "/player/player2";
    rerender(<PlayerDetail />);

    await waitFor(() => expect(MockWebSocket.instances).toHaveLength(2));
    expect(firstSocket.close).toHaveBeenCalled();
  });

  it("closes WebSocket on unmount", async () => {
    const { unmount } = render(<PlayerDetail />);

    await waitFor(() => expect(MockWebSocket.instances).toHaveLength(1));
    const socket = MockWebSocket.instances[0];

    unmount();

    expect(socket.close).toHaveBeenCalled();
  });
});
