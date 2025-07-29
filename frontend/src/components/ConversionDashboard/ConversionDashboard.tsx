/**
 * ConversionDashboard - Complete conversion workflow integration
 * Orchestrates upload, progress tracking, and results display
 */

import React, { useState } from 'react';
import { ConversionUpload } from '../ConversionUpload/ConversionUpload';
import { ConversionReportContainer } from '../ConversionReport/ConversionReportContainer';
import styles from './ConversionDashboard.module.css';

type DashboardState = 'upload' | 'processing' | 'completed' | 'failed';

export const ConversionDashboard: React.FC = () => {
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [dashboardState, setDashboardState] = useState<DashboardState>('upload');

  const handleConversionStart = (jobId: string) => {
    setCurrentJobId(jobId);
    setDashboardState('processing');
  };

  const handleConversionComplete = (jobId: string, status: 'completed' | 'failed' = 'completed') => {
    setCurrentJobId(jobId);
    setDashboardState(status);
  };

  const handleStartNewConversion = () => {
    setCurrentJobId(null);
    setDashboardState('upload');
  };

  const renderContent = () => {
    switch (dashboardState) {
      case 'upload':
        return (
          <ConversionUpload
            onConversionStart={handleConversionStart}
            onConversionComplete={handleConversionComplete}
          />
        );
      
      case 'processing':
        return (
          <ConversionUpload
            onConversionStart={handleConversionStart}
            onConversionComplete={handleConversionComplete}
          />
        );
      
      case 'completed':
      case 'failed':
        return (
          <div>
            <div className={styles.statusHeader}>
              <h2>Conversion {dashboardState === 'completed' ? 'Complete' : 'Failed'}</h2>
              <button
                onClick={handleStartNewConversion}
                className={styles.startButton}
              >
                Start New Conversion
              </button>
            </div>
            
            {currentJobId && (
              <ConversionReportContainer
                jobId={currentJobId}
                jobStatus={dashboardState as 'completed' | 'failed'}
              />
            )}
          </div>
        );
      
      default:
        return null;
    }
  };

  return (
    <div className={styles.dashboard}>
      <div className={styles.header}>
        <h1>ModPorter AI - Java to Bedrock Converter</h1>
        <p>Convert your Java Edition mods to Bedrock Edition add-ons with AI-powered smart assumptions</p>
      </div>
      
      {renderContent()}
    </div>
  );
};