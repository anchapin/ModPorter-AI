import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import './TopNavigation.css';

interface TopNavigationProps {
  className?: string;
}

export const TopNavigation: React.FC<TopNavigationProps> = ({ className = '' }) => {
  const location = useLocation();

  const isActive = (path: string) => {
    if (path === '/') {
      return location.pathname === '/';
    }
    return location.pathname.startsWith(path);
  };

  return (
    <header className={`top-navigation ${className}`}>
      <nav className="top-navigation__nav">
        <Link to="/" className="top-navigation__logo">
          ModPorter AI
        </Link>
        
        <div className="top-navigation__links">
          <Link 
            to="/" 
            className={`top-navigation__link ${isActive('/') ? 'top-navigation__link--active' : ''}`}
          >
            Convert
          </Link>
          
          <Link 
            to="/comparison" 
            className={`top-navigation__link ${isActive('/comparison') ? 'top-navigation__link--active' : ''}`}
          >
            Comparison
          </Link>
          
          <Link 
            to="/behavioral-test" 
            className={`top-navigation__link ${isActive('/behavioral-test') ? 'top-navigation__link--active' : ''}`}
          >
            Behavioral Test
          </Link>
          
          <Link 
            to="/docs" 
            className={`top-navigation__link ${isActive('/docs') ? 'top-navigation__link--active' : ''}`}
          >
            Documentation
          </Link>
        </div>
      </nav>
    </header>
  );
};

export default TopNavigation;