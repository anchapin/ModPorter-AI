import React, { useState } from 'react';
import { submitIssueReport } from '../../services/api';
import styles from './ConversionReport.module.css';

interface ReportIssueProps {
  jobId: string;
  modName: string;
  version: string;
  conversionScore: number;
  failingCategories: string[];
}

interface IssueReportPayload {
  job_id: string;
  mod_name: string;
  version: string;
  conversion_score: number;
  failing_categories: string[];
  description: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  contact_email?: string;
}

export const ReportIssue: React.FC<ReportIssueProps> = ({
  jobId,
  modName,
  version,
  conversionScore,
  failingCategories,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [description, setDescription] = useState('');
  const [severity, setSeverity] = useState<'low' | 'medium' | 'high' | 'critical'>('medium');
  const [contactEmail, setContactEmail] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitStatus, setSubmitStatus] = useState<'success' | 'error' | null>(null);
  const [submitMessage, setSubmitMessage] = useState('');

  const handleSubmit = async () => {
    if (!description.trim()) {
      setSubmitStatus('error');
      setSubmitMessage('Please provide a description of the issue.');
      return;
    }

    setIsSubmitting(true);
    setSubmitStatus(null);
    setSubmitMessage('');

    try {
      const payload: IssueReportPayload = {
        job_id: jobId,
        mod_name: modName,
        version,
        conversion_score: conversionScore,
        failing_categories: failingCategories,
        description: description.trim(),
        severity,
        contact_email: contactEmail.trim() || undefined,
      };

      await submitIssueReport(payload);
      setSubmitStatus('success');
      setSubmitMessage('Thank you! Your issue report has been submitted. We will investigate and get back to you.');
      setDescription('');
      setContactEmail('');
      setSeverity('medium');
    } catch (error) {
      setSubmitStatus('error');
      setSubmitMessage(
        error instanceof Error ? error.message : 'Failed to submit issue report'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className={styles.reportIssueSection}>
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className={styles.reportIssueToggle}
        aria-expanded={isExpanded}
      >
        <span className={styles.reportIssueIcon}>🐛</span>
        <span>Report an issue with this conversion</span>
        <span className={styles.toggleArrow}>{isExpanded ? '▲' : '▼'}</span>
      </button>

      {isExpanded && (
        <div className={styles.reportIssueForm}>
          <div className={styles.reportIssueMeta}>
            <div className={styles.metaItem}>
              <span className={styles.metaLabel}>Mod:</span>
              <span className={styles.metaValue}>{modName}</span>
            </div>
            <div className={styles.metaItem}>
              <span className={styles.metaLabel}>Version:</span>
              <span className={styles.metaValue}>{version}</span>
            </div>
            <div className={styles.metaItem}>
              <span className={styles.metaLabel}>Conversion Score:</span>
              <span className={styles.metaValue}>{conversionScore.toFixed(1)}%</span>
            </div>
          </div>

          {failingCategories.length > 0 && (
            <div className={styles.failingCategories}>
              <span className={styles.failingLabel}>Affected mods:</span>
              <div className={styles.failingTags}>
                {failingCategories.map((cat, idx) => (
                  <span key={idx} className={styles.failingTag}>{cat}</span>
                ))}
              </div>
            </div>
          )}

          <div className={styles.formGroup}>
            <label htmlFor="severity" className={styles.formLabel}>
              Severity
            </label>
            <select
              id="severity"
              value={severity}
              onChange={(e) => setSeverity(e.target.value as typeof severity)}
              className={styles.formSelect}
              disabled={isSubmitting}
            >
              <option value="low">Low - Minor issue, conversion mostly works</option>
              <option value="medium">Medium - Noticeable problem affecting gameplay</option>
              <option value="high">High - Major issue, large portion not working</option>
              <option value="critical">Critical - Conversion completely broken</option>
            </select>
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="description" className={styles.formLabel}>
              Description *
            </label>
            <textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Please describe what went wrong with the conversion. Include what you expected vs what actually happened."
              rows={4}
              className={styles.formTextarea}
              disabled={isSubmitting}
              required
            />
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="contactEmail" className={styles.formLabel}>
              Email (optional, for follow-up)
            </label>
            <input
              type="email"
              id="contactEmail"
              value={contactEmail}
              onChange={(e) => setContactEmail(e.target.value)}
              placeholder="your@email.com"
              className={styles.formInput}
              disabled={isSubmitting}
            />
          </div>

          {submitStatus === 'error' && submitMessage && (
            <p className={styles.reportIssueError}>Error: {submitMessage}</p>
          )}

          {submitStatus === 'success' && submitMessage && (
            <p className={styles.reportIssueSuccess}>{submitMessage}</p>
          )}

          <button
            onClick={handleSubmit}
            disabled={isSubmitting}
            className={styles.reportIssueSubmit}
          >
            {isSubmitting ? 'Submitting...' : 'Submit Issue Report'}
          </button>
        </div>
      )}
    </div>
  );
};

export default ReportIssue;