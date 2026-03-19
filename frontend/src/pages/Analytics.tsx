/**
 * Analytics Dashboard Page
 * Provides comprehensive analytics and metrics for the beta launch
 */

import React, { useState, useEffect, useCallback } from 'react';
import { 
  fetchDashboardAnalytics, 
  ConversionStats, 
  UserStats, 
  ErrorStats, 
  PerformanceMetrics 
} from '../services/analytics-dashboard';
import './Analytics.css';

type TimeRange = 7 | 14 | 30;

export const Analytics: React.FC = () => {
  const [timeRange, setTimeRange] = useState<TimeRange>(7);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  
  const [conversionStats, setConversionStats] = useState<ConversionStats | null>(null);
  const [userStats, setUserStats] = useState<UserStats | null>(null);
  const [errorStats, setErrorStats] = useState<ErrorStats | null>(null);
  const [performanceMetrics, setPerformanceMetrics] = useState<PerformanceMetrics | null>(null);

  const loadAnalytics = useCallback(async (showRefreshIndicator: boolean = false) => {
    if (showRefreshIndicator) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }
    
    try {
      const data = await fetchDashboardAnalytics(timeRange);
      setConversionStats(data.conversions);
      setUserStats(data.users);
      setErrorStats(data.errors);
      setPerformanceMetrics(data.performance);
      setLastUpdated(new Date());
    } catch (error) {
      console.error('Failed to load analytics:', error);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [timeRange]);

  useEffect(() => {
    loadAnalytics();
  }, [loadAnalytics]);

  // Auto-refresh every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      loadAnalytics(true);
    }, 30000);
    
    return () => clearInterval(interval);
  }, [loadAnalytics]);

  const handleRefresh = () => {
    loadAnalytics(true);
  };

  const formatPercentage = (value: number): string => {
    return `${value.toFixed(1)}%`;
  };

  const formatNumber = (value: number): string => {
    if (value >= 1000) {
      return `${(value / 1000).toFixed(1)}k`;
    }
    return value.toString();
  };

  const formatTime = (seconds: number): string => {
    if (seconds >= 60) {
      const minutes = Math.floor(seconds / 60);
      const remainingSeconds = Math.round(seconds % 60);
      return `${minutes}m ${remainingSeconds}s`;
    }
    return `${seconds.toFixed(1)}s`;
  };

  const getErrorTrendIcon = (trend: 'up' | 'down' | 'stable') => {
    switch (trend) {
      case 'up':
        return '↑';
      case 'down':
        return '↓';
      default:
        return '→';
    }
  };

  const getErrorTrendClass = (trend: 'up' | 'down' | 'stable') => {
    switch (trend) {
      case 'up':
        return 'trend-up';
      case 'down':
        return 'trend-down';
      default:
        return 'trend-stable';
    }
  };

  if (isLoading) {
    return (
      <div className="analytics-page">
        <div className="analytics-loading">
          <div className="loading-spinner"></div>
          <p>Loading analytics...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="analytics-page">
      {/* Header */}
      <div className="analytics-header">
        <div className="header-content">
          <h1>
            <span className="header-icon">📊</span>
            Analytics Dashboard
          </h1>
          <p className="header-subtitle">
            Monitor platform performance and user activity
          </p>
        </div>
        
        <div className="header-controls">
          <div className="time-range-selector">
            <button 
              className={`time-btn ${timeRange === 7 ? 'active' : ''}`}
              onClick={() => setTimeRange(7)}
            >
              7 Days
            </button>
            <button 
              className={`time-btn ${timeRange === 14 ? 'active' : ''}`}
              onClick={() => setTimeRange(14)}
            >
              14 Days
            </button>
            <button 
              className={`time-btn ${timeRange === 30 ? 'active' : ''}`}
              onClick={() => setTimeRange(30)}
            >
              30 Days
            </button>
          </div>
          
          <button 
            className={`refresh-btn ${isRefreshing ? 'refreshing' : ''}`}
            onClick={handleRefresh}
            disabled={isRefreshing}
          >
            {isRefreshing ? '⟳' : '↻'} Refresh
          </button>
        </div>
        
        {lastUpdated && (
          <p className="last-updated">
            Last updated: {lastUpdated.toLocaleTimeString()}
          </p>
        )}
      </div>

      {/* Stats Grid */}
      <div className="stats-grid">
        {/* Conversion Stats Card */}
        <div className="stat-card conversion-card">
          <div className="stat-icon">🔄</div>
          <div className="stat-content">
            <h3>Conversions</h3>
            <div className="stat-value">{formatNumber(conversionStats?.totalConversions || 0)}</div>
            <div className="stat-details">
              <span className="success">
                ✓ {formatNumber(conversionStats?.successfulConversions || 0)} successful
              </span>
              <span className="failed">
                ✗ {formatNumber(conversionStats?.failedConversions || 0)} failed
              </span>
            </div>
          </div>
          <div className="stat-percentage">
            <span className="percentage-value">
              {formatPercentage(conversionStats?.successRate || 0)}
            </span>
            <span className="percentage-label">success rate</span>
          </div>
        </div>

        {/* User Metrics Card */}
        <div className="stat-card users-card">
          <div className="stat-icon">👥</div>
          <div className="stat-content">
            <h3>Users</h3>
            <div className="stat-value">{formatNumber(userStats?.totalRegistrations || 0)}</div>
            <div className="stat-details">
              <span>+{userStats?.dailySignups || 0} today</span>
              <span>+{userStats?.weeklySignups || 0} this week</span>
            </div>
          </div>
          <div className="stat-percentage">
            <span className="percentage-value">{formatNumber(userStats?.activeUsers || 0)}</span>
            <span className="percentage-label">active users</span>
          </div>
        </div>

        {/* Error Rate Card */}
        <div className="stat-card errors-card">
          <div className="stat-icon">⚠️</div>
          <div className="stat-content">
            <h3>Error Rate</h3>
            <div className="stat-value error-value">
              {formatPercentage(errorStats?.errorRate || 0)}
            </div>
            <div className="stat-details">
              <span className={getErrorTrendClass(errorStats?.errorTrend || 'stable')}>
                {getErrorTrendIcon(errorStats?.errorTrend || 'stable')} trend
              </span>
              <span>{errorStats?.recentErrors || 0} errors</span>
            </div>
          </div>
          <div className="alert-badge" title="Alert threshold is 5%">
            {errorStats && errorStats.errorRate > 5 ? '🚨 Alert' : '✓ OK'}
          </div>
        </div>

        {/* Performance Metrics Card */}
        <div className="stat-card performance-card">
          <div className="stat-icon">⚡</div>
          <div className="stat-content">
            <h3>Performance</h3>
            <div className="stat-value">{formatTime(performanceMetrics?.averageConversionTime || 0)}</div>
            <div className="stat-details">
              <span>Throughput: {performanceMetrics?.throughput || 0}/min</span>
              <span>Peak: {performanceMetrics?.peakTime || 'N/A'}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Error Details Section */}
      {errorStats && errorStats.topErrors.length > 0 && (
        <div className="error-details-section">
          <h2>Top Errors</h2>
          <div className="error-list">
            {errorStats.topErrors.map((error, index) => (
              <div key={index} className="error-item">
                <span className="error-rank">#{index + 1}</span>
                <span className="error-type">{error.errorType}</span>
                <span className="error-count">{error.count} occurrences</span>
                <div className="error-bar">
                  <div 
                    className="error-bar-fill" 
                    style={{ 
                      width: `${(error.count / errorStats.topErrors[0].count) * 100}%` 
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Registration Progress */}
      <div className="registration-progress-section">
        <h2>Beta Registration Progress</h2>
        <div className="progress-container">
          <div className="progress-bar">
            <div 
              className="progress-fill" 
              style={{ 
                width: `${Math.min((userStats?.totalRegistrations || 0), 100)}%` 
              }}
            />
          </div>
          <div className="progress-markers">
            <span>0</span>
            <span className="marker">25</span>
            <span className="marker">50</span>
            <span className="marker">75</span>
            <span>100</span>
          </div>
          <p className="progress-text">
            {userStats?.totalRegistrations || 0} / 100 beta users registered
            {userStats && userStats.totalRegistrations >= 100 && ' 🎉 Goal achieved!'}
          </p>
        </div>
        
        {/* Milestone Badges */}
        <div className="milestone-badges">
          <span className={`milestone-badge ${userStats?.betaMilestones?.reached25 ? 'achieved' : ''}`}>
            {userStats?.betaMilestones?.reached25 ? '✓' : '○'} 25
          </span>
          <span className={`milestone-badge ${userStats?.betaMilestones?.reached50 ? 'achieved' : ''}`}>
            {userStats?.betaMilestones?.reached50 ? '✓' : '○'} 50
          </span>
          <span className={`milestone-badge ${userStats?.betaMilestones?.reached75 ? 'achieved' : ''}`}>
            {userStats?.betaMilestones?.reached75 ? '✓' : '○'} 75
          </span>
          <span className={`milestone-badge ${userStats?.betaMilestones?.reached100 ? 'achieved' : ''}`}>
            {userStats?.betaMilestones?.reached100 ? '✓' : '○'} 100
          </span>
        </div>
      </div>
    </div>
  );
};

export default Analytics;
