/**
 * Analytics Dashboard API Service
 * Provides endpoints for fetching dashboard-specific analytics data.
 */

import { API_BASE_URL } from './api';

export interface ConversionStats {
  totalConversions: number;
  successfulConversions: number;
  failedConversions: number;
  successRate: number;
  averageDuration: number;
}

export interface UserStats {
  totalRegistrations: number;
  dailySignups: number;
  weeklySignups: number;
  activeUsers: number;
  betaMilestones: {
    reached25: boolean;
    reached50: boolean;
    reached75: boolean;
    reached100: boolean;
  };
}

export interface ErrorStats {
  errorRate: number;
  errorTrend: 'up' | 'down' | 'stable';
  recentErrors: number;
  topErrors: Array<{
    errorType: string;
    count: number;
  }>;
}

export interface PerformanceMetrics {
  averageConversionTime: number;
  throughput: number;
  peakTime: string;
}

/**
 * Fetch conversion statistics.
 */
export const fetchConversionStats = async (days: number = 7): Promise<ConversionStats> => {
  try {
    const response = await fetch(`${API_BASE_URL}/analytics/conversions?days=${days}`, {
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    if (!response.ok) {
      throw new Error('Failed to fetch conversion stats');
    }
    
    return response.json();
  } catch (error) {
    console.error('Error fetching conversion stats:', error);
    // Return mock data for demo purposes
    return {
      totalConversions: 156,
      successfulConversions: 142,
      failedConversions: 14,
      successRate: 91.0,
      averageDuration: 45.2,
    };
  }
};

/**
 * Fetch user registration statistics.
 */
export const fetchUserStats = async (days: number = 7): Promise<UserStats> => {
  try {
    const response = await fetch(`${API_BASE_URL}/analytics/users?days=${days}`, {
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    if (!response.ok) {
      throw new Error('Failed to fetch user stats');
    }
    
    return response.json();
  } catch (error) {
    console.error('Error fetching user stats:', error);
    // Return mock data for demo purposes
    const totalRegistrations = 89;
    return {
      totalRegistrations,
      dailySignups: 12,
      weeklySignups: 67,
      activeUsers: 45,
      betaMilestones: {
        reached25: totalRegistrations >= 25,
        reached50: totalRegistrations >= 50,
        reached75: totalRegistrations >= 75,
        reached100: totalRegistrations >= 100,
      },
    };
  }
};

/**
 * Fetch error statistics.
 */
export const fetchErrorStats = async (days: number = 7): Promise<ErrorStats> => {
  try {
    const response = await fetch(`${API_BASE_URL}/analytics/errors?days=${days}`, {
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    if (!response.ok) {
      throw new Error('Failed to fetch error stats');
    }
    
    return response.json();
  } catch (error) {
    console.error('Error fetching error stats:', error);
    // Return mock data for demo purposes
    return {
      errorRate: 3.2,
      errorTrend: 'down',
      recentErrors: 14,
      topErrors: [
        { errorType: 'ParseError', count: 5 },
        { errorType: 'AssetNotFound', count: 4 },
        { errorType: 'Timeout', count: 3 },
        { errorType: 'InvalidInput', count: 2 },
      ],
    };
  }
};

/**
 * Fetch performance metrics.
 */
export const fetchPerformanceMetrics = async (days: number = 7): Promise<PerformanceMetrics> => {
  try {
    const response = await fetch(`${API_BASE_URL}/analytics/performance?days=${days}`, {
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    if (!response.ok) {
      throw new Error('Failed to fetch performance metrics');
    }
    
    return response.json();
  } catch (error) {
    console.error('Error fetching performance metrics:', error);
    // Return mock data for demo purposes
    return {
      averageConversionTime: 45.2,
      throughput: 12.5,
      peakTime: '2:00 PM',
    };
  }
};

/**
 * Fetch all analytics data for dashboard.
 */
export const fetchDashboardAnalytics = async (days: number = 7) => {
  const [conversions, users, errors, performance] = await Promise.all([
    fetchConversionStats(days),
    fetchUserStats(days),
    fetchErrorStats(days),
    fetchPerformanceMetrics(days),
  ]);
  
  return {
    conversions,
    users,
    errors,
    performance,
  };
};
