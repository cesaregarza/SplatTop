import React, { Suspense } from "react";
import "./App.css";
import Navbar from "./components/navbar";
import Footer from "./components/footer";
import { BrowserRouter as Router, Route, Routes } from "react-router-dom";

const Top500 = React.lazy(() => import("./components/top500"));
const FAQ = React.lazy(() => import("./components/static_pages/faq"));
const About = React.lazy(() => import("./components/static_pages/about"));
const PlayerDetail = React.lazy(() => import("./components/player_detail"));
const Analytics = React.lazy(() => import("./components/analytics"));

const App = () => {
  return (
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
          </Routes>
        </Suspense>
        <Footer />
      </div>
    </Router>
  );
};

export default App;
