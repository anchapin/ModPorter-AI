/**
 * Simple Convert Page for MVP
 * Clean upload-to-download experience
 */

import React, { useState } from 'react';
import { ConversionFlowManager } from '../components/ConversionFlow';
import { BatchConversionManager } from '../components/BatchConversion';
import { AdvancedOptionsPanel, AdvancedOptions } from '../components/AdvancedOptions';
import './ConvertPage.css';

const DEFAULT_ADVANCED_OPTIONS: AdvancedOptions = {
  timeout: 300,
  parallelProcessing: false,
  maxRetries: 3,
  enableSmartAssumptions: true,
  enableTextureOptimization: true,
  targetVersion: '1.20.0',
  generateReport: true
};

export const ConvertPage: React.FC = () => {
  const [conversionMode, setConversionMode] = useState<'single' | 'batch'>('single');
  const [advancedOptions, setAdvancedOptions] = useState<AdvancedOptions>(DEFAULT_ADVANCED_OPTIONS);

  const handleComplete = (jobId: string, filename: string) => {
    console.log('Conversion completed:', jobId, filename);
    // You could trigger analytics, notifications, etc.
  };

  const handleError = (error: string) => {
    console.error('Conversion failed:', error);
    // You could trigger error reporting, etc.
  };

  const handleBatchComplete = (jobIds: string[]) => {
    console.log('Batch conversion completed:', jobIds);
  };

  return (
    <div className="convert-page">
      <div className="convert-page-header">
        <h1>Mod Converter</h1>
        <p>
          Convert your Minecraft Java Edition mods to Bedrock Edition
        </p>
      </div>

      {/* Conversion Mode Tabs */}
      <div className="conversion-mode-tabs">
        <button
          className={`mode-tab ${conversionMode === 'single' ? 'active' : ''}`}
          onClick={() => setConversionMode('single')}
        >
          Single Conversion
        </button>
        <button
          className={`mode-tab ${conversionMode === 'batch' ? 'active' : ''}`}
          onClick={() => setConversionMode('batch')}
        >
          Batch Conversion
        </button>
      </div>

      {/* Advanced Options */}
      <div className="convert-page-options">
        <AdvancedOptionsPanel
          options={advancedOptions}
          onChange={setAdvancedOptions}
        />
      </div>

      {/* Conversion Flow */}
      {conversionMode === 'single' ? (
        <ConversionFlowManager
          onComplete={handleComplete}
          onError={handleError}
          showReport={true}
          autoReset={false}
        />
      ) : (
        <BatchConversionManager
          onComplete={handleBatchComplete}
          onError={handleError}
        />
      )}

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
