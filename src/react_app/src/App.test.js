import { render } from "@testing-library/react";
import App from "./App";

jest.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key) => key,
    i18n: {
      language: "en",
      changeLanguage: () => Promise.resolve(),
    },
  }),
}));

test("renders without crashing", () => {
  const { container } = render(<App />);
  expect(container).toBeTruthy();
});
