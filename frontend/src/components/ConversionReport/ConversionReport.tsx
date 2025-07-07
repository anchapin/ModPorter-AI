/**
 * ConversionReport Component - PRD Feature 3: Interactive Conversion Report
 * Visual, comprehensive reporting of conversion results
 */

import React, { useState } from 'react';
import {
  ExtendedConversionResponse,
  ConversionStatus,
  ConversionStatusEnum,
  ConvertedMod,
  FailedMod,
  SmartAssumption
} from '../../types/api';
import { downloadResult } from '../../services/api';

interface ConversionReportProps {
  conversionResult?: ExtendedConversionResponse | ConversionStatus | null;
}

export const ConversionReport: React.FC<ConversionReportProps> = ({
  conversionResult,
}) => {
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  if (!conversionResult) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: '#ef4444' }}>
        <h2>Conversion Report Not Available</h2>
        <p>There was an issue loading the conversion details. Please try again later.</p>
      </div>
    );
  }

  const jobId = conversionResult.job_id;
  const status = conversionResult.status;
  const progress = conversionResult.progress || 0;
  const message = conversionResult.message;
  const error = conversionResult.error;
  
  // Extended properties for rich reporting (if available)
  const overallSuccessRate = (conversionResult as ExtendedConversionResponse).overallSuccessRate || 0;
  const convertedMods = (conversionResult as ExtendedConversionResponse).convertedMods || [];
  const failedMods = (conversionResult as ExtendedConversionResponse).failedMods || [];
  const smartAssumptionsApplied = (conversionResult as ExtendedConversionResponse).smartAssumptionsApplied || [];
  const detailedReport = (conversionResult as ExtendedConversionResponse).detailedReport;

  const getStatusColor = (currentStatus: string) => {
    switch (currentStatus) {
      case ConversionStatusEnum.COMPLETED: return '#10b981'; // green
      case ConversionStatusEnum.FAILED: return '#ef4444'; // red
      case ConversionStatusEnum.UPLOADING: // Added UPLOADING as suggested by Copilot
      case ConversionStatusEnum.IN_PROGRESS:
      case ConversionStatusEnum.ANALYZING:
      case ConversionStatusEnum.CONVERTING:
      case ConversionStatusEnum.PACKAGING:
      case ConversionStatusEnum.PENDING:
        return '#f59e0b'; // yellow
      default: return '#6b7280'; // gray
    }
  };

  const getSuccessRateColor = (rate: number) => {
    if (rate >= 80) return '#10b981'; // green
    if (rate >= 60) return '#f59e0b'; // yellow
    if (rate >= 40) return '#f97316'; // orange
    return '#ef4444'; // red
  };


  const handleDownload = async () => {
    if (!jobId) {
      setDownloadError('Job ID is missing, cannot download.');
      return;
    }
    setIsDownloading(true);
    setDownloadError(null);
    try {
      const blob = await downloadResult(jobId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${jobId}_converted_modpack.mcaddon`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      setDownloadError(err.message ? `Download error: ${err.message}` : 'Download failed. Please check your connection and try again.');
    } finally {
      setIsDownloading(false);
    }
  };

  // Handle cases where conversion is still processing or not yet started
  if (status === ConversionStatusEnum.PENDING ||
      status === ConversionStatusEnum.UPLOADING ||
      status === ConversionStatusEnum.IN_PROGRESS ||
      status === ConversionStatusEnum.ANALYZING ||
      status === ConversionStatusEnum.CONVERTING ||
      status === ConversionStatusEnum.PACKAGING) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <div role="progressbar" style={{ marginBottom: '1rem' }}>
          <div style={{ 
            width: '100%', 
            height: '8px', 
            backgroundColor: '#e5e7eb',
            borderRadius: '4px',
            overflow: 'hidden'
          }}>
            <div style={{
              width: `${progress}%`,
              height: '100%',
              backgroundColor: '#3b82f6',
              transition: 'width 0.3s ease'
            }} />
          </div>
        </div>
        <h2>Converting your mod...</h2>
        <p>Status: {status}</p>
        <p>Message: {message}</p>
        <p>Progress: {progress}%</p>
      </div>
    );
  }

  return (
    <div style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: '2rem', textAlign: 'center' }}>
        <h1 style={{ 
          color: getStatusColor(status),
          fontSize: '2rem',
          marginBottom: '0.5rem'
        }}>
          Conversion {status === ConversionStatusEnum.COMPLETED ? 'Complete' : status === ConversionStatusEnum.FAILED ? 'Failed' : 'Details'}
        </h1>
        
        {status === ConversionStatusEnum.FAILED && error && (
          <p style={{ color: getStatusColor(status), fontSize: '1.1rem', marginTop: '-0.5rem', marginBottom: '1rem' }}>
            <strong>Error:</strong> {error}
          </p>
        )}

        {status === ConversionStatusEnum.COMPLETED && overallSuccessRate > 0 && (
          <div style={{ fontSize: '1.25rem', marginBottom: '1rem' }}>
            <span style={{ color: getSuccessRateColor(overallSuccessRate) }}>
              {overallSuccessRate.toFixed(1)}% Overall Success Rate
            </span>
          </div>
        )}
      </div>

      {/* Download Section */}
      {status === ConversionStatusEnum.COMPLETED && (
        <div style={{ 
          backgroundColor: '#f0f9ff', 
          padding: '1rem', 
          borderRadius: '8px',
          marginBottom: '2rem',
          textAlign: 'center'
        }}>
          <h3>Your Bedrock Add-on is Ready!</h3>
          <button
            onClick={handleDownload}
            disabled={isDownloading}
            style={{
              display: 'inline-block',
              backgroundColor: isDownloading ? '#9ca3af' : '#3b82f6',
              color: 'white',
              padding: '0.75rem 1.5rem',
              borderRadius: '6px',
              border: 'none',
              cursor: isDownloading ? 'not-allowed' : 'pointer',
              fontWeight: 'bold',
              marginTop: '0.5rem'
            }}
          >
            {isDownloading ? 'Downloading...' : 'Download .mcaddon'}
          </button>
          {downloadError && <p style={{ color: 'red', marginTop: '0.5rem' }}>Error: {downloadError}</p>}
        </div>
      )}

      {/* Converted Mods */}
      {convertedMods && convertedMods.length > 0 && (
        <div style={{ marginBottom: '2rem' }}>
          <h3 style={{ color: '#10b981', marginBottom: '1rem' }}>
            ✅ Successfully Converted ({convertedMods.length})
          </h3>
          {convertedMods.map((mod: ConvertedMod, index: number) => (
            <div key={index} style={{ 
              border: '1px solid #d1d5db',
              borderRadius: '6px',
              padding: '1rem',
              marginBottom: '1rem'
            }}>
              <h4>{mod.name} {mod.version}</h4>
              <p>Status: <span style={{ color: mod.status === 'success' ? '#10b981' : mod.status === 'partial' ? '#f59e0b' : '#ef4444' }}>{mod.status}</span></p>
              {mod.warnings?.length > 0 && (
                <div>
                  <strong>Warnings:</strong>
                  <ul>
                    {mod.warnings.map((warning: string, i: number) => (
                      <li key={i} style={{ color: '#f59e0b' }}>{warning}</li>
                    ))}
                  </ul>
                </div>
              )}
              {/* Optionally display mod.features here */}
            </div>
          ))}
        </div>
      )}

      {/* Failed Mods */}
      {failedMods && failedMods.length > 0 && (
        <div style={{ marginBottom: '2rem' }}>
          <h3 style={{ color: '#ef4444', marginBottom: '1rem' }}>
            ❌ Failed to Convert ({failedMods.length})
          </h3>
          {failedMods.map((mod: FailedMod, index: number) => (
            <div key={index} style={{ 
              border: '1px solid #fca5a5',
              borderRadius: '6px',
              padding: '1rem',
              marginBottom: '1rem',
              backgroundColor: '#fef2f2'
            }}>
              <h4>{mod.name}</h4>
              <p><strong>Reason:</strong> {mod.reason}</p>
              {mod.suggestions?.length > 0 && (
                <div>
                  <strong>Suggestions:</strong>
                  <ul>
                    {mod.suggestions.map((suggestion: string, i: number) => (
                      <li key={i}>{suggestion}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Smart Assumptions */}
      {smartAssumptionsApplied && smartAssumptionsApplied.length > 0 && (
        <div style={{ marginBottom: '2rem' }}>
          <h3 style={{ color: '#8b5cf6', marginBottom: '1rem' }}>
            🧠 Smart Assumptions Applied ({smartAssumptionsApplied.length})
          </h3>
          {smartAssumptionsApplied.map((assumption: SmartAssumption, index: number) => (
            <div key={index} style={{ 
              border: '1px solid #c4b5fd',
              borderRadius: '6px',
              padding: '1rem',
              marginBottom: '1rem',
              backgroundColor: '#faf5ff'
            }}>
              <h4>Original: {assumption.originalFeature}</h4>
              <p><strong>Converted to:</strong> {assumption.assumptionApplied}</p>
              <p><strong>Impact:</strong> 
                <span style={{ 
                  color: assumption.impact === 'high' ? '#ef4444' : 
                        assumption.impact === 'medium' ? '#f59e0b' : '#10b981',
                  fontWeight: 'bold',
                  marginLeft: '0.5rem'
                }}>
                  {assumption.impact}
                </span>
              </p>
              <p>{assumption.description}</p>
            </div>
          ))}
        </div>
      )}

      {/* Technical Details */}
      {detailedReport && (
        <details style={{ marginTop: '2rem' }}>
          <summary style={{ 
            cursor: 'pointer', 
            fontWeight: 'bold',
            padding: '0.5rem',
            backgroundColor: '#f3f4f6',
            borderRadius: '4px'
          }}>
            Technical Details
          </summary>
          <div style={{ 
            padding: '1rem',
            backgroundColor: '#f9fafb',
            marginTop: '0.5rem',
            borderRadius: '4px',
            fontFamily: 'monospace',
            fontSize: '0.875rem'
          }}>
            <pre>{JSON.stringify(detailedReport, null, 2)}</pre>
          </div>
        </details>
      )}
    </div>
  );
};