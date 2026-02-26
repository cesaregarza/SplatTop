import React, { Suspense, useEffect, useState } from "react";
import "./App.css";
import Navbar from "./components/navbar";
import Footer from "./components/footer";
import { BrowserRouter as Router, Route, Routes } from "react-router-dom";
import CompetitionApp from "./components/competition/CompetitionApp";

const Top500 = React.lazy(() => import("./components/top500"));
const FAQ = React.lazy(() => import("./components/static_pages/faq"));
const About = React.lazy(() => import("./components/static_pages/about"));
const PlayerDetail = React.lazy(() => import("./components/player_detail"));
const Analytics = React.lazy(() => import("./components/analytics"));
const TopWeapons = React.lazy(() =>
  import("./components/weapon_leaderboard")
);

const COMPETITION_OVERRIDE_KEY = "splat.top.competitionOverride";
const DEFAULT_FAVICON_HREF = "/favicon.ico?v=1";
const DEFAULT_FAVICON_TYPE = "image/x-icon";
const COMPETITION_FAVICON_HREF = "/favicon-comp.svg?v=1";
const COMPETITION_FAVICON_TYPE = "image/svg+xml";

const readBoolean = (value) => {
  if (value == null) return null;
  const normalized = String(value).trim().toLowerCase();
  if (normalized === "true" || normalized === "1") return true;
  if (normalized === "false" || normalized === "0") return false;
  return null;
};

const isCompetitionHostname = () => {
  if (typeof window === "undefined") {
    return false;
  }

  const hostname = window.location.hostname.toLowerCase();
  return hostname === "comp.localhost" || hostname.startsWith("comp.");
};

const detectCompetitionHost = () => {
  const explicitFlag = readBoolean(process.env.REACT_APP_ENABLE_COMPETITION);
  if (explicitFlag !== null) return explicitFlag;

  if (typeof window !== "undefined") {
    try {
      const params = new URLSearchParams(window.location.search);
      const overrideParam = readBoolean(params.get("competition"));
      if (overrideParam !== null) return overrideParam;

      const stored = readBoolean(
        window.localStorage?.getItem(COMPETITION_OVERRIDE_KEY)
      );
      if (stored !== null) return stored;
    } catch {}
  }

  if (typeof window === "undefined") {
    return false;
  }
  return isCompetitionHostname();
};

const setFaviconForMode = (isCompetition) => {
  if (typeof document === "undefined") {
    return;
  }

  let favicon = document.querySelector('link[rel="icon"]');
  if (!favicon) {
    favicon = document.createElement("link");
    favicon.setAttribute("rel", "icon");
    document.head.appendChild(favicon);
  }

  favicon.setAttribute(
    "href",
    isCompetition ? COMPETITION_FAVICON_HREF : DEFAULT_FAVICON_HREF
  );
  favicon.setAttribute(
    "type",
    isCompetition ? COMPETITION_FAVICON_TYPE : DEFAULT_FAVICON_TYPE
  );
};

const MainSiteApp = () => (
  <Router>
    <div className="dark bg-gray-900 text-white min-h-screen">
      <Navbar />
      <Suspense fallback={<div>Loading...</div>}>
        <Routes>
          <Route exact path="/" element={<Top500 />} />
          <Route exact path="/faq" element={<FAQ />} />
          <Route exact path="/about" element={<About />} />
          <Route path="/player/:player_id" element={<PlayerDetail />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/top_weapons" element={<TopWeapons />} />
        </Routes>
      </Suspense>
      <Footer />
    </div>
  </Router>
);

const App = () => {
  const [isCompetition, setIsCompetition] = useState(() =>
    detectCompetitionHost()
  );

  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const override = readBoolean(params.get("competition"));
      if (override !== null) {
        try {
          window.localStorage?.setItem(
            COMPETITION_OVERRIDE_KEY,
            override ? "true" : "false"
          );
        } catch {}
      }
    }

    const competitionEnabled = detectCompetitionHost();
    setIsCompetition(competitionEnabled);
    setFaviconForMode(isCompetitionHostname());
  }, []);

  if (isCompetition) {
    return <CompetitionApp />;
  }

  return <MainSiteApp />;
};

export default App;
