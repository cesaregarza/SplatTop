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

const detectCompetitionHost = () => {
  if (typeof window === "undefined") {
    return false;
  }
  const hostname = window.location.hostname.toLowerCase();
  if (hostname === "comp.localhost") {
    return true;
  }
  return hostname.startsWith("comp.");
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
  const [isCompetition, setIsCompetition] = useState(detectCompetitionHost);

  useEffect(() => {
    setIsCompetition(detectCompetitionHost());
  }, []);

  if (isCompetition) {
    return <CompetitionApp />;
  }

  return <MainSiteApp />;
};

export default App;
