/**
 * ConversionReport Component - PRD Feature 3: Interactive Conversion Report
 * Visual, comprehensive reporting of conversion results
 */
import React from 'react';
import {
  InteractiveReport,
  SummaryReport,
  ModConversionStatus,
  FeatureAnalysis,
  AssumptionsReport,
  DeveloperLog,
  AssumptionDetail,
  FeatureConversionDetail,
  LogEntry,
} from '../../types/api';

interface ConversionReportProps {
  conversionResult: InteractiveReport;
  // Optional: jobStatus can be 'completed' | 'failed' if passed from parent
  // to determine the main title, otherwise we infer from summary.
  jobStatus?: 'completed' | 'failed' | 'processing'; // 'processing' would mean this component shouldn't render fully.
}

// Helper function for styling status strings
const getStatusColor = (status: string | undefined) => {
  if (!status) return '#6b7280'; // gray for undefined
  status = status.toLowerCase();
  if (status.includes('success') || status.includes('converted')) return '#10b981'; // green
  if (status.includes('partial')) return '#f59e0b'; // yellow
  if (status.includes('failed')) return '#ef4444'; // red
  return '#6b7280'; // gray
};

const getImpactColor = (impact: string | undefined) => {
  if (!impact) return '#6b7280';
  impact = impact.toLowerCase();
  if (impact === 'high') return '#ef4444';
  if (impact === 'medium') return '#f59e0b';
  if (impact === 'low') return '#10b981';
  return '#6b7280';
};


export const ConversionReport: React.FC<ConversionReportProps> = ({
  conversionResult,
  jobStatus // if passed from parent
}) => {
  const {
    summary,
    converted_mods,
    failed_mods,
    feature_analysis,
    smart_assumptions_report,
    developer_log,
    job_id,
    report_generation_date,
  } = conversionResult;

  // Determine overall status for display - parent might pass this, or we infer
  const displayStatus = jobStatus || (summary.overall_success_rate > 10 ? 'completed' : 'failed');

  const getSuccessRateColor = (rate: number) => {
    if (rate >= 80) return '#10b981';
    if (rate >= 60) return '#f59e0b';
    if (rate >= 40) return '#f97316';
    return '#ef4444';
  };

  // This component should ideally not render if status is 'processing'.
  // That should be handled by a parent component showing a progress bar.
  // If by mistake it's called with processing, show a minimal message.
  if (jobStatus === 'processing') {
    return <div style={{ padding: '2rem', textAlign: 'center' }}>Report is being generated...</div>;
  }

  // Icon helper functions and constants
  const STATUS_ICONS = {
    success: '✅',
    completed: '✅',
    converted: '✅',
    partial: '⚠️',
    warning: '⚠️',
    failed: '❌',
    error: '❌',
    unknown: '❓',
  };

  const getStatusIcon = (status: string | undefined): string => {
    if (!status) return STATUS_ICONS.unknown;
    const lowerStatus = status.toLowerCase();
    if (lowerStatus.includes('success') || lowerStatus.includes('completed') || lowerStatus.includes('converted')) return STATUS_ICONS.success;
    if (lowerStatus.includes('partial')) return STATUS_ICONS.partial;
    if (lowerStatus.includes('fail') || lowerStatus.includes('error')) return STATUS_ICONS.failed;
    if (lowerStatus.includes('warning')) return STATUS_ICONS.warning;
    return STATUS_ICONS.unknown;
  };

  const IMPACT_ICONS = { low: '🟢', medium: '🟡', high: '🔴', unknown: '⚪️' };

  const getImpactIcon = (impact: string | undefined): string => {
    if (!impact) return IMPACT_ICONS.unknown;
    const lowerImpact = impact.toLowerCase();
    if (lowerImpact === 'low') return IMPACT_ICONS.low;
    if (lowerImpact === 'medium') return IMPACT_ICONS.medium;
    if (lowerImpact === 'high') return IMPACT_ICONS.high;
    return IMPACT_ICONS.unknown;
  };

  const derivedOverallStatus = summary.overall_success_rate >= 80 ? 'completed' :
                             summary.overall_success_rate >= 40 ? 'partial success' : 'failed';


  const handleDownloadJson = () => {
    if (!conversionResult) return;

    const jsonString = JSON.stringify(conversionResult, null, 2);
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    // Use job_id from conversionResult for the filename
    const fileName = `conversion_report_${conversionResult.job_id || 'details'}.json`;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url); // Clean up
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '900px', margin: '0 auto', fontFamily: 'Arial, sans-serif' }}>
      {/* Header */}
      <div style={{ marginBottom: '1rem', paddingBottom: '1rem', borderBottom: '1px solid #e5e7eb', textAlign: 'center' }}>
        <h1 style={{
          color: getStatusColor(displayStatus), // displayStatus already considers overall success
          fontSize: '2.25rem',
          marginBottom: '0.25rem',
        }}>
          {getStatusIcon(derivedOverallStatus)} Conversion {displayStatus === 'completed' ? 'Report' : 'Failed'}
        </h1>
        <p style={{ color: '#6b7280', fontSize: '0.9rem', marginTop: '0', marginBottom: '0.75rem' }}>
          Job ID: {job_id} | Generated: {new Date(report_generation_date).toLocaleString()}
        </p>
        <button
          onClick={handleDownloadJson}
          style={{
            display: 'inline-block',
            backgroundColor: '#4A5568', // Neutral dark gray
            color: 'white',
            padding: '0.5rem 1rem',
            borderRadius: '6px',
            textDecoration: 'none',
            fontWeight: 'bold',
            border: 'none',
            cursor: 'pointer',
            transition: 'background-color 0.2s ease',
          }}
          onMouseOver={(e) => (e.currentTarget.style.backgroundColor = '#2D3748')}
          onMouseOut={(e) => (e.currentTarget.style.backgroundColor = '#4A5568')}
        >
          Download Report (JSON)
        </button>
      </div>

      {/* Summary Section */}
      <details open style={{ marginBottom: '2rem', backgroundColor: '#f9fafb', padding: '1.5rem', borderRadius: '8px' }}>
        <summary style={{ fontWeight: 'bold', fontSize: '1.25rem', cursor: 'pointer', color: '#374151' }}>📋 Overall Summary</summary>
        <div style={{ marginTop: '1rem', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
          <div><strong>Overall Success Rate:</strong> <span style={{ color: getSuccessRateColor(summary.overall_success_rate), fontWeight: 'bold' }}>{summary.overall_success_rate.toFixed(1)}%</span></div>
          <div><strong>Total Features:</strong> {summary.total_features}</div>
          <div><strong>Converted:</strong> {summary.converted_features}</div>
          <div><strong>Partially Converted:</strong> {summary.partially_converted_features}</div>
          <div><strong>Failed:</strong> {summary.failed_features}</div>
          <div><strong>Assumptions Applied:</strong> {summary.assumptions_applied_count}</div>
          <div><strong>Processing Time:</strong> {summary.processing_time_seconds.toFixed(2)}s</div>
        </div>
        {summary.download_url && (
          <div style={{ marginTop: '1.5rem', textAlign: 'center', backgroundColor: '#e0f2fe', padding: '1rem', borderRadius: '6px' }}>
            <h3 style={{marginTop: 0, marginBottom: '0.75rem', color: '#0c4a6e'}}>Your Bedrock Add-on is Ready!</h3>
            <a
              href={summary.download_url}
              download
              style={{
                display: 'inline-block', backgroundColor: '#2563eb', color: 'white',
                padding: '0.75rem 1.5rem', borderRadius: '6px', textDecoration: 'none', fontWeight: 'bold',
              }}
            >
              Download .mcaddon
            </a>
          </div>
        )}
         <div style={{marginTop: '1rem'}}>
            <strong>Quick Statistics:</strong>
            <pre style={{fontSize: '0.8rem', backgroundColor: '#fff', padding: '0.5rem', borderRadius: '4px', overflowX: 'auto'}}>
              {JSON.stringify(summary.quick_statistics, null, 2)}
            </pre>
        </div>
      </details>

      {/* Converted/Failed Mods Shared Styling */}
      const modCardStyle: React.CSSProperties = {
        border: '1px solid #e5e7eb', borderRadius: '6px', padding: '1rem', marginBottom: '1rem', backgroundColor: 'white'
      };

      {/* Converted Mods */}
      {converted_mods && converted_mods.length > 0 && (
        <details open style={{ marginBottom: '2rem' }}>
          <summary style={{ fontWeight: 'bold', fontSize: '1.25rem', cursor: 'pointer', color: '#166534' }}>
            {getStatusIcon('success')} Converted Mods ({converted_mods.length})
          </summary>
          {converted_mods.map((mod: ModConversionStatus, index: number) => (
            <div key={`converted-${index}`} style={{...modCardStyle, borderLeft: `5px solid ${getStatusColor(mod.status)}`}}>
              <h4>{getStatusIcon(mod.status)} {mod.name} <span style={{fontSize: '0.85rem', color: '#6b7280'}}>v{mod.version}</span></h4>
              <p>Status: <span style={{ color: getStatusColor(mod.status), fontWeight: 'bold' }}>{mod.status}</span></p>
              {mod.warnings && mod.warnings.length > 0 && (
                <div>
                  <strong>⚠️ Warnings:</strong>
                  <ul style={{paddingLeft: '20px', margin: '0.5rem 0', fontSize: '0.9rem'}}>
                    {mod.warnings.map((warning: string, i: number) => (
                      <li key={`warn-${i}`} style={{ color: '#d97706' }}>{warning}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ))}
        </details>
      )}

      {/* Failed Mods */}
      {failed_mods && failed_mods.length > 0 && (
        <details open style={{ marginBottom: '2rem' }}>
          <summary style={{ fontWeight: 'bold', fontSize: '1.25rem', cursor: 'pointer', color: '#991b1b' }}>
            {getStatusIcon('failed')} Failed Mods ({failed_mods.length})
          </summary>
          {failed_mods.map((mod: ModConversionStatus, index: number) => (
            <div key={`failed-${index}`} style={{...modCardStyle, borderLeft: `5px solid ${getStatusColor(mod.status)}`, backgroundColor: '#fff1f2'}}>
              <h4>{getStatusIcon(mod.status)} {mod.name} <span style={{fontSize: '0.85rem', color: '#6b7280'}}>v{mod.version}</span></h4>
              <p>Status: <span style={{ color: getStatusColor(mod.status), fontWeight: 'bold' }}>{mod.status}</span></p>
              {mod.errors && mod.errors.length > 0 && (
                <div>
                  <strong>❌ Errors:</strong>
                  <ul style={{paddingLeft: '20px', margin: '0.5rem 0', fontSize: '0.9rem'}}>
                    {mod.errors.map((error: string, i: number) => (
                      <li key={`err-${i}`} style={{ color: '#dc2626' }}>{error}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ))}
        </details>
      )}

      {/* Smart Assumptions Report */}
      {smart_assumptions_report && smart_assumptions_report.assumptions.length > 0 && (
        <details style={{ marginBottom: '2rem', backgroundColor: '#f5f3ff', padding: '1.5rem', borderRadius: '8px'  }}>
          <summary style={{ fontWeight: 'bold', fontSize: '1.25rem', cursor: 'pointer', color: '#5b21b6' }}>
            🧠 Detailed Smart Assumptions ({smart_assumptions_report.assumptions.length})
          </summary>
          {smart_assumptions_report.assumptions.map((assumption: AssumptionDetail, index: number) => (
            <div key={index} style={{ border: '1px solid #ddd6fe', padding: '1rem', margin: '1rem 0', borderRadius: '6px', backgroundColor: 'white' }}>
              <h4 style={{marginTop: 0, color: '#4c1d95'}}>Assumption ID: {assumption.assumption_id}</h4>
              <p><strong>Feature Affected:</strong> {assumption.feature_affected}</p>
              <p><strong>Description:</strong> {assumption.description}</p>
              <p><strong>Reasoning:</strong> {assumption.reasoning}</p>
              <p><strong>Impact:</strong> {getImpactIcon(assumption.impact_level)} <span style={{color: getImpactColor(assumption.impact_level), fontWeight: 'bold'}}>{assumption.impact_level}</span></p>
              <p><strong>User Explanation:</strong> {assumption.user_explanation}</p>
              {assumption.technical_notes && <p><strong>Technical Notes:</strong> {assumption.technical_notes}</p>}
            </div>
          ))}
        </details>
      )}

      {/* Feature Analysis */}
      {feature_analysis && (
        <details style={{ marginBottom: '2rem', backgroundColor: '#f0fdf4', padding: '1.5rem', borderRadius: '8px' }}>
          <summary style={{ fontWeight: 'bold', fontSize: '1.25rem', cursor: 'pointer', color: '#15803d' }}>
            📊 Detailed Feature Analysis
          </summary>
          <div style={{marginTop: '1rem'}}>
            <p><strong>Overall Compatibility Summary:</strong> {feature_analysis.compatibility_mapping_summary}</p>
            {feature_analysis.visual_comparisons_overview && <p><strong>Visual Comparisons:</strong> {feature_analysis.visual_comparisons_overview}</p>}
            <p><strong>Impact Assessment:</strong> {feature_analysis.impact_assessment_summary}</p>

            <h4 style={{marginTop: '1.5rem', color: '#166534'}}>Per-Feature Status:</h4>
            {feature_analysis.per_feature_status.map((feature: FeatureConversionDetail, index: number) => (
              <div key={index} style={{ border: '1px solid #bbf7d0', padding: '1rem', margin: '0.5rem 0', borderRadius: '6px', backgroundColor: 'white' }}>
                <h5 style={{marginTop: 0, color: '#14532d'}}>{getStatusIcon(feature.status)} {feature.feature_name} - <span style={{color: getStatusColor(feature.status), fontWeight: 'bold'}}>{feature.status}</span></h5>
                <p><strong>Compatibility Notes:</strong> {feature.compatibility_notes}</p>
                {feature.impact_of_assumption && <p><strong>Impact of Assumption:</strong> {feature.impact_of_assumption}</p>}
                {/* Visual comparison fields can be added here if they contain URLs or text */}
              </div>
            ))}
          </div>
        </details>
      )}

      {/* Developer Log */}
      {developer_log && (
        <details style={{ marginBottom: '2rem', backgroundColor: '#f1f5f9', padding: '1.5rem', borderRadius: '8px' }}>
          <summary style={{ fontWeight: 'bold', fontSize: '1.25rem', cursor: 'pointer', color: '#0f172a' }}>
            🛠️ Developer Technical Log
          </summary>
          <div style={{marginTop: '1rem', fontSize: '0.9rem', fontFamily: 'monospace'}}>
            <h4>Performance Metrics:</h4>
            <pre style={{backgroundColor: '#e2e8f0', padding: '0.75rem', borderRadius: '4px', overflowX: 'auto'}}>{JSON.stringify(developer_log.performance_metrics, null, 2)}</pre>

            {developer_log.code_translation_details.length > 0 && (<>
              <h4 style={{marginTop: '1rem'}}>Code Translation Details:</h4>
              {developer_log.code_translation_details.map((log: LogEntry, i: number) => (
                <div key={`ctd-${i}`} style={{padding: '0.25rem 0', borderBottom: '1px dashed #cbd5e1'}}>
                  <span style={{color: '#475569'}}>{new Date(log.timestamp).toLocaleTimeString()}</span> [{log.level}]: {log.message}
                </div>
              ))}
            </>)}

            {developer_log.api_mapping_issues.length > 0 && (<>
              <h4 style={{marginTop: '1rem'}}>API Mapping Issues:</h4>
              {developer_log.api_mapping_issues.map((log: LogEntry, i: number) => (
                <div key={`ami-${i}`} style={{padding: '0.25rem 0', borderBottom: '1px dashed #cbd5e1'}}>
                  <span style={{color: '#475569'}}>{new Date(log.timestamp).toLocaleTimeString()}</span> [{log.level}]: {log.message}
                </div>
              ))}
            </>)}

            {developer_log.file_processing_log.length > 0 && (<>
              <h4 style={{marginTop: '1rem'}}>File Processing Log:</h4>
              {developer_log.file_processing_log.map((log: LogEntry, i: number) => (
                <div key={`fpl-${i}`} style={{padding: '0.25rem 0', borderBottom: '1px dashed #cbd5e1'}}>
                  <span style={{color: '#475569'}}>{new Date(log.timestamp).toLocaleTimeString()}</span> [{log.level}]: {log.message}
                </div>
              ))}
            </>)}

            {developer_log.error_summary.length > 0 && (<>
              <h4 style={{marginTop: '1rem'}}>Error Summary:</h4>
              <pre style={{backgroundColor: '#e2e8f0', padding: '0.75rem', borderRadius: '4px', overflowX: 'auto'}}>{JSON.stringify(developer_log.error_summary, null, 2)}</pre>
            </>)}
          </div>
        </details>
      )}
    </div>
  );
};