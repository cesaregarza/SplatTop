import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react-swc";
import tailwindcss from "@tailwindcss/vite";

const exposedReactEnvKeys = [
  "REACT_APP_ENABLE_COMPETITION",
  "REACT_APP_MAIN_SITE_URL",
  "REACT_APP_SHOWCASE_STABLE_LEADERBOARD",
  "REACT_APP_VERSION",
];

export default defineConfig(({ mode }) => {
  const fileEnv = loadEnv(mode, process.cwd(), "");
  const reactEnv = Object.fromEntries(
    exposedReactEnvKeys.map((key) => [key, process.env[key] ?? fileEnv[key] ?? ""])
  );

  return {
    server: {
      port: 3000,
      strictPort: true,
    },
    plugins: [
      react({ include: /\.(js|jsx|ts|tsx)$/ }),
      tailwindcss(),
    ],
    define: {
      "process.env": JSON.stringify({
        NODE_ENV: mode,
        ...reactEnv,
      }),
    },
    build: {
      outDir: "build",
      target: "baseline-widely-available",
    },
  };
});
