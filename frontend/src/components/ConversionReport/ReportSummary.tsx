/**
 * ReportSummary Component - Enhanced summary section for conversion reports
 * Part of Issue #10 - Conversion Report Generation System
 */

import React from 'react';
import type { SummaryReport } from '../../types/api';
import styles from './ConversionReport.module.css';

interface ReportSummaryProps {
  summary: SummaryReport;
}

const CircularProgress: React.FC<{ value: number; size?: number }> = ({ value, size = 120 }) => {
  const circumference = 2 * Math.PI * 45;
  const strokeDasharray = circumference;
  const strokeDashoffset = circumference - (value / 100) * circumference;
  
  const getColor = (value: number) => {
    if (value >= 80) return '#28a745';
    if (value >= 60) return '#ffc107';
    return '#dc3545';
  };

  return (
    <div className={styles.circularProgress} style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox="0 0 100 100">
        <circle
          cx="50"
          cy="50"
          r="45"
          fill="none"
          stroke="#e0e0e0"
          strokeWidth="8"
        />
        <circle
          cx="50"
          cy="50"
          r="45"
          fill="none"
          stroke={getColor(value)}
          strokeWidth="8"
          strokeDasharray={strokeDasharray}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          transform="rotate(-90 50 50)"
          style={{ transition: 'stroke-dashoffset 0.5s ease-in-out' }}
        />
        <text
          x="50"
          y="50"
          textAnchor="middle"
          dy="0.3em"
          fontSize="16"
          fontWeight="bold"
          fill={getColor(value)}
        >
          {value.toFixed(1)}%
        </text>
      </svg>
    </div>
  );
};

const StatCard: React.FC<{ title: string; value: string | number; icon?: string; color?: string }> = ({ 
  title, 
  value, 
  icon = '',
  color = '#007bff'
}) => (
  <div className={styles.statCard}>
    <div className={styles.statIcon} style={{ color }}>
      {icon}
    </div>
    <div className={styles.statContent}>
      <div className={styles.statValue} style={{ color }}>
        {value}
      </div>
      <div className={styles.statTitle}>
        {title}
      </div>
    </div>
  </div>
);

const DownloadButton: React.FC<{ url: string }> = ({ url }) => (
  <a
    href={url}
    download
    className={styles.downloadButton}
    title="Download converted add-on"
  >
    📥 Download .mcaddon
  </a>
);

const QualityIndicator: React.FC<{ score: number }> = ({ score }) => {
  const getQualityLabel = (score: number) => {
    if (score >= 90) return 'Excellent';
    if (score >= 80) return 'Good';
    if (score >= 60) return 'Fair';
    if (score >= 40) return 'Poor';
    return 'Needs Improvement';
  };

  const getQualityColor = (score: number) => {
    if (score >= 80) return '#28a745';
    if (score >= 60) return '#ffc107';
    return '#dc3545';
  };

  return (
    <div className={styles.qualityIndicator}>
      <div className={styles.qualityBar}>
        <div 
          className={styles.qualityFill}
          style={{ 
            width: `${score}%`,
            backgroundColor: getQualityColor(score)
          }}
        />
      </div>
      <div className={styles.qualityLabel} style={{ color: getQualityColor(score) }}>
        {getQualityLabel(score)} ({score.toFixed(1)})
      </div>
    </div>
  );
};

const RecommendedActions: React.FC<{ actions: string[] }> = ({ actions }) => {
  if (!actions || actions.length === 0) return null;

  return (
    <div className={styles.recommendedActions}>
      <h4 className={styles.actionsTitle}>💡 Recommended Actions</h4>
      <ul className={styles.actionsList}>
        {actions.map((action, index) => (
          <li key={index} className={styles.actionItem}>
            {action}
          </li>
        ))}
      </ul>
    </div>
  );
};

export const ReportSummary: React.FC<ReportSummaryProps> = ({ summary }) => {
  const {
    overall_success_rate,
    total_features,
    converted_features,
    partially_converted_features,
    failed_features,
    assumptions_applied_count,
    processing_time_seconds,
    download_url,
    total_files_processed,
    output_size_mb,
    conversion_quality_score,
    recommended_actions
  } = summary;

  return (
    <div className={styles.reportSummary}>
      {/* Main Success Rate Display */}
      <div className={styles.summaryHeader}>
        <div className={styles.successRateContainer}>
          <CircularProgress value={overall_success_rate} />
          <div className={styles.successRateInfo}>
            <h3>Overall Success Rate</h3>
            <p className={styles.successRateDescription}>
              {overall_success_rate >= 90 ? 'Excellent conversion results!' :
               overall_success_rate >= 70 ? 'Good conversion with minor issues' :
               overall_success_rate >= 50 ? 'Moderate success, review needed' :
               'Conversion needs attention'}
            </p>
          </div>
        </div>
        
        {/* Quality Score */}
        <div className={styles.qualitySection}>
          <h4>Conversion Quality</h4>
          <QualityIndicator score={conversion_quality_score || 0} />
        </div>
      </div>

      {/* Statistics Grid */}
      <div className={styles.statsGrid}>
        <StatCard 
          title="Total Features" 
          value={total_features} 
          icon="🎯"
          color="#007bff"
        />
        <StatCard 
          title="Converted" 
          value={converted_features} 
          icon="✅"
          color="#28a745"
        />
        <StatCard 
          title="Partial" 
          value={partially_converted_features} 
          icon="⚠️"
          color="#ffc107"
        />
        <StatCard 
          title="Failed" 
          value={failed_features} 
          icon="❌"
          color="#dc3545"
        />
        <StatCard 
          title="Assumptions" 
          value={assumptions_applied_count} 
          icon="🧠"
          color="#6f42c1"
        />
        <StatCard 
          title="Processing Time" 
          value={`${processing_time_seconds.toFixed(1)}s`} 
          icon="⏱️"
          color="#17a2b8"
        />
      </div>

      {/* Additional Metrics */}
      {(total_files_processed > 0 || output_size_mb > 0) && (
        <div className={styles.additionalMetrics}>
          <h4>Processing Details</h4>
          <div className={styles.metricsGrid}>
            {total_files_processed > 0 && (
              <div className={styles.metric}>
                <span className={styles.metricLabel}>Files Processed:</span>
                <span className={styles.metricValue}>{total_files_processed}</span>
              </div>
            )}
            {output_size_mb > 0 && (
              <div className={styles.metric}>
                <span className={styles.metricLabel}>Output Size:</span>
                <span className={styles.metricValue}>{output_size_mb.toFixed(1)} MB</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Download Section */}
      {download_url && (
        <div className={styles.downloadSection}>
          <h4>Download Results</h4>
          <DownloadButton url={download_url} />
        </div>
      )}

      {/* Recommended Actions */}
      <RecommendedActions actions={recommended_actions || []} />
    </div>
  );
};