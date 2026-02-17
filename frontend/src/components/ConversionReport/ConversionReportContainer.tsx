/**
 * ConversionReportContainer - Fetches and displays real conversion report data
 */

import React, { useState, useEffect, useCallback } from 'react';
import { ConversionReport } from './ConversionReport';
import type { InteractiveReport } from '../../types/api';
import { API_BASE_URL } from '../../services/api';
import styles from './ConversionReport.module.css';

interface ConversionReportContainerProps {
  jobId: string;
  jobStatus?: 'completed' | 'failed' | 'processing';
}

export const ConversionReportContainer: React.FC<ConversionReportContainerProps> = ({
  jobId,
  jobStatus
}) => {
  const [reportData, setReportData] = useState<InteractiveReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchReportData = useCallback(async () => {
    if (!jobId) {
      setError('No job ID provided');
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      // Try new conversions endpoint first, fall back to legacy jobs endpoint
      let response = await fetch(`${API_BASE_URL}/conversions/${jobId}/report`);
      
      if (response.status === 404) {
        // Fallback to legacy endpoint
        response = await fetch(`${API_BASE_URL}/jobs/${jobId}/report`);
      }

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Conversion report not found. Please ensure the conversion completed successfully.');
        }
        throw new Error(`Failed to fetch report: ${response.status} ${response.statusText}`);
      }

      const data: InteractiveReport = await response.json();
      setReportData(data);
    } catch (err) {
      console.error('Error fetching conversion report:', err);
      setError(err instanceof Error ? err.message : 'Failed to load conversion report');
    } finally {
      setLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    fetchReportData();
  }, [fetchReportData]);

  if (loading) {
    return (
      <div className={styles.loadingContainer}>
        <div className={styles.loadingSpinner}></div>
        <p>Loading conversion report...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.errorContainer}>
        <h2>Unable to Load Report</h2>
        <p>{error}</p>
        <button 
          onClick={fetchReportData} 
          className={styles.retryButton}
        >
          Retry
        </button>
      </div>
    );
  }

  if (!reportData) {
    return (
      <div className={styles.errorContainer}>
        <h2>No Report Data</h2>
        <p>The conversion report is not available at this time.</p>
      </div>
    );
  }

  return <ConversionReport conversionResult={reportData} jobStatus={jobStatus} />;
};