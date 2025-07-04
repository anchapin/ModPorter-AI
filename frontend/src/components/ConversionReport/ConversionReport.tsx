/**
 * ConversionReport Component - PRD Feature 3: Interactive Conversion Report
 * Visual, comprehensive reporting of conversion results
 */

import React from 'react';
import { ConversionResponse } from '../../types/api';

interface ConversionReportProps {
  conversionResult: ConversionResponse;
}

export const ConversionReport: React.FC<ConversionReportProps> = ({
  conversionResult,
}) => {
  const { 
    status, 
    overallSuccessRate, 
    convertedMods, 
    failedMods, 
    smartAssumptionsApplied,
    downloadUrl,
    detailedReport 
  } = conversionResult;

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return '#10b981'; // green
      case 'failed': return '#ef4444'; // red
      case 'processing': return '#f59e0b'; // yellow
      default: return '#6b7280'; // gray
    }
  };

  const getSuccessRateColor = (rate: number) => {
    if (rate >= 80) return '#10b981'; // green
    if (rate >= 60) return '#f59e0b'; // yellow
    if (rate >= 40) return '#f97316'; // orange
    return '#ef4444'; // red
  };

  if (status === 'processing') {
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
              width: `${detailedReport.progress || 0}%`,
              height: '100%',
              backgroundColor: '#3b82f6',
              transition: 'width 0.3s ease'
            }} />
          </div>
        </div>
        <h2>Converting your mod...</h2>
        <p>Stage: {detailedReport.stage}</p>
        <p>Progress: {detailedReport.progress || 0}%</p>
      </div>
    );
  }

  return (
    <div style={{ padding: '2rem', maxWidth: '800px' }}>
      {/* Header */}
      <div style={{ marginBottom: '2rem', textAlign: 'center' }}>
        <h1 style={{ 
          color: getStatusColor(status),
          fontSize: '2rem',
          marginBottom: '0.5rem'
        }}>
          Conversion {status === 'completed' ? 'Complete' : 'Failed'}
        </h1>
        
        {status === 'completed' && (
          <div style={{ fontSize: '1.25rem', marginBottom: '1rem' }}>
            <span style={{ color: getSuccessRateColor(overallSuccessRate) }}>
              {overallSuccessRate.toFixed(1)}% Success Rate
            </span>
          </div>
        )}
      </div>

      {/* Download Section */}
      {downloadUrl && (
        <div style={{ 
          backgroundColor: '#f0f9ff', 
          padding: '1rem', 
          borderRadius: '8px',
          marginBottom: '2rem',
          textAlign: 'center'
        }}>
          <h3>Your Bedrock Add-on is Ready!</h3>
          <a 
            href={downloadUrl}
            download
            style={{
              display: 'inline-block',
              backgroundColor: '#3b82f6',
              color: 'white',
              padding: '0.75rem 1.5rem',
              borderRadius: '6px',
              textDecoration: 'none',
              fontWeight: 'bold',
              marginTop: '0.5rem'
            }}
          >
            Download .mcaddon
          </a>
        </div>
      )}

      {/* Converted Mods */}
      {convertedMods.length > 0 && (
        <div style={{ marginBottom: '2rem' }}>
          <h3 style={{ color: '#10b981', marginBottom: '1rem' }}>
            ✅ Successfully Converted ({convertedMods.length})
          </h3>
          {convertedMods.map((mod: any, index: number) => (
            <div key={index} style={{ 
              border: '1px solid #d1d5db',
              borderRadius: '6px',
              padding: '1rem',
              marginBottom: '1rem'
            }}>
              <h4>{mod.name} {mod.version}</h4>
              <p>Status: <span style={{ color: '#10b981' }}>{mod.status}</span></p>
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
            </div>
          ))}
        </div>
      )}

      {/* Failed Mods */}
      {failedMods.length > 0 && (
        <div style={{ marginBottom: '2rem' }}>
          <h3 style={{ color: '#ef4444', marginBottom: '1rem' }}>
            ❌ Failed to Convert ({failedMods.length})
          </h3>
          {failedMods.map((mod: any, index: number) => (
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
      {smartAssumptionsApplied.length > 0 && (
        <div style={{ marginBottom: '2rem' }}>
          <h3 style={{ color: '#8b5cf6', marginBottom: '1rem' }}>
            🧠 Smart Assumptions Applied ({smartAssumptionsApplied.length})
          </h3>
          {smartAssumptionsApplied.map((assumption: any, index: number) => (
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