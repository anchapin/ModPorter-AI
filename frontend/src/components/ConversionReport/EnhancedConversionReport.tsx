/**
 * Enhanced ConversionReport Component - Comprehensive report interface
 * Implements Issue #10 - Conversion Report Generation System
 */

import React, { useState, useMemo } from 'react';
import type { InteractiveReport } from '../../types/api';
import { ReportSummary } from './ReportSummary';
import { FeatureAnalysis } from './FeatureAnalysis';
import { AssumptionsReport } from './AssumptionsReport';
import { DeveloperLog } from './DeveloperLog';
import styles from './ConversionReport.module.css';

interface EnhancedConversionReportProps {
  reportData: InteractiveReport;
  jobStatus?: 'completed' | 'failed' | 'processing';
}

interface NavigationItem {
  id: string;
  title: string;
  icon: string;
  count?: number;
  hasErrors?: boolean;
}

const ExportControls: React.FC<{ reportData: InteractiveReport }> = ({ reportData }) => {
  const [isExporting, setIsExporting] = useState(false);

  const handleExportJSON = () => {
    setIsExporting(true);
    try {
      const jsonData = JSON.stringify(reportData, null, 2);
      const blob = new Blob([jsonData], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `conversion-report-${reportData.metadata?.job_id || 'unknown'}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } finally {
      setIsExporting(false);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  const handleShareableLink = () => {
    const baseUrl = window.location.origin;
    const shareUrl = `${baseUrl}/reports/${reportData.metadata?.report_id || reportData.job_id}`;
    
    if (navigator.share) {
      navigator.share({
        title: 'ModPorter AI Conversion Report',
        text: 'Check out this conversion report from ModPorter AI',
        url: shareUrl,
      }).catch(() => {
        // Fallback to copying to clipboard
        navigator.clipboard.writeText(shareUrl);
        alert('Share link copied to clipboard!');
      });
    } else {
      navigator.clipboard.writeText(shareUrl);
      alert('Share link copied to clipboard!');
    }
  };

  return (
    <div className={styles.exportControls}>
      <h4>Export & Share</h4>
      <div className={styles.exportButtons}>
        <button 
          onClick={handleExportJSON} 
          disabled={isExporting}
          className={styles.exportButton}
        >
          📥 Export JSON
        </button>
        <button 
          onClick={handlePrint}
          className={styles.exportButton}
        >
          🖨️ Print Report
        </button>
        <button 
          onClick={handleShareableLink}
          className={styles.exportButton}
        >
          🔗 Share Link
        </button>
      </div>
    </div>
  );
};

const QuickNavigation: React.FC<{
  sections: NavigationItem[];
  activeSection: string;
  onSectionClick: (sectionId: string) => void;
}> = ({ sections, activeSection, onSectionClick }) => {
  return (
    <div className={styles.quickNavigation}>
      <h4>Quick Navigation</h4>
      <div className={styles.navItems}>
        {sections.map((section) => (
          <button
            key={section.id}
            onClick={() => onSectionClick(section.id)}
            className={`${styles.navItem} ${activeSection === section.id ? styles.navItemActive : ''}`}
            title={section.title}
          >
            <span className={styles.navIcon}>{section.icon}</span>
            <span className={styles.navTitle}>{section.title}</span>
            {section.count !== undefined && (
              <span className={styles.navCount}>({section.count})</span>
            )}
            {section.hasErrors && (
              <span className={styles.navError}>⚠️</span>
            )}
          </button>
        ))}
      </div>
    </div>
  );
};

const ReportMetadata: React.FC<{ reportData: InteractiveReport }> = ({ reportData }) => {
  const metadata = reportData.metadata;

  return (
    <div className={styles.reportMetadata}>
      <div className={styles.metadataGrid}>
        <div className={styles.metadataItem}>
          <span className={styles.metadataLabel}>Report ID:</span>
          <span className={styles.metadataValue}>{metadata?.report_id || 'N/A'}</span>
        </div>
        <div className={styles.metadataItem}>
          <span className={styles.metadataLabel}>Job ID:</span>
          <span className={styles.metadataValue}>{metadata?.job_id || reportData.job_id}</span>
        </div>
        <div className={styles.metadataItem}>
          <span className={styles.metadataLabel}>Generated:</span>
          <span className={styles.metadataValue}>
            {metadata?.generation_timestamp 
              ? new Date(metadata.generation_timestamp).toLocaleString()
              : new Date().toLocaleString()
            }
          </span>
        </div>
        <div className={styles.metadataItem}>
          <span className={styles.metadataLabel}>Version:</span>
          <span className={styles.metadataValue}>{metadata?.version || '2.0.0'}</span>
        </div>
      </div>
    </div>
  );
};

const GlobalSearch: React.FC<{
  onSearch: (query: string) => void;
}> = ({ onSearch }) => {
  const [query, setQuery] = useState('');

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newQuery = e.target.value;
    setQuery(newQuery);
    onSearch(newQuery);
  };

  return (
    <div className={styles.globalSearch}>
      <input
        type="text"
        placeholder="Search across all report sections..."
        value={query}
        onChange={handleSearch}
        className={styles.globalSearchInput}
      />
      <span className={styles.searchIcon}>🔍</span>
    </div>
  );
};

export const EnhancedConversionReport: React.FC<EnhancedConversionReportProps> = ({
  reportData,
  jobStatus
}) => {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(['summary']) // Start with summary expanded
  );
  const [activeSection, setActiveSection] = useState('summary');

  // Determine overall status
  const overallStatus = useMemo(() => {
    if (jobStatus) return jobStatus;
    if (!reportData.summary) return 'failed';
    return reportData.summary.overall_success_rate > 10 ? 'completed' : 'failed';
  }, [jobStatus, reportData.summary]);

  // Create navigation items
  const navigationSections = useMemo<NavigationItem[]>(() => {
    const sections: NavigationItem[] = [
      {
        id: 'summary',
        title: 'Summary',
        icon: '📊',
      }
    ];

    if (reportData.feature_analysis?.features?.length > 0) {
      sections.push({
        id: 'features',
        title: 'Feature Analysis',
        icon: '🔧',
        count: reportData.feature_analysis.features.length
      });
    }

    if (reportData.assumptions_report?.assumptions?.length > 0) {
      sections.push({
        id: 'assumptions',
        title: 'Smart Assumptions',
        icon: '🧠',
        count: reportData.assumptions_report.assumptions.length
      });
    }

    if (reportData.developer_log) {
      const hasErrors = reportData.developer_log.error_details?.length > 0;
      sections.push({
        id: 'developer',
        title: 'Technical Log',
        icon: '🛠️',
        hasErrors
      });
    }

    return sections;
  }, [reportData]);

  // Toggle section expansion
  const toggleSection = (sectionId: string) => {
    setExpandedSections(prev => {
      const newSet = new Set(prev);
      if (newSet.has(sectionId)) {
        newSet.delete(sectionId);
      } else {
        newSet.add(sectionId);
      }
      return newSet;
    });
  };

  // Handle section click from navigation
  const handleSectionClick = (sectionId: string) => {
    setActiveSection(sectionId);
    setExpandedSections(prev => new Set([...prev, sectionId]));
    
    // Scroll to section
    const element = document.getElementById(`section-${sectionId}`);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  // Expand all sections
  const expandAll = () => {
    setExpandedSections(new Set(navigationSections.map(s => s.id)));
  };

  // Collapse all sections
  const collapseAll = () => {
    setExpandedSections(new Set(['summary'])); // Keep summary expanded
  };

  if (!reportData) {
    return (
      <div className={styles.errorContainer}>
        <h2>Conversion Report Not Available</h2>
        <p>There was an issue loading the conversion details. Please try again later.</p>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      {/* Enhanced Header */}
      <div className={styles.enhancedHeader}>
        <div className={styles.headerContent}>
          <h1 className={`${styles.title} ${styles[`title${overallStatus.charAt(0).toUpperCase() + overallStatus.slice(1)}`]}`}>
            ModPorter AI Conversion Report
          </h1>
          <div className={styles.headerSubtitle}>
            {overallStatus === 'completed' ? 'Conversion Completed Successfully' :
             overallStatus === 'failed' ? 'Conversion Completed with Issues' :
             'Conversion in Progress...'}
          </div>
        </div>
        
        <div className={styles.headerActions}>
          <button onClick={expandAll} className={styles.actionButton}>
            📖 Expand All
          </button>
          <button onClick={collapseAll} className={styles.actionButton}>
            📕 Collapse All
          </button>
        </div>
      </div>

      {/* Report Metadata */}
      <ReportMetadata reportData={reportData} />

      {/* Quick Navigation */}
      <QuickNavigation
        sections={navigationSections}
        activeSection={activeSection}
        onSectionClick={handleSectionClick}
      />

      {/* Global Search */}
      <GlobalSearch onSearch={() => {}} />

      {/* Export Controls */}
      <ExportControls reportData={reportData} />

      {/* Report Sections */}
      <div className={styles.reportSections}>
        {/* Summary Section */}
        <div id="section-summary" className={styles.section}>
          <ReportSummary summary={reportData.summary} />
        </div>

        {/* Feature Analysis Section */}
        {reportData.feature_analysis && (
          <div id="section-features">
            <FeatureAnalysis
              analysis={reportData.feature_analysis}
              isExpanded={expandedSections.has('features')}
              onToggle={() => toggleSection('features')}
            />
          </div>
        )}

        {/* Assumptions Report Section */}
        {reportData.assumptions_report && (
          <div id="section-assumptions">
            <AssumptionsReport
              assumptions={reportData.assumptions_report}
              isExpanded={expandedSections.has('assumptions')}
              onToggle={() => toggleSection('assumptions')}
            />
          </div>
        )}

        {/* Developer Log Section */}
        {reportData.developer_log && (
          <div id="section-developer">
            <DeveloperLog
              log={reportData.developer_log}
              isExpanded={expandedSections.has('developer')}
              onToggle={() => toggleSection('developer')}
            />
          </div>
        )}
      </div>

      {/* Report Footer */}
      <div className={styles.reportFooter}>
        <p>
          Report generated by ModPorter AI v{reportData.metadata?.version || '2.0.0'} | 
          <a href="https://modporter.ai" target="_blank" rel="noopener noreferrer">
            Learn more about ModPorter AI
          </a>
        </p>
      </div>
    </div>
  );
};