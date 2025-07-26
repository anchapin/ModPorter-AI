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

  const navigationLinks = [
    { to: '/', label: 'Convert' },
    { to: '/comparison', label: 'Comparison' },
    { to: '/behavioral-test', label: 'Behavioral Test' },
    { to: '/docs', label: 'Documentation' }
  ];

  return (
    <header className={`top-navigation ${className}`}>
      <nav className="top-navigation__nav">
        <Link to="/" className="top-navigation__logo">
          ModPorter AI
        </Link>
        
        <div className="top-navigation__links">
          {navigationLinks.map(({ to, label }) => (
            <Link 
              key={to}
              to={to} 
              className={`top-navigation__link ${isActive(to) ? 'top-navigation__link--active' : ''}`}
            >
              {label}
            </Link>
          ))}
        </div>
      </nav>
    </header>
  );
};

export default TopNavigation;