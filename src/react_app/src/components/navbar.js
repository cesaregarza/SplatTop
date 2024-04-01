import React, { useState } from 'react';

const Navbar = () => {
  const [isActive, setIsActive] = useState(false);

  const toggleNavbar = () => {
    setIsActive(!isActive);
  };

  return (
    <header className="content">
      <nav className="navbar is-fixed-top" role="navigation" aria-label="main navigation">
        <div className="navbar-brand">
          <a href="/" className="navbar-item">splat.top Top 500</a>
          <a
            role="button"
            className={`navbar-burger ${isActive ? 'is-active' : ''}`}
            aria-label="menu"
            aria-expanded="false"
            onClick={toggleNavbar}
          >
            <span aria-hidden="true"></span>
            <span aria-hidden="true"></span>
            <span aria-hidden="true"></span>
          </a>
        </div>
        <div id="navbarMenu" className={`navbar-menu ${isActive ? 'is-active' : ''}`}>
          <div className="navbar-start">
            <a href="/faq" className="navbar-item">FAQ</a>
            <a href="/search" className="navbar-item">Search</a>
          </div>
        </div>
      </nav>
    </header>
  );
};

export default Navbar;
