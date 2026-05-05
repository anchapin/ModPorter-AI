import React, { useEffect, useState } from 'react';
import './StatusPage.css';

interface ComponentStatus {
  name: string;
  status: 'operational' | 'degraded' | 'partial_outage' | 'major_outage' | 'maintenance';
  latency_ms?: number;
  lastChecked: string;
  description: string;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL
  ? import.meta.env.VITE_API_BASE_URL + '/api/v1'
  : import.meta.env.VITE_API_URL
    ? import.meta.env.VITE_API_URL.replace(/\/api\/v1$/, '') + '/api/v1'
    : '/api/v1';

const StatusPage: React.FC = () => {
  const [components, setComponents] = useState<ComponentStatus[]>([]);
  const [overallStatus, setOverallStatus] = useState<string>('checking');
  const [lastUpdated, setLastUpdated] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);

  const fetchStatus = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/health/readiness`);
      const data = await response.json();

      const dependencies = data.checks?.dependencies || {};
      const now = new Date().toISOString();

      const componentList: ComponentStatus[] = [
        {
          name: 'Web App',
          status: response.ok ? 'operational' : 'major_outage',
          lastChecked: now,
          description: 'Frontend application and static assets',
        },
        {
          name: 'API',
          status: response.ok ? 'operational' : 'major_outage',
          lastChecked: now,
          description: 'REST API endpoints and authentication',
        },
        {
          name: 'Conversion Queue',
          status: dependencies.redis?.status === 'healthy' ? 'operational' : 'degraded',
          latency_ms: dependencies.redis?.latency_ms,
          lastChecked: now,
          description: 'Background job processing and AI conversion',
        },
        {
          name: 'Database',
          status: dependencies.database?.status === 'healthy' ? 'operational' : 'major_outage',
          latency_ms: dependencies.database?.latency_ms,
          lastChecked: now,
          description: 'PostgreSQL database for user data and conversions',
        },
      ];

      setComponents(componentList);

      const hasOutage = componentList.some(c =>
        c.status === 'major_outage' || c.status === 'partial_outage'
      );
      const hasDegraded = componentList.some(c => c.status === 'degraded');

      if (hasOutage) {
        setOverallStatus('major_outage');
      } else if (hasDegraded) {
        setOverallStatus('degraded');
      } else {
        setOverallStatus('operational');
      }

      setLastUpdated(now);
    } catch {
      setOverallStatus('major_outage');
      setComponents([
        {
          name: 'Web App',
          status: 'major_outage',
          lastChecked: new Date().toISOString(),
          description: 'Unable to reach status API',
        },
        {
          name: 'API',
          status: 'major_outage',
          lastChecked: new Date().toISOString(),
          description: 'REST API endpoints unavailable',
        },
        {
          name: 'Conversion Queue',
          status: 'maintenance',
          lastChecked: new Date().toISOString(),
          description: 'Status unknown',
        },
        {
          name: 'Database',
          status: 'maintenance',
          lastChecked: new Date().toISOString(),
          description: 'Status unknown',
        },
      ]);
    }
    setIsLoading(false);
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'operational':
        return '✓';
      case 'degraded':
        return '⚠';
      case 'partial_outage':
        return '◐';
      case 'major_outage':
        return '✕';
      case 'maintenance':
        return '🔧';
      default:
        return '?';
    }
  };

  const getStatusClass = (status: string) => {
    switch (status) {
      case 'operational':
        return 'status-operational';
      case 'degraded':
        return 'status-degraded';
      case 'partial_outage':
        return 'status-partial';
      case 'major_outage':
        return 'status-outage';
      case 'maintenance':
        return 'status-maintenance';
      default:
        return '';
    }
  };

  const getOverallStatusText = () => {
    switch (overallStatus) {
      case 'operational':
        return 'All Systems Operational';
      case 'degraded':
        return 'Degraded Performance';
      case 'major_outage':
        return 'Major Outage';
      case 'partial_outage':
        return 'Partial Outage';
      case 'maintenance':
        return 'Under Maintenance';
      default:
        return 'Checking Status...';
    }
  };

  const getOverallStatusClass = () => {
    switch (overallStatus) {
      case 'operational':
        return 'overall-operational';
      case 'degraded':
        return 'overall-degraded';
      case 'major_outage':
        return 'overall-outage';
      case 'partial_outage':
        return 'overall-partial';
      case 'maintenance':
        return 'overall-maintenance';
      default:
        return 'overall-checking';
    }
  };

  return (
    <div className="status-page">
      <div className="status-container">
        <div className="status-header">
          <div className="status-logo">
            <span className="logo-icon">🎮</span>
            <span className="logo-text">Portkit</span>
          </div>
          <div className={`status-indicator ${getOverallStatusClass()}`}>
            <span className="status-dot"></span>
            <span className="status-text">{getOverallStatusText()}</span>
          </div>
        </div>

        <div className="status-hero">
          <h1>System Status</h1>
          <p>Real-time status for Portkit services</p>
          {!isLoading && lastUpdated && (
            <p className="last-updated">
              Last checked: {new Date(lastUpdated).toLocaleString()}
            </p>
          )}
        </div>

        <div className="components-grid">
          {components.map((component, index) => (
            <div key={index} className={`component-card ${getStatusClass(component.status)}`}>
              <div className="component-header">
                <span className="component-status-icon">{getStatusIcon(component.status)}</span>
                <h3 className="component-name">{component.name}</h3>
              </div>
              <p className="component-description">{component.description}</p>
              <div className="component-meta">
                {component.latency_ms !== undefined && (
                  <span className="component-latency">
                    Latency: {Math.round(component.latency_ms)}ms
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>

        <div className="status-footer">
          <p>
            Having issues?{' '}
            <a
              href="https://discord.gg/modporter"
              target="_blank"
              rel="noopener noreferrer"
            >
              Report on Discord
            </a>
          </p>
          <p className="status-page-link">
            <a href="/">← Back to Portkit</a>
          </p>
        </div>
      </div>
    </div>
  );
};

export default StatusPage;