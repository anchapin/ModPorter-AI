/**
 * FeatureAnalysis Component - Enhanced feature analysis section
 * Part of Issue #10 - Conversion Report Generation System
 */

import React, { useState, useMemo } from 'react';
import type { FeatureAnalysis as FeatureAnalysisType, FeatureConversionDetail } from '../../types/api';
import styles from './ConversionReport.module.css';

interface FeatureAnalysisProps {
  analysis: FeatureAnalysisType;
  isExpanded: boolean;
  onToggle: () => void;
}

interface FeatureCardProps {
  feature: FeatureConversionDetail;
}

const CompatibilityScore: React.FC<{ score: number }> = ({ score }) => {
  const getScoreColor = (score: number) => {
    if (score >= 90) return '#28a745';
    if (score >= 70) return '#ffc107';
    if (score >= 50) return '#fd7e14';
    return '#dc3545';
  };

  return (
    <div className={styles.compatibilityScore}>
      <div className={styles.scoreBar}>
        <div 
          className={styles.scoreFill}
          style={{ 
            width: `${score}%`,
            backgroundColor: getScoreColor(score)
          }}
        />
      </div>
      <span className={styles.scoreText} style={{ color: getScoreColor(score) }}>
        {score.toFixed(0)}%
      </span>
    </div>
  );
};

const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const getStatusInfo = (status: string) => {
    const normalizedStatus = status.toLowerCase();
    
    if (normalizedStatus.includes('success') || normalizedStatus.includes('converted')) {
      return { color: '#28a745', icon: '✅', text: 'Success' };
    }
    if (normalizedStatus.includes('partial')) {
      return { color: '#ffc107', icon: '⚠️', text: 'Partial' };
    }
    if (normalizedStatus.includes('failed')) {
      return { color: '#dc3545', icon: '❌', text: 'Failed' };
    }
    return { color: '#6c757d', icon: '⚪', text: status };
  };

  const statusInfo = getStatusInfo(status);

  return (
    <span 
      className={styles.statusBadge}
      style={{ 
        backgroundColor: statusInfo.color + '20',
        color: statusInfo.color,
        border: `1px solid ${statusInfo.color}40`
      }}
    >
      {statusInfo.icon} {statusInfo.text}
    </span>
  );
};

const FeatureCard: React.FC<FeatureCardProps> = ({ feature }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className={styles.featureCard}>
      <div className={styles.featureHeader} onClick={() => setIsExpanded(!isExpanded)}>
        <div className={styles.featureTitle}>
          <h4 className={styles.featureName}>{feature.feature_name}</h4>
          <StatusBadge status={feature.status} />
        </div>
        <div className={styles.featureMetrics}>
          <CompatibilityScore score={feature.compatibility_score || 0} />
          <button 
            className={styles.expandButton}
            aria-label={isExpanded ? 'Collapse' : 'Expand'}
          >
            {isExpanded ? '▼' : '▶'}
          </button>
        </div>
      </div>

      {isExpanded && (
        <div className={styles.featureDetails}>
          <div className={styles.featureInfo}>
            <div className={styles.featureInfoItem}>
              <strong>Original Type:</strong> {feature.original_type || 'Unknown'}
            </div>
            {feature.converted_type && (
              <div className={styles.featureInfoItem}>
                <strong>Converted Type:</strong> {feature.converted_type}
              </div>
            )}
            <div className={styles.featureInfoItem}>
              <strong>Compatibility Notes:</strong> {feature.compatibility_notes}
            </div>
            {feature.impact_of_assumption && (
              <div className={styles.featureInfoItem}>
                <strong>Impact of Assumptions:</strong> {feature.impact_of_assumption}
              </div>
            )}
          </div>

          {feature.assumptions_used && feature.assumptions_used.length > 0 && (
            <div className={styles.assumptionsUsed}>
              <strong>Assumptions Applied:</strong>
              <ul className={styles.assumptionsList}>
                {feature.assumptions_used.map((assumption, index) => (
                  <li key={index} className={styles.assumptionItem}>
                    {assumption}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {feature.visual_comparison && (
            <div className={styles.visualComparison}>
              <strong>Visual Comparison:</strong>
              <div className={styles.comparisonContainer}>
                {feature.visual_comparison.before && (
                  <div className={styles.comparisonItem}>
                    <h5>Before</h5>
                    <p>{feature.visual_comparison.before}</p>
                  </div>
                )}
                {feature.visual_comparison.after && (
                  <div className={styles.comparisonItem}>
                    <h5>After</h5>
                    <p>{feature.visual_comparison.after}</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {feature.technical_notes && (
            <div className={styles.technicalNotes}>
              <strong>Technical Notes:</strong>
              <p className={styles.technicalText}>{feature.technical_notes}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const SearchBar: React.FC<{ onSearch: (query: string) => void }> = ({ onSearch }) => {
  const [query, setQuery] = useState('');

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newQuery = e.target.value;
    setQuery(newQuery);
    onSearch(newQuery);
  };

  return (
    <div className={styles.searchBar}>
      <input
        type="text"
        placeholder="Search features..."
        value={query}
        onChange={handleSearch}
        className={styles.searchInput}
      />
      <span className={styles.searchIcon}>🔍</span>
    </div>
  );
};

const FilterDropdown: React.FC<{ 
  options: Array<{ label: string; value: string }>;
  onFilter: (value: string) => void;
}> = ({ options, onFilter }) => {
  const [selectedFilter, setSelectedFilter] = useState('all');

  const handleFilter = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    setSelectedFilter(value);
    onFilter(value);
  };

  return (
    <select 
      value={selectedFilter} 
      onChange={handleFilter}
      className={styles.filterSelect}
    >
      {options.map(option => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  );
};

const CategoryBreakdown: React.FC<{ categories: Record<string, string[]> }> = ({ categories }) => {
  return (
    <div className={styles.categoryBreakdown}>
      <h4>Features by Category</h4>
      <div className={styles.categoriesGrid}>
        {Object.entries(categories).map(([category, features]) => (
          <div key={category} className={styles.categoryCard}>
            <h5 className={styles.categoryTitle}>{category}</h5>
            <div className={styles.categoryCount}>{features.length} features</div>
            <div className={styles.categoryFeatures}>
              {features.slice(0, 3).map((feature, index) => (
                <span key={index} className={styles.featureTag}>
                  {feature}
                </span>
              ))}
              {features.length > 3 && (
                <span className={styles.moreTag}>
                  +{features.length - 3} more
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export const FeatureAnalysis: React.FC<FeatureAnalysisProps> = ({ 
  analysis, 
  isExpanded, 
  onToggle 
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  const filterOptions = [
    { label: 'All Features', value: 'all' },
    { label: 'Successful', value: 'success' },
    { label: 'Partial', value: 'partial' },
    { label: 'Failed', value: 'failed' }
  ];

  const filteredFeatures = useMemo(() => {
    let filtered = analysis.features || [];

    // Apply search filter
    if (searchQuery) {
      filtered = filtered.filter(feature =>
        feature.feature_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        feature.compatibility_notes?.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    // Apply status filter
    if (statusFilter !== 'all') {
      filtered = filtered.filter(feature =>
        feature.status?.toLowerCase().includes(statusFilter)
      );
    }

    return filtered;
  }, [analysis.features, searchQuery, statusFilter]);

  const averageCompatibility = useMemo(() => {
    if (!analysis.features || analysis.features.length === 0) return 0;
    const total = analysis.features.reduce((sum, feature) => sum + (feature.compatibility_score || 0), 0);
    return total / analysis.features.length;
  }, [analysis.features]);

  return (
    <div className={styles.section}>
      <div className={styles.sectionHeader} onClick={onToggle}>
        <h3 className={styles.sectionTitle}>
          📊 Feature Analysis ({analysis.features?.length || 0} features)
        </h3>
        <button 
          className={styles.toggleButton}
          aria-label={isExpanded ? 'Collapse' : 'Expand'}
        >
          {isExpanded ? '▼' : '▶'}
        </button>
      </div>

      {isExpanded && (
        <div className={styles.sectionContent}>
          {/* Summary Information */}
          <div className={styles.analysisSummary}>
            <div className={styles.summaryCards}>
              <div className={styles.summaryCard}>
                <div className={styles.summaryValue}>{averageCompatibility.toFixed(1)}%</div>
                <div className={styles.summaryLabel}>Average Compatibility</div>
              </div>
              <div className={styles.summaryCard}>
                <div className={styles.summaryValue}>{analysis.total_compatibility_score || 0}%</div>
                <div className={styles.summaryLabel}>Overall Score</div>
              </div>
              <div className={styles.summaryCard}>
                <div className={styles.summaryValue}>{Object.keys(analysis.feature_categories || {}).length}</div>
                <div className={styles.summaryLabel}>Categories</div>
              </div>
            </div>
            
            <div className={styles.summaryText}>
              <p><strong>Compatibility Summary:</strong> {analysis.compatibility_mapping_summary}</p>
              {analysis.visual_comparisons_overview && (
                <p><strong>Visual Changes:</strong> {analysis.visual_comparisons_overview}</p>
              )}
              <p><strong>Impact Assessment:</strong> {analysis.impact_assessment_summary}</p>
            </div>
          </div>

          {/* Category Breakdown */}
          {analysis.feature_categories && Object.keys(analysis.feature_categories).length > 0 && (
            <CategoryBreakdown categories={analysis.feature_categories} />
          )}

          {/* Conversion Patterns */}
          {analysis.conversion_patterns && analysis.conversion_patterns.length > 0 && (
            <div className={styles.conversionPatterns}>
              <h4>Conversion Patterns Identified</h4>
              <div className={styles.patternsList}>
                {analysis.conversion_patterns.map((pattern, index) => (
                  <span key={index} className={styles.patternTag}>
                    {pattern}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Feature Controls */}
          <div className={styles.featureControls}>
            <SearchBar onSearch={setSearchQuery} />
            <FilterDropdown options={filterOptions} onFilter={setStatusFilter} />
            <div className={styles.resultsCount}>
              {filteredFeatures.length} of {analysis.features?.length || 0} features
            </div>
          </div>

          {/* Feature List */}
          <div className={styles.featureList}>
            {filteredFeatures.map((feature, index) => (
              <FeatureCard key={feature.feature_name || index} feature={feature} />
            ))}
          </div>

          {filteredFeatures.length === 0 && (
            <div className={styles.noResults}>
              <p>No features match the current filters.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};