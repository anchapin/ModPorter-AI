/**
 * Tests for Enhanced Conversion Report Components
 * Tests implementation of Issue #10 - Conversion Report Generation System
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { EnhancedConversionReport } from './EnhancedConversionReport';
import { ReportSummary } from './ReportSummary';
import { FeatureAnalysis } from './FeatureAnalysis';
import { AssumptionsReport } from './AssumptionsReport';
import { DeveloperLog } from './DeveloperLog';
import type { 
  InteractiveReport, 
  SummaryReport, 
  FeatureAnalysis as FeatureAnalysisType,
  AssumptionsReport as AssumptionsReportType,
  DeveloperLog as DeveloperLogType 
} from '../../types/api';

// Mock data
const mockSummaryReport: SummaryReport = {
  overall_success_rate: 85.5,
  total_features: 20,
  converted_features: 17,
  partially_converted_features: 2,
  failed_features: 1,
  assumptions_applied_count: 5,
  processing_time_seconds: 45.2,
  download_url: '/api/download/test_job_123',
  quick_statistics: { files_processed: 150 },
  total_files_processed: 150,
  output_size_mb: 12.5,
  conversion_quality_score: 82.0,
  recommended_actions: [
    'Good conversion results. Review partial conversions for optimization.',
    'Review 1 failed features for manual conversion.'
  ]
};

const mockFeatureAnalysis: FeatureAnalysisType = {
  features: [
    {
      name: 'CustomBlock',
      original_type: 'Block',
      converted_type: 'minecraft:block',
      status: 'Success',
      compatibility_score: 95.0,
      assumptions_used: ['block_assumption_1'],
      impact_assessment: 'Low impact conversion',
      visual_comparison: { before: 'Java block', after: 'Bedrock block' },
      technical_notes: 'Direct translation possible'
    },
    {
      name: 'EntityAI',
      original_type: 'AI Component',
      converted_type: 'behavior_component',
      status: 'Partial Success',
      compatibility_score: 70.0,
      assumptions_used: ['ai_assumption_1', 'ai_assumption_2'],
      impact_assessment: 'Medium impact - behavior simplified',
      technical_notes: 'Complex AI logic simplified for Bedrock'
    }
  ],
  compatibility_mapping_summary: 'Overall good compatibility with minor assumptions',
  visual_comparisons_overview: 'Most visuals maintained',
  impact_assessment_summary: 'Low to medium impact on functionality',
  total_compatibility_score: 82.5,
  feature_categories: {
    'Blocks': ['CustomBlock'],
    'AI': ['EntityAI']
  },
  conversion_patterns: ['Direct Translation', 'Assumption-Based Conversion']
};

const mockAssumptionsReport: AssumptionsReportType = {
  assumptions: [
    {
      assumption_id: 'SA_001',
      feature_affected: 'CustomBlock Materials',
      description: 'Custom material mapped to closest Bedrock equivalent',
      reasoning: 'No direct material mapping available',
      impact_level: 'Low',
      user_explanation: 'Material appearance may differ slightly',
      technical_notes: 'Used minecraft:stone as base material',
      original_feature: 'CustomBlock Materials',
      assumption_type: 'Material Mapping',
      bedrock_equivalent: 'minecraft:stone',
      confidence_score: 0.9,
      alternatives_considered: ['minecraft:dirt', 'minecraft:cobblestone']
    }
  ],
  total_assumptions_count: 1,
  impact_distribution: { low: 1, medium: 0, high: 0 },
  category_breakdown: {
    'Material Mapping': [
      {
        assumption_id: 'SA_001',
        feature_affected: 'CustomBlock Materials',
        description: 'Custom material mapped to closest Bedrock equivalent',
        reasoning: 'No direct material mapping available',
        impact_level: 'Low',
        user_explanation: 'Material appearance may differ slightly',
        technical_notes: 'Used minecraft:stone as base material',
        original_feature: 'CustomBlock Materials',
        assumption_type: 'Material Mapping',
        bedrock_equivalent: 'minecraft:stone',
        confidence_score: 0.9,
        alternatives_considered: ['minecraft:dirt', 'minecraft:cobblestone']
      }
    ]
  }
};

const mockDeveloperLog: DeveloperLogType = {
  code_translation_details: [
    {
      timestamp: '2024-01-01T12:00:00Z',
      level: 'INFO',
      message: 'Successfully translated CustomBlock.java',
      details: { source: 'CustomBlock.java', target: 'custom_block.json' }
    }
  ],
  api_mapping_issues: [
    {
      timestamp: '2024-01-01T12:01:00Z',
      level: 'WARNING',
      message: 'Java API has no direct Bedrock equivalent',
      details: { java_api: 'getCustomProperty', bedrock_equivalent: 'none' }
    }
  ],
  file_processing_log: [
    {
      timestamp: '2024-01-01T12:02:00Z',
      level: 'INFO',
      message: 'Processed texture file successfully',
      details: { file: 'block_texture.png', status: 'converted' }
    }
  ],
  performance_metrics: {
    total_time_seconds: 45.2,
    memory_peak_mb: 128,
    cpu_usage_avg_percentage: 30.5
  },
  error_details: [],
  optimization_opportunities: ['Consider caching for better performance'],
  technical_debt_notes: ['Update deprecated API usage'],
  benchmark_comparisons: { baseline_performance: 15.2 }
};

const mockInteractiveReport: InteractiveReport = {
  job_id: 'test_job_123',
  report_generation_date: '2024-01-01T12:00:00Z',
  summary: mockSummaryReport,
  feature_analysis: mockFeatureAnalysis,
  assumptions_report: mockAssumptionsReport,
  developer_log: mockDeveloperLog,
  metadata: {
    report_id: 'report_test_123',
    job_id: 'test_job_123',
    generation_timestamp: '2024-01-01T12:00:00Z',
    version: '2.0.0',
    report_type: 'comprehensive'
  },
  navigation_structure: {
    sections: ['summary', 'features', 'assumptions', 'developer'],
    expandable: true,
    search_enabled: true
  },
  export_formats: ['pdf', 'json', 'html'],
  user_actions: ['download', 'share', 'feedback', 'expand_all']
};

// Mock clipboard API
Object.assign(navigator, {
  clipboard: {
    writeText: jest.fn()
  }
});

describe('ReportSummary Component', () => {
  it('renders summary information correctly', () => {
    render(<ReportSummary summary={mockSummaryReport} />);
    
    expect(screen.getByText('85.5%')).toBeInTheDocument();
    expect(screen.getByText('Overall Success Rate')).toBeInTheDocument();
    expect(screen.getByText('20')).toBeInTheDocument(); // Total Features
    expect(screen.getByText('17')).toBeInTheDocument(); // Converted
    expect(screen.getByText('📥 Download .mcaddon')).toBeInTheDocument();
  });

  it('displays quality indicator correctly', () => {
    render(<ReportSummary summary={mockSummaryReport} />);
    
    expect(screen.getByText('Good (82.0)')).toBeInTheDocument();
  });

  it('shows recommended actions when present', () => {
    render(<ReportSummary summary={mockSummaryReport} />);
    
    expect(screen.getByText('💡 Recommended Actions')).toBeInTheDocument();
    expect(screen.getByText(/Good conversion results/)).toBeInTheDocument();
    expect(screen.getByText(/Review 1 failed features/)).toBeInTheDocument();
  });
});

describe('FeatureAnalysis Component', () => {
  it('renders feature analysis when expanded', () => {
    render(
      <FeatureAnalysis 
        analysis={mockFeatureAnalysis} 
        isExpanded={true} 
        onToggle={() => {}} 
      />
    );
    
    expect(screen.getByText('📊 Feature Analysis (2 features)')).toBeInTheDocument();
    expect(screen.getByText('CustomBlock')).toBeInTheDocument();
    expect(screen.getByText('EntityAI')).toBeInTheDocument();
    expect(screen.getByText('Direct Translation')).toBeInTheDocument();
  });

  it('handles search functionality', async () => {
    render(
      <FeatureAnalysis 
        analysis={mockFeatureAnalysis} 
        isExpanded={true} 
        onToggle={() => {}} 
      />
    );
    
    const searchInput = screen.getByPlaceholderText('Search features...');
    fireEvent.change(searchInput, { target: { value: 'CustomBlock' } });
    
    await waitFor(() => {
      expect(screen.getByText('1 of 2 features')).toBeInTheDocument();
    });
  });

  it('handles status filtering', async () => {
    render(
      <FeatureAnalysis 
        analysis={mockFeatureAnalysis} 
        isExpanded={true} 
        onToggle={() => {}} 
      />
    );
    
    const filterSelect = screen.getByDisplayValue('All Features');
    fireEvent.change(filterSelect, { target: { value: 'success' } });
    
    await waitFor(() => {
      expect(screen.getByText('1 of 2 features')).toBeInTheDocument();
    });
  });

  it('expands feature details when clicked', () => {
    render(
      <FeatureAnalysis 
        analysis={mockFeatureAnalysis} 
        isExpanded={true} 
        onToggle={() => {}} 
      />
    );
    
    const featureHeader = screen.getByText('CustomBlock').closest('.featureHeader');
    expect(featureHeader).toBeInTheDocument();
    
    if (featureHeader) {
      fireEvent.click(featureHeader);
      expect(screen.getByText('Direct translation possible')).toBeInTheDocument();
    }
  });
});

describe('AssumptionsReport Component', () => {
  it('renders assumptions when expanded', () => {
    render(
      <AssumptionsReport 
        assumptions={mockAssumptionsReport} 
        isExpanded={true} 
        onToggle={() => {}} 
      />
    );
    
    expect(screen.getByText('🧠 Smart Assumptions (1 applied)')).toBeInTheDocument();
    expect(screen.getByText('CustomBlock Materials')).toBeInTheDocument();
    expect(screen.getByText('90% confident')).toBeInTheDocument();
  });

  it('shows impact distribution', () => {
    render(
      <AssumptionsReport 
        assumptions={mockAssumptionsReport} 
        isExpanded={true} 
        onToggle={() => {}} 
      />
    );
    
    expect(screen.getByText('Impact Distribution')).toBeInTheDocument();
    expect(screen.getByText('Low Impact')).toBeInTheDocument();
    expect(screen.getByText('1 (100%)')).toBeInTheDocument();
  });

  it('handles impact level filtering', async () => {
    render(
      <AssumptionsReport 
        assumptions={mockAssumptionsReport} 
        isExpanded={true} 
        onToggle={() => {}} 
      />
    );
    
    const impactFilter = screen.getByDisplayValue('All Impacts');
    fireEvent.change(impactFilter, { target: { value: 'low' } });
    
    await waitFor(() => {
      expect(screen.getByText('1 of 1 assumptions')).toBeInTheDocument();
    });
  });

  it('renders empty state when no assumptions', () => {
    const emptyReport = { ...mockAssumptionsReport, assumptions: [], total_assumptions_count: 0 };
    
    render(
      <AssumptionsReport 
        assumptions={emptyReport} 
        isExpanded={true} 
        onToggle={() => {}} 
      />
    );
    
    expect(screen.getByText('🧠 Smart Assumptions (0 applied)')).toBeInTheDocument();
    expect(screen.getByText(/No smart assumptions were required/)).toBeInTheDocument();
  });
});

describe('DeveloperLog Component', () => {
  it('renders developer log when expanded', () => {
    render(
      <DeveloperLog 
        log={mockDeveloperLog} 
        isExpanded={true} 
        onToggle={() => {}} 
      />
    );
    
    expect(screen.getByText('🛠️ Developer Technical Log')).toBeInTheDocument();
    expect(screen.getByText('📊 Performance Metrics')).toBeInTheDocument();
    expect(screen.getByText('🚀 Optimization Opportunities')).toBeInTheDocument();
  });

  it('shows performance metrics correctly', () => {
    render(
      <DeveloperLog 
        log={mockDeveloperLog} 
        isExpanded={true} 
        onToggle={() => {}} 
      />
    );
    
    expect(screen.getByText('45.20s')).toBeInTheDocument(); // Total time
    expect(screen.getByText('128 MB')).toBeInTheDocument(); // Memory peak
    expect(screen.getByText('30.5%')).toBeInTheDocument(); // CPU usage
  });

  it('handles log level filtering', async () => {
    render(
      <DeveloperLog 
        log={mockDeveloperLog} 
        isExpanded={true} 
        onToggle={() => {}} 
      />
    );
    
    // Click to expand code translation section
    const codeTranslationHeader = screen.getByText('🔄 Code Translation Details (1)');
    fireEvent.click(codeTranslationHeader);
    
    await waitFor(() => {
      const levelFilter = screen.getByDisplayValue('All Levels');
      fireEvent.change(levelFilter, { target: { value: 'info' } });
      
      expect(screen.getByText('1 of 1 entries')).toBeInTheDocument();
    });
  });

  it('handles export functionality', () => {
    // Mock URL.createObjectURL and other needed methods
    global.URL.createObjectURL = jest.fn(() => 'mock-url');
    global.URL.revokeObjectURL = jest.fn();
    
    const mockLink = {
      click: jest.fn(),
      download: '',
      href: ''
    };
    
    jest.spyOn(document, 'createElement').mockImplementation((tagName) => {
      if (tagName === 'a') {
        return mockLink as any;
      }
      return document.createElement(tagName);
    });
    
    jest.spyOn(document.body, 'appendChild').mockImplementation(() => {} as any);
    jest.spyOn(document.body, 'removeChild').mockImplementation(() => {} as any);
    
    render(
      <DeveloperLog 
        log={mockDeveloperLog} 
        isExpanded={true} 
        onToggle={() => {}} 
      />
    );
    
    const exportButton = screen.getByText('📥 Export Technical Data');
    fireEvent.click(exportButton);
    
    expect(mockLink.click).toHaveBeenCalled();
    expect(global.URL.createObjectURL).toHaveBeenCalled();
  });
});

describe('EnhancedConversionReport Component', () => {
  it('renders complete report correctly', () => {
    render(<EnhancedConversionReport reportData={mockInteractiveReport} />);
    
    expect(screen.getByText('ModPorter AI Conversion Report')).toBeInTheDocument();
    expect(screen.getByText('Conversion Completed Successfully')).toBeInTheDocument();
    expect(screen.getByText('Quick Navigation')).toBeInTheDocument();
    expect(screen.getByText('Export & Share')).toBeInTheDocument();
  });

  it('handles section navigation', () => {
    render(<EnhancedConversionReport reportData={mockInteractiveReport} />);
    
    const featuresNavButton = screen.getByText('Feature Analysis');
    fireEvent.click(featuresNavButton);
    
    // Should expand the features section (test the navigation works)
    expect(featuresNavButton.closest('.navItem')).toHaveClass('navItemActive');
  });

  it('handles expand/collapse all functionality', () => {
    render(<EnhancedConversionReport reportData={mockInteractiveReport} />);
    
    const expandAllButton = screen.getByText('📖 Expand All');
    const collapseAllButton = screen.getByText('📕 Collapse All');
    
    fireEvent.click(expandAllButton);
    // All sections should be expanded
    
    fireEvent.click(collapseAllButton);
    // All sections should be collapsed except summary
  });

  it('handles global search', () => {
    render(<EnhancedConversionReport reportData={mockInteractiveReport} />);
    
    const searchInput = screen.getByPlaceholderText('Search across all report sections...');
    fireEvent.change(searchInput, { target: { value: 'CustomBlock' } });
    
    // Search functionality should filter content
    expect(searchInput).toHaveValue('CustomBlock');
  });

  it('handles export functionality', () => {
    global.URL.createObjectURL = jest.fn(() => 'mock-url');
    global.URL.revokeObjectURL = jest.fn();
    
    const mockLink = {
      click: jest.fn(),
      download: '',
      href: ''
    };
    
    jest.spyOn(document, 'createElement').mockImplementation((tagName) => {
      if (tagName === 'a') {
        return mockLink as any;
      }
      return document.createElement(tagName);
    });
    
    jest.spyOn(document.body, 'appendChild').mockImplementation(() => {} as any);
    jest.spyOn(document.body, 'removeChild').mockImplementation(() => {} as any);
    
    render(<EnhancedConversionReport reportData={mockInteractiveReport} />);
    
    const exportJsonButton = screen.getByText('📥 Export JSON');
    fireEvent.click(exportJsonButton);
    
    expect(mockLink.click).toHaveBeenCalled();
    expect(global.URL.createObjectURL).toHaveBeenCalled();
  });

  it('handles print functionality', () => {
    // Mock window.print
    Object.defineProperty(window, 'print', {
      value: jest.fn(),
      writable: true
    });
    
    render(<EnhancedConversionReport reportData={mockInteractiveReport} />);
    
    const printButton = screen.getByText('🖨️ Print Report');
    fireEvent.click(printButton);
    
    expect(window.print).toHaveBeenCalled();
  });

  it('handles share functionality with navigator.share', async () => {
    // Mock navigator.share
    Object.defineProperty(navigator, 'share', {
      value: jest.fn().mockResolvedValue(undefined),
      writable: true
    });
    
    render(<EnhancedConversionReport reportData={mockInteractiveReport} />);
    
    const shareButton = screen.getByText('🔗 Share Link');
    fireEvent.click(shareButton);
    
    await waitFor(() => {
      expect(navigator.share).toHaveBeenCalledWith({
        title: 'ModPorter AI Conversion Report',
        text: 'Check out this conversion report from ModPorter AI',
        url: expect.stringContaining('report_test_123')
      });
    });
  });

  it('handles share functionality without navigator.share', async () => {
    // Mock navigator.clipboard.writeText
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: jest.fn() },
      writable: true
    });
    
    // Mock alert
    jest.spyOn(window, 'alert').mockImplementation(() => {});
    
    render(<EnhancedConversionReport reportData={mockInteractiveReport} />);
    
    const shareButton = screen.getByText('🔗 Share Link');
    fireEvent.click(shareButton);
    
    await waitFor(() => {
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
        expect.stringContaining('report_test_123')
      );
      expect(window.alert).toHaveBeenCalledWith('Share link copied to clipboard!');
    });
  });

  it('renders error state when no report data', () => {
    render(<EnhancedConversionReport reportData={null as any} />);
    
    expect(screen.getByText('Conversion Report Not Available')).toBeInTheDocument();
    expect(screen.getByText(/There was an issue loading the conversion details/)).toBeInTheDocument();
  });

  it('determines status correctly', () => {
    const failedReport = {
      ...mockInteractiveReport,
      summary: { ...mockSummaryReport, overall_success_rate: 5.0 }
    };
    
    render(<EnhancedConversionReport reportData={failedReport} />);
    
    expect(screen.getByText('Conversion Completed with Issues')).toBeInTheDocument();
  });
});

describe('Integration Tests', () => {
  it('handles complete user workflow', async () => {
    render(<EnhancedConversionReport reportData={mockInteractiveReport} />);
    
    // 1. User sees the report
    expect(screen.getByText('ModPorter AI Conversion Report')).toBeInTheDocument();
    
    // 2. User expands feature analysis
    const featuresNavButton = screen.getByText('Feature Analysis');
    fireEvent.click(featuresNavButton);
    
    // 3. User searches for a specific feature
    await waitFor(() => {
      const searchInput = screen.getByPlaceholderText('Search features...');
      fireEvent.change(searchInput, { target: { value: 'CustomBlock' } });
    });
    
    // 4. User expands a feature for details
    await waitFor(() => {
      const customBlockElement = screen.getByText('CustomBlock');
      const featureHeader = customBlockElement.closest('.featureHeader');
      if (featureHeader) {
        fireEvent.click(featureHeader);
      }
    });
    
    // 5. User views assumptions
    const assumptionsNavButton = screen.getByText('Smart Assumptions');
    fireEvent.click(assumptionsNavButton);
    
    // 6. User exports the report
    const exportJsonButton = screen.getByText('📥 Export JSON');
    fireEvent.click(exportJsonButton);
    
    // Verify the workflow completed without errors
    expect(screen.getByText('ModPorter AI Conversion Report')).toBeInTheDocument();
  });
});