import React, { useState, memo } from 'react';
import './ConversionUpload.css';

interface ConversionOptionsProps {
  smartAssumptions: boolean;
  setSmartAssumptions: (value: boolean) => void;
  includeDependencies: boolean;
  setIncludeDependencies: (value: boolean) => void;
  disabled: boolean;
}

/**
 * Renders the conversion configuration options (Smart Assumptions, Include Dependencies).
 *
 * Optimized with React.memo to prevent unnecessary re-renders when parent component
 * updates frequently (e.g., during file upload progress tracking).
 *
 * Expected Performance Impact:
 * - Prevents ~10 re-renders per second during the upload phase.
 * - Reduces main thread blocking during high-frequency state updates in parent.
 */
export const ConversionOptions = memo(({
  smartAssumptions,
  setSmartAssumptions,
  includeDependencies,
  setIncludeDependencies,
  disabled
}: ConversionOptionsProps) => {
  // Local state for info panel visibility prevents parent re-renders when toggled
  const [showSmartAssumptionsInfo, setShowSmartAssumptionsInfo] = useState(false);

  return (
    <div className={`conversion-options ${disabled ? 'disabled-options' : ''}`}>
      <div className="option-group">
        <div className="checkbox-with-info">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={smartAssumptions}
              onChange={(e) => setSmartAssumptions(e.target.checked)}
              disabled={disabled}
            />
            <span className="checkmark"></span>
            Enable Smart Assumptions
          </label>
          <button
            type="button"
            className="info-button"
            onClick={() => setShowSmartAssumptionsInfo(!showSmartAssumptionsInfo)}
            aria-label="Learn more about smart assumptions"
            aria-expanded={showSmartAssumptionsInfo}
            aria-controls="smart-assumptions-info"
            disabled={disabled}
          >
            ?
          </button>
        </div>

        {showSmartAssumptionsInfo && (
          <div className="info-panel" id="smart-assumptions-info">
            <h4>Smart Assumptions</h4>
            <p>
              When enabled, our AI will make intelligent assumptions to convert incompatible features:
            </p>
            <ul>
              <li>Custom dimensions → Large structures in existing dimensions</li>
              <li>Complex machinery → Simplified blocks with similar functionality</li>
              <li>Custom GUIs → Book or sign-based interfaces</li>
            </ul>
            <p>This increases conversion success rate but may alter some mod features.</p>
          </div>
        )}
      </div>

      <div className="option-group">
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={includeDependencies}
            onChange={(e) => setIncludeDependencies(e.target.checked)}
            disabled={disabled}
          />
          <span className="checkmark"></span>
          Include Dependencies
        </label>
      </div>
    </div>
  );
});

ConversionOptions.displayName = 'ConversionOptions';
