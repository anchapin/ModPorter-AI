/**
 * Settings Page
 * Configuration and user preferences
 */

import React, { useState } from 'react';
import './Settings.css';

interface SettingsState {
  apiKey: string;
  defaultTargetVersion: string;
  autoDeleteAfterDays: number;
  enableNotifications: boolean;
  maxConcurrentConversions: number;
}

export const Settings: React.FC = () => {
  const [settings, setSettings] = useState<SettingsState>({
    apiKey: '',
    defaultTargetVersion: '1.20.0',
    autoDeleteAfterDays: 30,
    enableNotifications: true,
    maxConcurrentConversions: 3
  });
  
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    // Save to localStorage for demo purposes
    localStorage.setItem('modporter_settings', JSON.stringify(settings));
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleChange = (key: keyof SettingsState, value: string | number | boolean) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  return (
    <div className="settings-page">
      <div className="settings-header">
        <h1>⚙️ Settings</h1>
        <p>Configure your ModPorter AI preferences</p>
      </div>

      <div className="settings-content">
        <div className="settings-section">
          <h2>API Configuration</h2>
          <div className="form-group">
            <label htmlFor="apiKey">API Key</label>
            <input
              type="password"
              id="apiKey"
              value={settings.apiKey}
              onChange={(e) => handleChange('apiKey', e.target.value)}
              placeholder="Enter your API key"
            />
            <span className="help-text">Required for AI-powered conversions</span>
          </div>
          
          <div className="form-group">
            <label htmlFor="targetVersion">Default Target Version</label>
            <select
              id="targetVersion"
              value={settings.defaultTargetVersion}
              onChange={(e) => handleChange('defaultTargetVersion', e.target.value)}
            >
              <option value="1.20.0">1.20.0 (Wild Update)</option>
              <option value="1.19.0">1.19.0 (The Wild Update)</option>
              <option value="1.18.0">1.18.0 (Caves & Cliffs II)</option>
              <option value="1.17.0">1.17.0 (Caves & Cliffs I)</option>
            </select>
          </div>
        </div>

        <div className="settings-section">
          <h2>Conversion Settings</h2>
          <div className="form-group">
            <label htmlFor="maxConcurrent">Max Concurrent Conversions</label>
            <input
              type="number"
              id="maxConcurrent"
              min={1}
              max={10}
              value={settings.maxConcurrentConversions}
              onChange={(e) => handleChange('maxConcurrentConversions', parseInt(e.target.value))}
            />
            <span className="help-text">Number of conversions to run in parallel (1-10)</span>
          </div>
          
          <div className="form-group">
            <label htmlFor="autoDelete">Auto-delete old conversions after (days)</label>
            <input
              type="number"
              id="autoDelete"
              min={1}
              max={365}
              value={settings.autoDeleteAfterDays}
              onChange={(e) => handleChange('autoDeleteAfterDays', parseInt(e.target.value))}
            />
          </div>
        </div>

        <div className="settings-section">
          <h2>Notifications</h2>
          <div className="form-group checkbox-group">
            <label>
              <input
                type="checkbox"
                checked={settings.enableNotifications}
                onChange={(e) => handleChange('enableNotifications', e.target.checked)}
              />
              Enable email notifications
            </label>
            <span className="help-text">Get notified when conversions complete or fail</span>
          </div>
        </div>

        <div className="settings-actions">
          <button className="save-button" onClick={handleSave}>
            {saved ? '✓ Saved!' : 'Save Settings'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default Settings;
