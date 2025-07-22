/**
 * ConversionReport Component - PRD Feature 3: Interactive Conversion Report
 * Visual, comprehensive reporting of conversion results
 */

import React, { useState } from 'react'; // Added useState
import type {
  InteractiveReport,
  ModConversionStatus,
  FeedbackCreatePayload, // Added
  AssumptionDetail,
  FeatureConversionDetail,
  LogEntry,
} from '../../types/api';
import { submitFeedback } from '../../services/api'; // Added
import styles from './ConversionReport.module.css';

interface ConversionReportProps {
  conversionResult: InteractiveReport;
  jobStatus?: 'completed' | 'failed' | 'processing';
}

// Helper function for CSS class names
const getStatusClass = (status: string | undefined) => {
  if (!status) return '';
  status = status.toLowerCase();
  if (status.includes('success') || status.includes('converted')) return styles.colorSuccess;
  if (status.includes('partial')) return styles.colorWarning;
  if (status.includes('failed')) return styles.colorError;
  return styles.colorMuted;
};

const getImpactClass = (impact: string | undefined) => {
  if (!impact) return '';
  impact = impact.toLowerCase();
  if (impact === 'high') return styles.featureImpactHigh;
  if (impact === 'medium') return styles.featureImpactMedium;
  if (impact === 'low') return styles.featureImpactLow;
  return '';
};

const getModStatusClass = (status: string | undefined) => {
  if (!status) return '';
  status = status.toLowerCase();
  if (status.includes('success') || status.includes('converted')) return styles.modStatusSuccess;
  if (status.includes('partial')) return styles.modStatusPartial;
  if (status.includes('failed')) return styles.modStatusFailed;
  return '';
};

const getModItemClass = (status: string | undefined) => {
  if (!status) return styles.modItem;
  status = status.toLowerCase();
  if (status.includes('success') || status.includes('converted')) return `${styles.modItem} ${styles.modItemSuccess}`;
  if (status.includes('partial')) return `${styles.modItem} ${styles.modItemPartial}`;
  if (status.includes('failed')) return `${styles.modItem} ${styles.modItemFailed}`;
  return styles.modItem;
};

const getStatusIcon = (status: string | undefined) => {
  if (!status) return '⚪';
  status = status.toLowerCase();
  if (status.includes('success') || status.includes('converted')) return '✅';
  if (status.includes('partial')) return '⚠️';
  if (status.includes('failed')) return '❌';
  return '⚪';
};

const getImpactIcon = (impact: string | undefined) => {
  if (!impact) return '⚪';
  impact = impact.toLowerCase();
  if (impact === 'high') return '🔴';
  if (impact === 'medium') return '🟡';
  if (impact === 'low') return '🟢';
  return '⚪';
};

export const ConversionReport: React.FC<ConversionReportProps> = ({
  conversionResult,
  jobStatus
}) => {
  // Feedback state
  const [feedbackType, setFeedbackType] = useState<'thumbs_up' | 'thumbs_down' | null>(null);
  const [comment, setComment] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);
  const [submitStatus, setSubmitStatus] = useState<'success' | 'error' | null>(null);
  const [submitMessage, setSubmitMessage] = useState('');

  const handleDownloadReport = (event: React.MouseEvent<HTMLAnchorElement>) => {
    event.preventDefault();
    const pageHTML = document.documentElement.outerHTML;
    const blob = new Blob([pageHTML], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'conversion-report.html';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Feedback handlers
  const handleFeedbackTypeChange = (type: 'thumbs_up' | 'thumbs_down') => {
    if (feedbackType === type) {
      setFeedbackType(null); // Deselect if clicking the same button
    } else {
      setFeedbackType(type);
    }
  };

  const handleFeedbackSubmit = async () => {
    if (!feedbackType) {
      setSubmitStatus('error');
      setSubmitMessage('Please select thumbs up or thumbs down.');
      return;
    }

    setIsSubmitting(true);
    setSubmitStatus(null);
    setSubmitMessage('');

    try {
      const payload: FeedbackCreatePayload = {
        job_id: conversionResult.job_id,
        feedback_type: feedbackType,
        comment: comment || null,
        user_id: undefined, // Not implemented yet
      };

      await submitFeedback(payload);
      setFeedbackSubmitted(true);
      setSubmitStatus('success');
      setSubmitMessage('Thank you for your feedback!');
    } catch (error) {
      setSubmitStatus('error');
      setSubmitMessage(error instanceof Error ? error.message : 'Failed to submit feedback');
    } finally {
      setIsSubmitting(false);
    }
  };


  if (!conversionResult) {
    return (
      <div className={styles.errorContainer}>
        <h2>Conversion Report Not Available</h2>
        <p>There was an issue loading the conversion details. Please try again later.</p>
      </div>
    );
  }

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

  const displayStatus = jobStatus || (summary.overall_success_rate > 10 ? 'completed' : 'failed');

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.header}>
        <h1 className={`${styles.title} ${displayStatus === 'completed' ? styles.titleCompleted : displayStatus === 'failed' ? styles.titleFailed : styles.titleProcessing}`}>
          Conversion {displayStatus === 'completed' ? 'Report' : 'Failed'}
        </h1>
        <p className={styles.subtitle}>
          Job ID: {job_id} | Generated: {new Date(report_generation_date).toLocaleString()}
        </p>
      </div>

      {/* Summary Section */}
      <details open className={styles.summarySection}>
        <summary className={styles.summaryTitle}>Overall Summary</summary>
        <div className={styles.summaryGrid}>
          <div><strong>Overall Success Rate:</strong> <span className={`${styles.successRate} ${getStatusClass(summary.overall_success_rate.toString())}`}>{summary.overall_success_rate.toFixed(1)}%</span></div>
          <div><strong>Total Features:</strong> {summary.total_features}</div>
          <div><strong>Converted:</strong> {summary.converted_features}</div>
          <div><strong>Partially Converted:</strong> {summary.partially_converted_features}</div>
          <div><strong>Failed:</strong> {summary.failed_features}</div>
          <div><strong>Assumptions Applied:</strong> {summary.assumptions_applied_count}</div>
          <div><strong>Processing Time:</strong> {summary.processing_time_seconds.toFixed(2)}s</div>
        </div>
      </details>

      {/* Download Section */}
      {summary.download_url && (
        <div style={{
          marginBottom: '2rem',
          backgroundColor: '#f0f9ff',
          padding: '1.5rem',
          borderRadius: '8px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '1rem'
        }}>
          <h3 style={{ marginTop: 0, marginBottom: 0, color: '#1e40af' }}>Your Bedrock Add-on is Ready!</h3>
          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '1rem' }}>
            <a
              href={summary.download_url}
              download
              style={{
                display: 'inline-block',
                backgroundColor: '#007bff',
                color: 'white',
                padding: '1rem 2rem',
                borderRadius: '6px',
                textDecoration: 'none',
                fontWeight: 'bold',
                marginTop: '0.5rem',
                boxShadow: '0px 4px 8px rgba(0, 0, 0, 0.1)'
              }}
            >
              📥 Download .mcaddon
            </a>
            <a
              href="#"
              onClick={handleDownloadReport}
              style={{
                display: 'inline-block',
                backgroundColor: '#007bff',
                color: 'white',
                padding: '1rem 2rem',
                borderRadius: '6px',
                textDecoration: 'none',
                fontWeight: 'bold',
                marginTop: '0.5rem',
                boxShadow: '0px 4px 8px rgba(0, 0, 0, 0.1)'
              }}
            >
              📄 Download Report
            </a>
          </div>
        </div>
      )}

      {/* Feedback Section */}
      <div className={styles.feedbackSection}>
        <h3 className={styles.feedbackTitle}>Rate this Conversion</h3>
        {feedbackSubmitted ? (
          <div className={submitStatus === 'success' ? styles.feedbackSuccess : styles.colorError}>
            {submitMessage}
          </div>
        ) : (
          <>
            <div className={styles.feedbackButtons}>
              <button
                onClick={() => handleFeedbackTypeChange('thumbs_up')}
                className={`${styles.feedbackButton} ${feedbackType === 'thumbs_up' ? styles.feedbackButtonActive : ''}`}
                aria-pressed={feedbackType === 'thumbs_up'}
                title="Thumbs Up"
              >
                👍
              </button>
              <button
                onClick={() => handleFeedbackTypeChange('thumbs_down')}
                className={`${styles.feedbackButton} ${feedbackType === 'thumbs_down' ? styles.feedbackButtonActive : ''}`}
                aria-pressed={feedbackType === 'thumbs_down'}
                title="Thumbs Down"
              >
                👎
              </button>
            </div>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Optional: Add any comments here..."
              rows={4}
              className={styles.feedbackTextarea}
              disabled={isSubmitting}
            />
            <button
              onClick={handleFeedbackSubmit}
              disabled={isSubmitting || !feedbackType}
              className={styles.submitButton}
            >
              {isSubmitting ? 'Submitting...' : 'Submit Feedback'}
            </button>
            {submitStatus === 'error' && submitMessage && (
              <p className={styles.colorError}>Error: {submitMessage}</p>
            )}
          </>
        )}
      </div>

      {/* Converted Mods */}
      {converted_mods && converted_mods.length > 0 && (
        <details open className={styles.section}>
          <summary className={`${styles.sectionTitle} ${styles.colorSuccess}`}>
            {getStatusIcon('success')} Converted Mods ({converted_mods.length})
          </summary>
          <div className={styles.sectionContent}>
            {converted_mods.map((mod: ModConversionStatus, index: number) => (
              <div key={`converted-${index}`} className={getModItemClass(mod.status)}>
                <div className={styles.modHeader}>
                  <span className={styles.modName}>{getStatusIcon(mod.status)} {mod.name} <span className={styles.colorMuted}>v{mod.version}</span></span>
                  <span className={`${styles.modStatus} ${getModStatusClass(mod.status)}`}>{mod.status}</span>
                </div>
                {mod.warnings && mod.warnings.length > 0 && (
                  <div>
                    <strong>⚠️ Warnings:</strong>
                    <ul>
                      {mod.warnings.map((warning: string, i: number) => (
                        <li key={`warn-${i}`} className={styles.colorWarning}>{warning}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {/* Optionally display mod.features here */}
              </div>
            ))}
          </div>
        </details>
      )}

      {/* Failed Mods */}
      {failed_mods && failed_mods.length > 0 && (
        <details open className={styles.section}>
          <summary className={`${styles.sectionTitle} ${styles.colorError}`}>
            {getStatusIcon('failed')} Failed Mods ({failed_mods.length})
          </summary>
          <div className={styles.sectionContent}>
            {failed_mods.map((mod: ModConversionStatus, index: number) => (
              <div key={`failed-${index}`} className={getModItemClass(mod.status)}>
                <div className={styles.modHeader}>
                  <span className={styles.modName}>{getStatusIcon(mod.status)} {mod.name} <span className={styles.colorMuted}>v{mod.version}</span></span>
                  <span className={`${styles.modStatus} ${getModStatusClass(mod.status)}`}>{mod.status}</span>
                </div>
                {mod.errors && mod.errors.length > 0 && (
                  <div>
                    <strong>❌ Errors:</strong>
                    <ul>
                      {mod.errors.map((error: string, i: number) => (
                        <li key={`err-${i}`} className={styles.colorError}>{error}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}
          </div>
        </details>
      )}

      {/* Smart Assumptions Report */}
      {smart_assumptions_report && smart_assumptions_report.assumptions.length > 0 && (
        <details className={`${styles.section} ${styles.summarySection}`}>
          <summary className={styles.sectionTitle}>
            🧠 Detailed Smart Assumptions ({smart_assumptions_report.assumptions.length})
          </summary>
          <div className={styles.sectionContent}>
            <div className={styles.assumptionList}>
              {smart_assumptions_report.assumptions.map((assumption: AssumptionDetail, index: number) => (
                <div key={index} className={styles.assumptionItem}>
                  <div className={styles.assumptionHeader}>
                    <span className={styles.assumptionTitle}>Assumption ID: {assumption.assumption_id}</span>
                  </div>
                  <div className={styles.assumptionContent}>
                    <div className={styles.assumptionDetails}>
                      <div className={styles.assumptionDetail}>
                        <span className={styles.assumptionDetailLabel}>Feature Affected:</span>
                        <span className={styles.assumptionDetailValue}>{assumption.feature_affected}</span>
                      </div>
                      <div className={styles.assumptionDetail}>
                        <span className={styles.assumptionDetailLabel}>Description:</span>
                        <span className={styles.assumptionDetailValue}>{assumption.description}</span>
                      </div>
                      <div className={styles.assumptionDetail}>
                        <span className={styles.assumptionDetailLabel}>Reasoning:</span>
                        <span className={styles.assumptionDetailValue}>{assumption.reasoning}</span>
                      </div>
                      <div className={styles.assumptionDetail}>
                        <span className={styles.assumptionDetailLabel}>Impact:</span>
                        <span className={`${styles.assumptionDetailValue} ${getImpactClass(assumption.impact_level)}`}>
                          {getImpactIcon(assumption.impact_level)} {assumption.impact_level}
                        </span>
                      </div>
                      <div className={styles.assumptionDetail}>
                        <span className={styles.assumptionDetailLabel}>User Explanation:</span>
                        <span className={styles.assumptionDetailValue}>{assumption.user_explanation}</span>
                      </div>
                      {assumption.technical_notes && (
                        <div className={styles.assumptionDetail}>
                          <span className={styles.assumptionDetailLabel}>Technical Notes:</span>
                          <span className={styles.assumptionDetailValue}>{assumption.technical_notes}</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </details>
      )}

      {/* Feature Analysis */}
      {feature_analysis && (
        <details className={`${styles.section} ${styles.summarySection}`}>
          <summary className={`${styles.sectionTitle} ${styles.colorSuccess}`}>
            📊 Detailed Feature Analysis
          </summary>
          <div className={styles.sectionContent}>
            <p><strong>Overall Compatibility Summary:</strong> {feature_analysis.compatibility_mapping_summary}</p>
            {feature_analysis.visual_comparisons_overview && <p><strong>Visual Comparisons:</strong> {feature_analysis.visual_comparisons_overview}</p>}
            <p><strong>Impact Assessment:</strong> {feature_analysis.impact_assessment_summary}</p>

            <h4 className={`${styles.marginBottom} ${styles.colorSuccess}`}>Per-Feature Status:</h4>
            <div className={styles.featureGrid}>
              {feature_analysis.per_feature_status.map((feature: FeatureConversionDetail, index: number) => (
                <div key={index} className={styles.featureItem}>
                  <div className={styles.featureHeader}>
                    <span className={styles.featureName}>{getStatusIcon(feature.status)} {feature.feature_name}</span>
                    <span className={`${styles.featureImpact} ${getStatusClass(feature.status)}`}>{feature.status}</span>
                  </div>
                  <p className={styles.modDescription}><strong>Compatibility Notes:</strong> {feature.compatibility_notes}</p>
                  {feature.impact_of_assumption && <p className={styles.modDescription}><strong>Impact of Assumption:</strong> {feature.impact_of_assumption}</p>}
                  {/* Visual comparison fields can be added here if they contain URLs or text */}
                </div>
              ))}
            </div>
          </div>
        </details>
      )}

      {/* Developer Log */}
      {developer_log && (
        <details className={`${styles.section} ${styles.summarySection}`}>
          <summary className={styles.sectionTitle}>
            🛠️ Developer Technical Log
          </summary>
          <div className={styles.sectionContent}>
            <h4>Performance Metrics:</h4>
            <pre className={styles.featureCode}>{JSON.stringify(developer_log.performance_metrics, null, 2)}</pre>

            {developer_log.code_translation_details.length > 0 && (
              <>
                <h4 className={styles.marginBottom}>Code Translation Details:</h4>
                <div className={styles.logList}>
                  {developer_log.code_translation_details.map((log: LogEntry, i: number) => (
                    <div key={`ctd-${i}`} className={styles.logEntry}>
                      <span className={styles.logTimestamp}>{new Date(log.timestamp).toLocaleTimeString()}</span>
                      <span className={`${styles.logLevel} ${styles.logLevelInfo}`}>[{log.level}]:</span>
                      <span className={styles.logMessage}>{log.message}</span>
                    </div>
                  ))}
                </div>
              </>
            )}

            {developer_log.api_mapping_issues.length > 0 && (
              <>
                <h4 className={styles.marginBottom}>API Mapping Issues:</h4>
                <div className={styles.logList}>
                  {developer_log.api_mapping_issues.map((log: LogEntry, i: number) => (
                    <div key={`ami-${i}`} className={styles.logEntry}>
                      <span className={styles.logTimestamp}>{new Date(log.timestamp).toLocaleTimeString()}</span>
                      <span className={`${styles.logLevel} ${styles.logLevelWarn}`}>[{log.level}]:</span>
                      <span className={styles.logMessage}>{log.message}</span>
                    </div>
                  ))}
                </div>
              </>
            )}

            {developer_log.file_processing_log.length > 0 && (
              <>
                <h4 className={styles.marginBottom}>File Processing Log:</h4>
                <div className={styles.logList}>
                  {developer_log.file_processing_log.map((log: LogEntry, i: number) => (
                    <div key={`fpl-${i}`} className={styles.logEntry}>
                      <span className={styles.logTimestamp}>{new Date(log.timestamp).toLocaleTimeString()}</span>
                      <span className={`${styles.logLevel} ${styles.logLevelInfo}`}>[{log.level}]:</span>
                      <span className={styles.logMessage}>{log.message}</span>
                    </div>
                  ))}
                </div>
              </>
            )}

            {developer_log.error_summary.length > 0 && (
              <>
                <h4 className={styles.marginBottom}>Error Summary:</h4>
                <pre className={styles.featureCode}>{JSON.stringify(developer_log.error_summary, null, 2)}</pre>
              </>
            )}
          </div>
        </details>
      )}
    </div>
  );
};