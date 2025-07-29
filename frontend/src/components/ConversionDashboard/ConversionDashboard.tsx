/**
 * ConversionDashboard - Complete conversion workflow integration
 * Orchestrates upload, progress tracking, and results display
 */

import React, { useState } from 'react';
import { ConversionUpload } from '../ConversionUpload/ConversionUpload';
import { ConversionReportContainer } from '../ConversionReport/ConversionReportContainer';
import { ConversionStatusEnum } from '../../types/api';

type DashboardState = 'upload' | 'processing' | 'completed' | 'failed';

export const ConversionDashboard: React.FC = () => {
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [dashboardState, setDashboardState] = useState<DashboardState>('upload');
  const [jobStatus, setJobStatus] = useState<string | null>(null);

  const handleConversionStart = (jobId: string) => {
    setCurrentJobId(jobId);
    setDashboardState('processing');
    setJobStatus('processing');
  };

  const handleConversionComplete = (jobId: string) => {
    setCurrentJobId(jobId);
    // Determine if it's completed or failed based on the final status
    // This could be enhanced by checking the actual status
    setDashboardState('completed');
    setJobStatus('completed');
  };

  const handleStartNewConversion = () => {
    setCurrentJobId(null);
    setDashboardState('upload');
    setJobStatus(null);
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
          <div>
            <ConversionUpload
              onConversionStart={handleConversionStart}
              onConversionComplete={handleConversionComplete}
            />
          </div>
        );
      
      case 'completed':
      case 'failed':
        return (
          <div>
            <div style={{ 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'center', 
              marginBottom: '2rem',
              padding: '1rem',
              backgroundColor: '#f8f9fa',
              borderRadius: '8px'
            }}>
              <h2>Conversion {dashboardState === 'completed' ? 'Complete' : 'Failed'}</h2>
              <button
                onClick={handleStartNewConversion}
                style={{
                  backgroundColor: '#007bff',
                  color: 'white',
                  border: 'none',
                  padding: '0.5rem 1rem',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
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
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '2rem' }}>
      <div style={{ marginBottom: '2rem', textAlign: 'center' }}>
        <h1>ModPorter AI - Java to Bedrock Converter</h1>
        <p>Convert your Java Edition mods to Bedrock Edition add-ons with AI-powered smart assumptions</p>
      </div>
      
      {renderContent()}
    </div>
  );
};