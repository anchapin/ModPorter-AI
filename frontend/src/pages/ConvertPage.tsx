/**
 * Simple Convert Page for MVP
 * Clean upload-to-download experience
 */

import React from 'react';
import { ConversionFlowManager } from '../components/ConversionFlow';
import './ConvertPage.css';

export const ConvertPage: React.FC = () => {
  const handleComplete = (jobId: string, filename: string) => {
    console.log('Conversion completed:', jobId, filename);
    // You could trigger analytics, notifications, etc.
  };

  const handleError = (error: string) => {
    console.error('Conversion failed:', error);
    // You could trigger error reporting, etc.
  };

  return (
    <div className="convert-page">
      <div className="convert-page-header">
        <h1>Mod Converter</h1>
        <p>
          Convert your Minecraft Java Edition mods to Bedrock Edition
        </p>
      </div>

      <ConversionFlowManager
        onComplete={handleComplete}
        onError={handleError}
        showReport={true}
        autoReset={false}
      />

      <div className="convert-page-footer">
        <div className="info-cards">
          <div className="info-card">
            <div className="card-icon">⚡</div>
            <h3>Fast Conversion</h3>
            <p>Most mods convert in under 5 minutes</p>
          </div>
          <div className="info-card">
            <div className="card-icon">🧠</div>
            <h3>Smart AI</h3>
            <p>Intelligent assumptions for better compatibility</p>
          </div>
          <div className="info-card">
            <div className="card-icon">📦</div>
            <h3>Ready to Use</h3>
            <p>Download .mcaddon files ready for Bedrock</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ConvertPage;
