/**
 * Advanced Options Panel
 * Provides configurable options for conversions
 */

import React, { useState, useCallback } from 'react';
import { useNotification } from '../NotificationSystem';
import './AdvancedOptionsPanel.css';

export interface AdvancedOptions {
  timeout: number;
  parallelProcessing: boolean;
  maxRetries: number;
  enableSmartAssumptions: boolean;
  enableTextureOptimization: boolean;
  targetVersion: string;
  generateReport: boolean;
}

interface AdvancedOptionsPanelProps {
  options: AdvancedOptions;
  onChange: (options: AdvancedOptions) => void;
}

const DEFAULT_OPTIONS: AdvancedOptions = {
  timeout: 300,
  parallelProcessing: false,
  maxRetries: 3,
  enableSmartAssumptions: true,
  enableTextureOptimization: true,
  targetVersion: '1.20.0',
  generateReport: true
};

const TARGET_VERSIONS = [
  { value: '1.20.0', label: '1.20.0 (Wild Update)' },
  { value: '1.19.0', label: '1.19.0 (The Wild Update)' },
  { value: '1.18.0', label: '1.18.0 (Caves & Cliffs II)' },
  { value: '1.17.0', label: '1.17.0 (Caves & Cliffs I)' },
  { value: '1.16.0', label: '1.16.0 (Nether Update)' },
  { value: '1.14.0', label: '1.14.0 (Village & Pillage)' }
];

export const AdvancedOptionsPanel: React.FC<AdvancedOptionsPanelProps> = ({
  options,
  onChange
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const notification = useNotification();

  const handleChange = useCallback((key: keyof AdvancedOptions, value: any) => {
    const newOptions = { ...options, [key]: value };
    onChange(newOptions);
  }, [options, onChange]);

  const handleReset = useCallback(() => {
    onChange(DEFAULT_OPTIONS);
    notification.info('Advanced options reset to defaults');
  }, [onChange, notification]);

  const handleSavePreset = useCallback(() => {
    localStorage.setItem('advancedOptions', JSON.stringify(options));
    notification.success('Options preset saved');
  }, [options, notification]);

  const handleLoadPreset = useCallback(() => {
    const saved = localStorage.getItem('advancedOptions');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        onChange(parsed);
        notification.success('Options preset loaded');
      } catch (e) {
        notification.error('Failed to load preset');
      }
    } else {
      notification.warning('No saved preset found');
    }
  }, [onChange, notification]);

  return (
    <div className="advanced-options-panel">
      <div 
        className="panel-header"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="header-title">
          <span className="toggle-icon">{isExpanded ? '▼' : '▶'}</span>
          <h3>Advanced Options</h3>
        </div>
        {isExpanded && (
          <div className="header-actions">
            <button 
              className="preset-button"
              onClick={(e) => {
                e.stopPropagation();
                handleLoadPreset();
              }}
            >
              Load Preset
            </button>
            <button 
              className="preset-button"
              onClick={(e) => {
                e.stopPropagation();
                handleSavePreset();
              }}
            >
              Save Preset
            </button>
          </div>
        )}
      </div>

      {isExpanded && (
        <div className="panel-content">
          {/* Timeout */}
          <div className="option-group">
            <label htmlFor="timeout">
              Conversion Timeout (seconds)
              <span className="hint">Maximum time to wait for conversion</span>
            </label>
            <input
              type="number"
              id="timeout"
              min={60}
              max={3600}
              step={30}
              value={options.timeout}
              onChange={(e) => handleChange('timeout', Number(e.target.value))}
            />
          </div>

          {/* Max Retries */}
          <div className="option-group">
            <label htmlFor="maxRetries">
              Maximum Retries
              <span className="hint">Number of retry attempts on failure</span>
            </label>
            <input
              type="number"
              id="maxRetries"
              min={0}
              max={10}
              value={options.maxRetries}
              onChange={(e) => handleChange('maxRetries', Number(e.target.value))}
            />
          </div>

          {/* Target Version */}
          <div className="option-group">
            <label htmlFor="targetVersion">
              Target Minecraft Version
              <span className="hint">Bedrock Edition version to target</span>
            </label>
            <select
              id="targetVersion"
              value={options.targetVersion}
              onChange={(e) => handleChange('targetVersion', e.target.value)}
            >
              {TARGET_VERSIONS.map(v => (
                <option key={v.value} value={v.value}>{v.label}</option>
              ))}
            </select>
          </div>

          {/* Toggle Options */}
          <div className="option-toggles">
            <div className="toggle-option">
              <label className="toggle-label">
                <input
                  type="checkbox"
                  checked={options.parallelProcessing}
                  onChange={(e) => handleChange('parallelProcessing', e.target.checked)}
                />
                <span className="toggle-switch"></span>
                <span className="toggle-text">
                  Parallel Processing
                  <span className="hint">Process multiple files concurrently</span>
                </span>
              </label>
            </div>

            <div className="toggle-option">
              <label className="toggle-label">
                <input
                  type="checkbox"
                  checked={options.enableSmartAssumptions}
                  onChange={(e) => handleChange('enableSmartAssumptions', e.target.checked)}
                />
                <span className="toggle-switch"></span>
                <span className="toggle-text">
                  Smart Assumptions
                  <span className="hint">AI makes intelligent guesses for missing info</span>
                </span>
              </label>
            </div>

            <div className="toggle-option">
              <label className="toggle-label">
                <input
                  type="checkbox"
                  checked={options.enableTextureOptimization}
                  onChange={(e) => handleChange('enableTextureOptimization', e.target.checked)}
                />
                <span className="toggle-switch"></span>
                <span className="toggle-text">
                  Texture Optimization
                  <span className="hint">Compress and optimize textures</span>
                </span>
              </label>
            </div>

            <div className="toggle-option">
              <label className="toggle-label">
                <input
                  type="checkbox"
                  checked={options.generateReport}
                  onChange={(e) => handleChange('generateReport', e.target.checked)}
                />
                <span className="toggle-switch"></span>
                <span className="toggle-text">
                  Generate Report
                  <span className="hint">Create detailed conversion report</span>
                </span>
              </label>
            </div>
          </div>

          {/* Reset Button */}
          <div className="panel-footer">
            <button className="reset-button" onClick={handleReset}>
              Reset to Defaults
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdvancedOptionsPanel;
