import { render, screen } from "@testing-library/react";
import App from "./App";

jest.mock("./components/navbar", () => () => <div>Navbar</div>);
jest.mock("./components/footer", () => () => <div>Footer</div>);
jest.mock("./components/top500", () => () => <div>Top 500</div>);
jest.mock("./components/static_pages/faq", () => () => <div>FAQ</div>);
jest.mock("./components/static_pages/about", () => () => <div>About</div>);
jest.mock("./components/static_pages/legacy_leaderboards", () => () => (
  <h1>Legacy leaderboards</h1>
));
jest.mock("./components/player_detail", () => () => <div>Player detail</div>);
jest.mock("./components/analytics", () => () => <div>Analytics</div>);
jest.mock("./components/weapon_leaderboard", () => () => (
  <div>Top Weapons</div>
));
jest.mock("./components/competition/CompetitionApp", () => () => (
  <div>Competition</div>
));

jest.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key) => key,
    i18n: {
      language: "en",
      changeLanguage: () => Promise.resolve(),
    },
  }),
}));

beforeEach(() => {
  window.history.pushState({}, "", "/");
});

test("renders without crashing", () => {
  const { container } = render(<App />);
  expect(container).toBeTruthy();
});

test("renders the legacy leaderboards route", async () => {
  window.history.pushState({}, "", "/legacy");
  render(<App />);
  expect(
    await screen.findByRole("heading", { name: /legacy leaderboards/i })
  ).toBeInTheDocument();
});
