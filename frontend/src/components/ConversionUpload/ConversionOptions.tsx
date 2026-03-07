import React, { useState, memo } from 'react';
import './ConversionUpload.css';

interface ConversionOptionsProps {
  smartAssumptions: boolean;
  onSmartAssumptionsChange: (checked: boolean) => void;
  includeDependencies: boolean;
  onIncludeDependenciesChange: (checked: boolean) => void;
  disabled: boolean;
}

// Memoized to prevent re-renders when parent state (like upload progress) changes frequently
export const ConversionOptions: React.FC<ConversionOptionsProps> = memo(
  ({
    smartAssumptions,
    onSmartAssumptionsChange,
    includeDependencies,
    onIncludeDependenciesChange,
    disabled,
  }) => {
    const [showSmartAssumptionsInfo, setShowSmartAssumptionsInfo] =
      useState(false);

    return (
      <div
        className={`conversion-options ${disabled ? 'disabled-options' : ''}`}
      >
        <div className="option-group">
          <div className="checkbox-with-info">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={smartAssumptions}
                onChange={(e) => onSmartAssumptionsChange(e.target.checked)}
                disabled={disabled}
              />
              <span className="checkmark"></span>
              Enable Smart Assumptions
            </label>
            <button
              type="button"
              className="info-button"
              onClick={() =>
                setShowSmartAssumptionsInfo(!showSmartAssumptionsInfo)
              }
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
                When enabled, our AI will make intelligent assumptions to
                convert incompatible features:
              </p>
              <ul>
                <li>
                  Custom dimensions → Large structures in existing dimensions
                </li>
                <li>
                  Complex machinery → Simplified blocks with similar
                  functionality
                </li>
                <li>Custom GUIs → Book or sign-based interfaces</li>
              </ul>
              <p>
                This increases conversion success rate but may alter some mod
                features.
              </p>
            </div>
          )}
        </div>

        <div className="option-group">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={includeDependencies}
              onChange={(e) => onIncludeDependenciesChange(e.target.checked)}
              disabled={disabled}
            />
            <span className="checkmark"></span>
            Include Dependencies
          </label>
        </div>
      </div>
    );
  }
);

export default ConversionOptions;
