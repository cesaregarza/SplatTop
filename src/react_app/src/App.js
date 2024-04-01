import React from 'react';
import './App.css';
import Top500 from './components/top500';
import Navbar from './components/navbar';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';

const App = () => {
  return (
    <Router>
      <div>
        <Navbar />
        <Routes>
          <Route exact path="/" element={<Top500 />} />
          {/* Add more routes for other components */}
        </Routes>
      </div>
    </Router>
  );
};

export default App;