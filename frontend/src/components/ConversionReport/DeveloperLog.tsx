/**
 * DeveloperLog Component - Enhanced technical log viewer
 * Part of Issue #10 - Conversion Report Generation System
 */

import React, { useState, useMemo } from 'react';
import type { DeveloperLog as DeveloperLogType, LogEntry } from '../../types/api';
import styles from './ConversionReport.module.css';

interface DeveloperLogProps {
  log: DeveloperLogType;
  isExpanded: boolean;
  onToggle: () => void;
}

interface LogSectionProps {
  title: string;
  logs: LogEntry[];
  icon?: string;
}

interface PerformanceMetricsProps {
  metrics: Record<string, any>;
}

const LogLevelBadge: React.FC<{ level: string }> = ({ level }) => {
  const getLevelInfo = (level: string) => {
    switch (level.toUpperCase()) {
      case 'ERROR':
        return { color: '#dc3545', bg: '#f8d7da', icon: '❌' };
      case 'WARNING':
      case 'WARN':
        return { color: '#ffc107', bg: '#fff3cd', icon: '⚠️' };
      case 'INFO':
        return { color: '#17a2b8', bg: '#d1ecf1', icon: 'ℹ️' };
      case 'DEBUG':
        return { color: '#6c757d', bg: '#f8f9fa', icon: '🔍' };
      default:
        return { color: '#6c757d', bg: '#f8f9fa', icon: '📝' };
    }
  };

  const levelInfo = getLevelInfo(level);

  return (
    <span 
      className={styles.logLevelBadge}
      style={{ 
        backgroundColor: levelInfo.bg,
        color: levelInfo.color,
        border: `1px solid ${levelInfo.color}40`
      }}
    >
      {levelInfo.icon} {level.toUpperCase()}
    </span>
  );
};

const LogEntryComponent: React.FC<{ entry: LogEntry }> = ({ entry }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className={styles.logEntry}>
      <div className={styles.logHeader}>
        <span className={styles.logTimestamp}>
          {new Date(entry.timestamp).toLocaleTimeString()}
        </span>
        <LogLevelBadge level={entry.level} />
        {entry.details && (
          <button 
            className={styles.logExpandButton}
            onClick={() => setIsExpanded(!isExpanded)}
            aria-label={isExpanded ? 'Hide details' : 'Show details'}
          >
            {isExpanded ? '▼' : '▶'}
          </button>
        )}
      </div>
      <div className={styles.logMessage}>
        {entry.message}
      </div>
      {isExpanded && entry.details && (
        <div className={styles.logDetails}>
          <pre className={styles.logDetailsContent}>
            {JSON.stringify(entry.details, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
};

const LogSection: React.FC<LogSectionProps> = ({ title, logs, icon = '📋' }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [levelFilter, setLevelFilter] = useState('all');

  const filteredLogs = useMemo(() => {
    if (levelFilter === 'all') return logs;
    return logs.filter(log => log.level.toLowerCase() === levelFilter.toLowerCase());
  }, [logs, levelFilter]);

  const logCounts = useMemo(() => {
    const counts = { error: 0, warning: 0, info: 0, debug: 0 };
    logs.forEach(log => {
      const level = log.level.toLowerCase();
      if (level === 'error') counts.error++;
      else if (level === 'warning' || level === 'warn') counts.warning++;
      else if (level === 'info') counts.info++;
      else if (level === 'debug') counts.debug++;
    });
    return counts;
  }, [logs]);

  if (logs.length === 0) return null;

  return (
    <div className={styles.logSection}>
      <div className={styles.logSectionHeader} onClick={() => setIsExpanded(!isExpanded)}>
        <h4 className={styles.logSectionTitle}>
          {icon} {title} ({logs.length})
        </h4>
        <div className={styles.logCounts}>
          {logCounts.error > 0 && (
            <span className={styles.logCount} style={{ color: '#dc3545' }}>
              {logCounts.error} errors
            </span>
          )}
          {logCounts.warning > 0 && (
            <span className={styles.logCount} style={{ color: '#ffc107' }}>
              {logCounts.warning} warnings
            </span>
          )}
          {logCounts.info > 0 && (
            <span className={styles.logCount} style={{ color: '#17a2b8' }}>
              {logCounts.info} info
            </span>
          )}
        </div>
        <button 
          className={styles.toggleButton}
          aria-label={isExpanded ? 'Collapse' : 'Expand'}
        >
          {isExpanded ? '▼' : '▶'}
        </button>
      </div>

      {isExpanded && (
        <div className={styles.logSectionContent}>
          <div className={styles.logControls}>
            <select 
              value={levelFilter} 
              onChange={(e) => setLevelFilter(e.target.value)}
              className={styles.logLevelFilter}
            >
              <option value="all">All Levels</option>
              <option value="error">Errors Only</option>
              <option value="warning">Warnings Only</option>
              <option value="info">Info Only</option>
              <option value="debug">Debug Only</option>
            </select>
            <div className={styles.logResultsCount}>
              {filteredLogs.length} of {logs.length} entries
            </div>
          </div>

          <div className={styles.logList}>
            {filteredLogs.map((log, index) => (
              <LogEntryComponent key={index} entry={log} />
            ))}
          </div>

          {filteredLogs.length === 0 && (
            <div className={styles.noResults}>
              <p>No log entries match the selected filter.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const PerformanceMetrics: React.FC<PerformanceMetricsProps> = ({ metrics }) => {
  const formatMetricValue = (key: string, value: any): string => {
    if (typeof value === 'number') {
      if (key.includes('time') || key.includes('duration')) {
        return `${value.toFixed(2)}s`;
      }
      if (key.includes('memory') || key.includes('size')) {
        return `${value.toFixed(1)} MB`;
      }
      if (key.includes('percentage') || key.includes('usage')) {
        return `${value.toFixed(1)}%`;
      }
      return value.toFixed(2);
    }
    return String(value);
  };

  const getMetricColor = (key: string, value: any): string => {
    if (typeof value !== 'number') return '#6c757d';
    
    if (key.includes('error') && value > 0) return '#dc3545';
    if (key.includes('warning') && value > 0) return '#ffc107';
    if (key.includes('success') || key.includes('completed')) return '#28a745';
    if (key.includes('time') && value > 300) return '#ffc107'; // > 5 minutes
    if (key.includes('memory') && value > 512) return '#ffc107'; // > 512 MB
    
    return '#17a2b8';
  };

  return (
    <div className={styles.performanceMetrics}>
      <h4 className={styles.metricsTitle}>📊 Performance Metrics</h4>
      <div className={styles.metricsGrid}>
        {Object.entries(metrics).map(([key, value]) => (
          <div key={key} className={styles.metricCard}>
            <div className={styles.metricLabel}>
              {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
            </div>
            <div 
              className={styles.metricValue}
              style={{ color: getMetricColor(key, value) }}
            >
              {formatMetricValue(key, value)}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

const OptimizationSuggestions: React.FC<{ 
  opportunities: string[];
  technicalDebt: string[];
}> = ({ opportunities, technicalDebt }) => {
  if (opportunities.length === 0 && technicalDebt.length === 0) return null;

  return (
    <div className={styles.optimizationSection}>
      {opportunities.length > 0 && (
        <div className={styles.optimizationGroup}>
          <h4 className={styles.optimizationTitle}>🚀 Optimization Opportunities</h4>
          <ul className={styles.optimizationList}>
            {opportunities.map((opportunity, index) => (
              <li key={index} className={styles.optimizationItem}>
                <span className={styles.optimizationIcon}>💡</span>
                {opportunity}
              </li>
            ))}
          </ul>
        </div>
      )}

      {technicalDebt.length > 0 && (
        <div className={styles.optimizationGroup}>
          <h4 className={styles.optimizationTitle}>⚠️ Technical Debt Notes</h4>
          <ul className={styles.optimizationList}>
            {technicalDebt.map((debt, index) => (
              <li key={index} className={styles.optimizationItem}>
                <span className={styles.optimizationIcon}>🔧</span>
                {debt}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

const BenchmarkComparisons: React.FC<{ comparisons: Record<string, number> }> = ({ comparisons }) => {
  if (!comparisons || Object.keys(comparisons).length === 0) return null;

  return (
    <div className={styles.benchmarkSection}>
      <h4 className={styles.benchmarkTitle}>📈 Benchmark Comparisons</h4>
      <div className={styles.benchmarkGrid}>
        {Object.entries(comparisons).map(([benchmark, value]) => {
          const isGood = value > 0;
          return (
            <div key={benchmark} className={styles.benchmarkCard}>
              <div className={styles.benchmarkLabel}>
                {benchmark.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
              </div>
              <div 
                className={styles.benchmarkValue}
                style={{ color: isGood ? '#28a745' : '#dc3545' }}
              >
                {isGood ? '+' : ''}{value.toFixed(1)}%
              </div>
              <div className={styles.benchmarkDescription}>
                vs. baseline
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

const ExportButton: React.FC<{ data: any; filename: string }> = ({ data, filename }) => {
  const handleExport = () => {
    const jsonData = JSON.stringify(data, null, 2);
    const blob = new Blob([jsonData], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <button 
      onClick={handleExport}
      className={styles.exportButton}
      title={`Export ${filename}`}
    >
      📥 Export Technical Data
    </button>
  );
};

export const DeveloperLog: React.FC<DeveloperLogProps> = ({ 
  log, 
  isExpanded, 
  onToggle 
}) => {
  const totalLogEntries = useMemo(() => {
    return (
      (log.code_translation_details?.length || 0) +
      (log.api_mapping_issues?.length || 0) +
      (log.file_processing_log?.length || 0) +
      (log.error_details?.length || 0)
    );
  }, [log]);

  const hasErrors = useMemo(() => {
    return log.error_details?.length > 0 || 
           log.code_translation_details?.some(entry => entry.level.toLowerCase() === 'error') ||
           log.api_mapping_issues?.some(entry => entry.level.toLowerCase() === 'error') ||
           log.file_processing_log?.some(entry => entry.level.toLowerCase() === 'error');
  }, [log]);

  return (
    <div className={styles.section}>
      <div className={styles.sectionHeader} onClick={onToggle}>
        <h3 className={styles.sectionTitle}>
          🛠️ Developer Technical Log 
          {hasErrors && <span className={styles.errorIndicator}>⚠️</span>}
        </h3>
        <div className={styles.logSummary}>
          {totalLogEntries} entries
        </div>
        <button 
          className={styles.toggleButton}
          aria-label={isExpanded ? 'Collapse' : 'Expand'}
        >
          {isExpanded ? '▼' : '▶'}
        </button>
      </div>

      {isExpanded && (
        <div className={styles.sectionContent}>
          {/* Performance Metrics */}
          {log.performance_metrics && Object.keys(log.performance_metrics).length > 0 && (
            <PerformanceMetrics metrics={log.performance_metrics} />
          )}

          {/* Optimization Suggestions */}
          <OptimizationSuggestions 
            opportunities={log.optimization_opportunities || []}
            technicalDebt={log.technical_debt_notes || []}
          />

          {/* Benchmark Comparisons */}
          {log.benchmark_comparisons && (
            <BenchmarkComparisons comparisons={log.benchmark_comparisons} />
          )}

          {/* Log Sections */}
          <div className={styles.logSections}>
            <LogSection 
              title="Code Translation Details"
              logs={log.code_translation_details || []}
              icon="🔄"
            />
            
            <LogSection 
              title="API Mapping Issues"
              logs={log.api_mapping_issues || []}
              icon="🔗"
            />
            
            <LogSection 
              title="File Processing Log"
              logs={log.file_processing_log || []}
              icon="📁"
            />

            {/* Error Summary */}
            {log.error_details && log.error_details.length > 0 && (
              <div className={styles.errorSummarySection}>
                <h4 className={styles.errorSummaryTitle}>❌ Error Summary</h4>
                <div className={styles.errorList}>
                  {log.error_details.map((error, index) => (
                    <div key={index} className={styles.errorItem}>
                      <div className={styles.errorMessage}>
                        <strong>Error:</strong> {error.error_message || error.message || 'Unknown error'}
                      </div>
                      {error.module && (
                        <div className={styles.errorModule}>
                          <strong>Module:</strong> {error.module}
                        </div>
                      )}
                      {error.stack_trace && (
                        <details className={styles.errorStackTrace}>
                          <summary>Stack Trace</summary>
                          <pre className={styles.stackTraceContent}>
                            {error.stack_trace}
                          </pre>
                        </details>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Export Button */}
          <div className={styles.exportSection}>
            <ExportButton data={log} filename="developer-log.json" />
          </div>
        </div>
      )}
    </div>
  );
};