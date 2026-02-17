/**
 * Settings Component - Day 5 Enhancement
 * Provides API key management and user preferences for the conversion app
 */

import React, { useState, useEffect } from 'react';
import './Settings.css';

interface SettingsPreferences {
  defaultSmartAssumptions: boolean;
  defaultIncludeDependencies: boolean;
  autoCheckUpdates: boolean;
  theme: 'light' | 'dark' | 'auto';
  notifications: boolean;
}

interface SettingsProps {
  className?: string;
  onSettingsChange?: (settings: SettingsPreferences) => void;
}

export const Settings: React.FC<SettingsProps> = ({ 
  className = '',
  onSettingsChange 
}) => {
  const [preferences, setPreferences] = useState<SettingsPreferences>({
    defaultSmartAssumptions: true,
    defaultIncludeDependencies: false,
    autoCheckUpdates: true,
    theme: 'auto',
    notifications: true,
  });
  
  const [apiKeys, setApiKeys] = useState({
    openai: '',
    curseforge: '',
    modrinth: '',
  });
  
  const [showApiKeys, setShowApiKeys] = useState<Record<string, boolean>>({});
  const [saved, setSaved] = useState(false);
  const [activeTab, setActiveTab] = useState<'preferences' | 'api-keys'>('preferences');

  // Load settings from localStorage on mount
  useEffect(() => {
    const storedPreferences = localStorage.getItem('modporter_preferences');
    if (storedPreferences) {
      try {
        const parsed = JSON.parse(storedPreferences);
        setPreferences(prev => ({ ...prev, ...parsed }));
      } catch (e) {
        console.error('Failed to parse stored preferences:', e);
      }
    }

    // Load masked API keys (never store actual keys in localStorage in production)
    const storedKeyStatus = localStorage.getItem('modporter_api_keys_status');
    if (storedKeyStatus) {
      try {
        const status = JSON.parse(storedKeyStatus);
        setApiKeys(prev => ({
          ...prev,
          openai: status.openai ? '••••••••••••••••' : '',
          curseforge: status.curseforge ? '••••••••••••••••' : '',
          modrinth: status.modrinth ? '••••••••••••••••' : '',
        }));
      } catch (e) {
        console.error('Failed to parse API key status:', e);
      }
    }
  }, []);

  // Save preferences to localStorage
  const savePreferences = (newPreferences: SettingsPreferences) => {
    setPreferences(newPreferences);
    localStorage.setItem('modporter_preferences', JSON.stringify(newPreferences));
    
    if (onSettingsChange) {
      onSettingsChange(newPreferences);
    }
    
    showSavedMessage();
  };

  // Save API key status (masked, never the actual key)
  const saveApiKey = (keyName: string, value: string) => {
    const hasKey = value.length > 0;
    const newKeys = { ...apiKeys, [keyName]: value };
    setApiKeys(newKeys);
    
    // Store only the status (whether key exists), never the actual key
    const status = {
      openai: newKeys.openai.length > 0,
      curseforge: newKeys.curseforge.length > 0,
      modrinth: newKeys.modrinth.length > 0,
    };
    localStorage.setItem('modporter_api_keys_status', JSON.stringify(status));
    
    // In production, you would send the actual key to the backend securely
    // For now, we just store the status
    showSavedMessage();
  };

  const showSavedMessage = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const toggleApiKeyVisibility = (keyName: string) => {
    setShowApiKeys(prev => ({ ...prev, [keyName]: !prev[keyName] }));
  };

  const handlePreferenceChange = (key: keyof SettingsPreferences, value: any) => {
    const newPreferences = { ...preferences, [key]: value };
    savePreferences(newPreferences);
  };

  const handleApiKeyChange = (keyName: string, value: string) => {
    // Don't save actual API keys to localStorage in production
    // This is just for demonstration
    setApiKeys(prev => ({ ...prev, [keyName]: value }));
  };

  const handleApiKeyBlur = (keyName: string) => {
    // Save when user leaves the field
    saveApiKey(keyName, apiKeys[keyName as keyof typeof apiKeys]);
  };

  return (
    <div className={`settings-container ${className}`}>
      <div className="settings-header">
        <h2>⚙️ Settings</h2>
        {saved && <span className="saved-message">✓ Saved</span>}
      </div>

      <div className="settings-tabs">
        <button 
          className={`tab-btn ${activeTab === 'preferences' ? 'active' : ''}`}
          onClick={() => setActiveTab('preferences')}
        >
          Preferences
        </button>
        <button 
          className={`tab-btn ${activeTab === 'api-keys' ? 'active' : ''}`}
          onClick={() => setActiveTab('api-keys')}
        >
          API Keys
        </button>
      </div>

      {activeTab === 'preferences' && (
        <div className="settings-content">
          <div className="settings-section">
            <h3>Default Conversion Options</h3>
            
            <div className="setting-item">
              <label className="setting-label">
                <input
                  type="checkbox"
                  checked={preferences.defaultSmartAssumptions}
                  onChange={(e) => handlePreferenceChange('defaultSmartAssumptions', e.target.checked)}
                />
                <span className="label-text">
                  Smart Assumptions
                  <span className="label-description">
                    Automatically make reasonable assumptions for missing information
                  </span>
                </span>
              </label>
            </div>

            <div className="setting-item">
              <label className="setting-label">
                <input
                  type="checkbox"
                  checked={preferences.defaultIncludeDependencies}
                  onChange={(e) => handlePreferenceChange('defaultIncludeDependencies', e.target.checked)}
                />
                <span className="label-text">
                  Include Dependencies
                  <span className="label-description">
                    Automatically include required dependencies in conversions
                  </span>
                </span>
              </label>
            </div>
          </div>

          <div className="settings-section">
            <h3>Application</h3>
            
            <div className="setting-item">
              <label className="setting-label">
                <span className="label-text">
                  Theme
                  <span className="label-description">
                    Choose your preferred color theme
                  </span>
                </span>
                <select
                  value={preferences.theme}
                  onChange={(e) => handlePreferenceChange('theme', e.target.value)}
                  className="setting-select"
                >
                  <option value="light">Light</option>
                  <option value="dark">Dark</option>
                  <option value="auto">Auto (System)</option>
                </select>
              </label>
            </div>

            <div className="setting-item">
              <label className="setting-label">
                <input
                  type="checkbox"
                  checked={preferences.notifications}
                  onChange={(e) => handlePreferenceChange('notifications', e.target.checked)}
                />
                <span className="label-text">
                  Notifications
                  <span className="label-description">
                    Receive notifications for conversion status updates
                  </span>
                </span>
              </label>
            </div>

            <div className="setting-item">
              <label className="setting-label">
                <input
                  type="checkbox"
                  checked={preferences.autoCheckUpdates}
                  onChange={(e) => handlePreferenceChange('autoCheckUpdates', e.target.checked)}
                />
                <span className="label-text">
                  Auto-check Updates
                  <span className="label-description">
                    Automatically check for new versions
                  </span>
                </span>
              </label>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'api-keys' && (
        <div className="settings-content">
          <div className="settings-section">
            <h3>API Keys</h3>
            <p className="section-description">
              Enter your API keys for enhanced functionality. Keys are stored securely and never shared.
            </p>
            
            <div className="api-key-item">
              <label className="api-key-label">
                OpenAI API Key
                <span className="key-description">
                  Required for AI-powered features and embeddings
                </span>
              </label>
              <div className="api-key-input-group">
                <input
                  type={showApiKeys.openai ? 'text' : 'password'}
                  value={apiKeys.openai}
                  onChange={(e) => handleApiKeyChange('openai', e.target.value)}
                  onBlur={() => handleApiKeyBlur('openai')}
                  placeholder="sk-..."
                  className="api-key-input"
                />
                <button
                  type="button"
                  className="visibility-toggle"
                  onClick={() => toggleApiKeyVisibility('openai')}
                  title={showApiKeys.openai ? 'Hide' : 'Show'}
                >
                  {showApiKeys.openai ? '🙈' : '👁️'}
                </button>
              </div>
            </div>

            <div className="api-key-item">
              <label className="api-key-label">
                CurseForge API Key
                <span className="key-description">
                  Required for importing mods from CurseForge
                </span>
              </label>
              <div className="api-key-input-group">
                <input
                  type={showApiKeys.curseforge ? 'text' : 'password'}
                  value={apiKeys.curseforge}
                  onChange={(e) => handleApiKeyChange('curseforge', e.target.value)}
                  onBlur={() => handleApiKeyBlur('curseforge')}
                  placeholder="Enter your CurseForge API key"
                  className="api-key-input"
                />
                <button
                  type="button"
                  className="visibility-toggle"
                  onClick={() => toggleApiKeyVisibility('curseforge')}
                  title={showApiKeys.curseforge ? 'Hide' : 'Show'}
                >
                  {showApiKeys.curseforge ? '🙈' : '👁️'}
                </button>
              </div>
            </div>

            <div className="api-key-item">
              <label className="api-key-label">
                Modrinth API Key
                <span className="key-description">
                  Required for importing mods from Modrinth
                </span>
              </label>
              <div className="api-key-input-group">
                <input
                  type={showApiKeys.modrinth ? 'text' : 'password'}
                  value={apiKeys.modrinth}
                  onChange={(e) => handleApiKeyChange('modrinth', e.target.value)}
                  onBlur={() => handleApiKeyBlur('modrinth')}
                  placeholder="Enter your Modrinth API key"
                  className="api-key-input"
                />
                <button
                  type="button"
                  className="visibility-toggle"
                  onClick={() => toggleApiKeyVisibility('modrinth')}
                  title={showApiKeys.modrinth ? 'Hide' : 'Show'}
                >
                  {showApiKeys.modrinth ? '🙈' : '👁️'}
                </button>
              </div>
            </div>
          </div>

          <div className="settings-section">
            <h3>API Key Status</h3>
            <div className="api-status-list">
              <div className={`api-status-item ${apiKeys.openai ? 'configured' : 'not-configured'}`}>
                <span className="status-icon">{apiKeys.openai ? '✅' : '❌'}</span>
                <span>OpenAI {apiKeys.openai ? 'configured' : 'not configured'}</span>
              </div>
              <div className={`api-status-item ${apiKeys.curseforge ? 'configured' : 'not-configured'}`}>
                <span className="status-icon">{apiKeys.curseforge ? '✅' : '❌'}</span>
                <span>CurseForge {apiKeys.curseforge ? 'configured' : 'not configured'}</span>
              </div>
              <div className={`api-status-item ${apiKeys.modrinth ? 'configured' : 'not-configured'}`}>
                <span className="status-icon">{apiKeys.modrinth ? '✅' : '❌'}</span>
                <span>Modrinth {apiKeys.modrinth ? 'configured' : 'not configured'}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// Hook for accessing settings from other components
// eslint-disable-next-line react-refresh/only-export-components
export const useSettings = () => {
  const [preferences, setPreferences] = useState<SettingsPreferences>({
    defaultSmartAssumptions: true,
    defaultIncludeDependencies: false,
    autoCheckUpdates: true,
    theme: 'auto',
    notifications: true,
  });

  useEffect(() => {
    const stored = localStorage.getItem('modporter_preferences');
    if (stored) {
      try {
        setPreferences(JSON.parse(stored));
      } catch (e) {
        console.error('Failed to load preferences:', e);
      }
    }
  }, []);

  const updatePreference = <K extends keyof SettingsPreferences>(
    key: K, 
    value: SettingsPreferences[K]
  ) => {
    const newPreferences = { ...preferences, [key]: value };
    setPreferences(newPreferences);
    localStorage.setItem('modporter_preferences', JSON.stringify(newPreferences));
  };

  return {
    preferences,
    updatePreference,
  };
};

export default Settings;
