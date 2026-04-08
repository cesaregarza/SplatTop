import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { CompetitionAuthProvider } from "./CompetitionAuth";
import CompetitionLayout from "./CompetitionLayout";

const makeJsonResponse = (data, status = 200) => ({
  ok: status >= 200 && status < 300,
  status,
  json: jest.fn().mockResolvedValue(data),
});

const renderWithAuth = (layoutProps = {}) => render(
  <MemoryRouter>
    <CompetitionAuthProvider>
      <CompetitionLayout
        generatedAtMs={1_700_000_010_000}
        stale={false}
        loading={false}
        faqLinkHref="/faq"
        vizLinkHref="/learn"
        top500Href="/top500"
        {...layoutProps}
      >
        <div>competition content</div>
      </CompetitionLayout>
    </CompetitionAuthProvider>
  </MemoryRouter>
);

describe("Competition auth UI", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  afterEach(() => {
    delete global.fetch;
  });

  it("renders the Discord login CTA when the session is unauthenticated", async () => {
    global.fetch = jest.fn().mockResolvedValue(
      makeJsonResponse({
        available: true,
        authenticated: false,
        is_admin: false,
        discord_id: null,
      })
    );

    renderWithAuth();

    const loginLink = await screen.findByRole("link", {
      name: /log in with discord/i,
    });

    expect(loginLink).toBeInTheDocument();
    expect(loginLink.getAttribute("href")).toContain(
      "/api/comp-auth/discord/login"
    );
    expect(global.fetch).toHaveBeenCalledWith(
      "/api/comp-auth/me",
      expect.objectContaining({
        credentials: "include",
      })
    );
  });

  it("renders the Discord ID and clears back to login after logout", async () => {
    global.fetch = jest.fn()
      .mockResolvedValueOnce(
        makeJsonResponse({
          available: true,
          authenticated: true,
          is_admin: true,
          discord_id: "123456789",
        })
      )
      .mockResolvedValueOnce(
        makeJsonResponse({
          available: true,
          authenticated: false,
          is_admin: false,
          discord_id: null,
        })
      );

    renderWithAuth();

    await screen.findByText("123456789");
    expect(screen.getByText("Admin")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /log out/i }));

    await waitFor(() => {
      expect(
        screen.getByRole("link", { name: /log in with discord/i })
      ).toBeInTheDocument();
    });

    expect(global.fetch).toHaveBeenNthCalledWith(
      2,
      "/api/comp-auth/logout",
      expect.objectContaining({
        method: "POST",
        credentials: "include",
      })
    );
  });

  it("hides the login CTA when Discord auth is not configured", async () => {
    global.fetch = jest.fn().mockResolvedValue(
      makeJsonResponse({
        available: false,
        authenticated: false,
        is_admin: false,
        discord_id: null,
      })
    );

    renderWithAuth();

    await screen.findByText("Discord login unavailable");
    expect(
      screen.queryByRole("link", { name: /log in with discord/i })
    ).not.toBeInTheDocument();
  });

  it("runs a blocking backend snapshot refresh for admins before revalidating", async () => {
    const onRefresh = jest.fn();
    global.fetch = jest.fn()
      .mockResolvedValueOnce(
        makeJsonResponse({
          available: true,
          authenticated: true,
          is_admin: true,
          discord_id: "123456789",
        })
      )
      .mockResolvedValueOnce(
        makeJsonResponse({
          queued: false,
          completed: true,
          task_name: "tasks.refresh_ripple_snapshots",
          result: { refreshed: true },
        })
      );

    renderWithAuth({ onRefresh });

    await screen.findByText("123456789");

    fireEvent.click(screen.getByRole("button", { name: /refresh now/i }));

    await waitFor(() => {
      expect(global.fetch).toHaveBeenNthCalledWith(
        2,
        "/api/ripple/admin/refresh?wait=true",
        expect.objectContaining({
          method: "POST",
          credentials: "include",
        })
      );
      expect(onRefresh).toHaveBeenCalledTimes(1);
    });

    expect(screen.getByText("Snapshot refreshed.")).toBeInTheDocument();
  });
});
