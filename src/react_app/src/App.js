import React from 'react';
import './App.css';
import Top500 from './components/top500';
import Navbar from './components/navbar';
import FAQ from './components/faq';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';

const App = () => {
  return (
    <Router>
      <div className="dark bg-gray-900 text-white min-h-screen">
        <Navbar />
        <Routes>
          <Route exact path="/" element={<Top500 />} />
          <Route exact path="/faq" element={<FAQ />} />
          {/* Add more routes for other components */}
        </Routes>
      </div>
    </Router>
  );
};

export default App;