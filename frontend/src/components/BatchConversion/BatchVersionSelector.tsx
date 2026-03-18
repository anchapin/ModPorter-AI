/**
 * Batch Version Selector Component
 * Task 1.5.2.4: Add Minecraft version selection
 * 
 * Features:
 * - Version dropdown (1.19, 1.20, 1.21)
 * - Version-specific rules
 * - Warning for incompatible features
 */

import React from 'react';

export type MinecraftVersion = '1.19.2' | '1.19.4' | '1.20.0' | '1.20.1' | '1.20.2' | '1.20.4' | '1.21.0' | '1.21.1' | '1.21.2';

export interface VersionInfo {
  version: MinecraftVersion;
  displayName: string;
  releaseDate: string;
  features: string[];
  limitations: string[];
}

export const SUPPORTED_VERSIONS: VersionInfo[] = [
  {
    version: '1.19.2',
    displayName: 'Minecraft 1.19.2 (Wild Update)',
    releaseDate: '2022-07-06',
    features: ['Deep Dark', 'Frog', 'Allay', 'Mud', 'Copper Bulb', 'Sculk Sensor'],
    limitations: ['No vibration resonance', 'No sniffer'],
  },
  {
    version: '1.19.4',
    displayName: 'Minecraft 1.19.4 (The Wild Update)',
    releaseDate: '2023-03-09',
    features: ['All 1.19 features', 'Chained Commands', 'Blast Furnace UI', 'Improved Book UI'],
    limitations: ['No experimental features'],
  },
  {
    version: '1.20.0',
    displayName: 'Minecraft 1.20.0 (Trails & Tales)',
    releaseDate: '2023-06-07',
    features: ['Sniffer', 'Armadillos', 'Breeze', 'Cherry Grove', 'Hanging Signs', 'Armor Trims'],
    limitations: ['No archaeology books'],
  },
  {
    version: '1.20.1',
    displayName: 'Minecraft 1.20.1',
    releaseDate: '2023-06-16',
    features: ['Breeze spawn', 'Camel ride', 'Improved world gen'],
    limitations: ['Minor features only'],
  },
  {
    version: '1.20.2',
    displayName: 'Minecraft 1.20.2',
    releaseDate: '2023-09-20',
    features: ['All 1.20.1 features', 'Update 1.20.2 mob tweaks'],
    limitations: ['No archaeology'],
  },
  {
    version: '1.20.4',
    displayName: 'Minecraft 1.20.4',
    releaseDate: '2023-11-07',
    features: ['All 1.20 features', 'Wolf armor', 'Crafter', 'Recipe book update'],
    limitations: ['No bundles'],
  },
  {
    version: '1.21.0',
    displayName: 'Minecraft 1.21.0 (The Trials Update)',
    releaseDate: '2024-04-24',
    features: ['Trial Chamber', 'Breeze mob', 'Ominous Trial', ' Mace weapon', 'Wind Charge'],
    limitations: ['Experimental features'],
  },
  {
    version: '1.21.1',
    displayName: 'Minecraft 1.21.1',
    releaseDate: '2024-06-27',
    features: ['All 1.21.0 features', 'Improved performance', 'Bug fixes'],
    limitations: ['No new features'],
  },
  {
    version: '1.21.2',
    displayName: 'Minecraft 1.21.2',
    releaseDate: '2024-09-12',
    features: ['All 1.21.1 features', 'Improved world gen', 'More mob variants'],
    limitations: ['Stable version'],
  },
];

interface BatchVersionSelectorProps {
  selectedVersion: MinecraftVersion;
  onVersionChange: (version: MinecraftVersion) => void;
  disabled?: boolean;
}

export const BatchVersionSelector: React.FC<BatchVersionSelectorProps> = ({
  selectedVersion,
  onVersionChange,
  disabled = false,
}) => {
  const selectedInfo = SUPPORTED_VERSIONS.find(v => v.version === selectedVersion);

  const getWarningMessage = (version: MinecraftVersion): string | null => {
    if (version.startsWith('1.19')) {
      return 'Note: Some 1.20+ features may not be fully supported';
    }
    if (version === '1.21.0') {
      return 'Warning: 1.21.0 uses experimental features - some conversions may require manual adjustment';
    }
    return null;
  };

  return (
    <div className="batch-version-selector">
      <div className="version-selector-header">
        <label htmlFor="batch-version-select">Target Minecraft Version:</label>
        <select
          id="batch-version-select"
          value={selectedVersion}
          onChange={(e) => onVersionChange(e.target.value as MinecraftVersion)}
          disabled={disabled}
          className="version-select"
        >
          <optgroup label="1.19.x (The Wild Update)">
            {SUPPORTED_VERSIONS.filter(v => v.version.startsWith('1.19')).map(v => (
              <option key={v.version} value={v.version}>
                {v.displayName}
              </option>
            ))}
          </optgroup>
          <optgroup label="1.20.x (Trails & Tales)">
            {SUPPORTED_VERSIONS.filter(v => v.version.startsWith('1.20')).map(v => (
              <option key={v.version} value={v.version}>
                {v.displayName}
              </option>
            ))}
          </optgroup>
          <optgroup label="1.21.x (Trials Update)">
            {SUPPORTED_VERSIONS.filter(v => v.version.startsWith('1.21')).map(v => (
              <option key={v.version} value={v.version}>
                {v.displayName}
              </option>
            ))}
          </optgroup>
        </select>
      </div>

      {selectedInfo && (
        <div className="version-info">
          <div className="version-features">
            <h4>Supported Features:</h4>
            <ul>
              {selectedInfo.features.slice(0, 5).map((feature, idx) => (
                <li key={idx}>{feature}</li>
              ))}
              {selectedInfo.features.length > 5 && (
                <li className="more">+{selectedInfo.features.length - 5} more</li>
              )}
            </ul>
          </div>
          
          {selectedInfo.limitations.length > 0 && (
            <div className="version-limitations">
              <h4>Limitations:</h4>
              <ul>
                {selectedInfo.limitations.map((limitation, idx) => (
                  <li key={idx}>{limitation}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {getWarningMessage(selectedVersion) && (
        <div className="version-warning">
          ⚠️ {getWarningMessage(selectedVersion)}
        </div>
      )}
    </div>
  );
};

export default BatchVersionSelector;
