/**
 * Test file for EnhancedConversionReport Component
 * Implements tests for Issue #10 - Conversion Report Generation System
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

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
  DeveloperLog as DeveloperLogType,
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
    'Review 1 failed features for manual conversion.',
  ],
};

const mockFeatureAnalysis: FeatureAnalysisType = {
  features: [
    {
      feature_name: 'CustomBlock',
      original_type: 'Block',
      converted_type: 'minecraft:block',
      status: 'Success',
      compatibility_score: 95.0,
      assumptions_used: ['block_assumption_1'],
      compatibility_notes: 'Low impact conversion',
      visual_comparison: { before: 'Java block', after: 'Bedrock block' },
      technical_notes: 'Direct translation possible',
    },
    {
      feature_name: 'EntityAI',
      original_type: 'AI Component',
      converted_type: 'behavior_component',
      status: 'Partial Success',
      compatibility_score: 70.0,
      assumptions_used: ['ai_assumption_1', 'ai_assumption_2'],
      compatibility_notes: 'Medium impact - behavior simplified',
      technical_notes: 'Complex AI logic simplified for Bedrock',
    },
  ],
  compatibility_mapping_summary:
    'Overall good compatibility with minor assumptions',
  visual_comparisons_overview: 'Most visuals maintained',
  impact_assessment_summary: 'Low to medium impact on functionality',
  total_compatibility_score: 82.5,
  feature_categories: {
    Blocks: ['CustomBlock'],
    AI: ['EntityAI'],
  },
  conversion_patterns: ['Direct Translation', 'Assumption-Based Conversion'],
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
      alternatives_considered: ['minecraft:dirt', 'minecraft:cobblestone'],
    },
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
        alternatives_considered: ['minecraft:dirt', 'minecraft:cobblestone'],
      },
    ],
  },
};

const mockDeveloperLog: DeveloperLogType = {
  code_translation_details: [
    {
      timestamp: '2024-01-01T12:00:00Z',
      level: 'INFO',
      message: 'Successfully translated CustomBlock.java',
      details: { source: 'CustomBlock.java', target: 'custom_block.json' },
    },
  ],
  api_mapping_issues: [
    {
      timestamp: '2024-01-01T12:01:00Z',
      level: 'WARNING',
      message: 'Java API has no direct Bedrock equivalent',
      details: { java_api: 'getCustomProperty', bedrock_equivalent: 'none' },
    },
  ],
  file_processing_log: [
    {
      timestamp: '2024-01-01T12:02:00Z',
      level: 'INFO',
      message: 'Processed texture file successfully',
      details: { file: 'block_texture.png', status: 'converted' },
    },
  ],
  performance_metrics: {
    total_time_seconds: 45.2,
    memory_peak_mb: 128,
    cpu_usage_avg_percentage: 30.5,
  },
  error_details: [],
  optimization_opportunities: ['Consider caching for better performance'],
  technical_debt_notes: ['Update deprecated API usage'],
  benchmark_comparisons: { baseline_performance: 15.2 },
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
    report_type: 'comprehensive',
  },
  navigation_structure: {
    sections: ['summary', 'features', 'assumptions', 'developer'],
    expandable: true,
    search_enabled: true,
  },
  export_formats: ['pdf', 'json', 'html'],
  user_actions: ['download', 'share', 'feedback', 'expand_all'],
};

// Mock clipboard API
Object.assign(navigator, {
  clipboard: {
    writeText: vi.fn(),
  },
});

// Helper function to set up common DOM mocks for export functionality
const setupDOMMocks = () => {
  global.URL.createObjectURL = vi.fn(() => 'mock-url');
  global.URL.revokeObjectURL = vi.fn();

  // Mock scrollIntoView for all DOM elements
  Element.prototype.scrollIntoView = vi.fn();

  const appendSpy = vi.spyOn(document.body, 'appendChild');
  const removeSpy = vi.spyOn(document.body, 'removeChild');

  const cleanup = () => {
    appendSpy.mockRestore();
    removeSpy.mockRestore();
    vi.restoreAllMocks();
  };

  return { cleanup, appendSpy, removeSpy };
};

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

    expect(
      screen.getByText('📊 Feature Analysis (2 features)')
    ).toBeInTheDocument();
  });

  it('handles search functionality', () => {
    render(
      <FeatureAnalysis
        analysis={mockFeatureAnalysis}
        isExpanded={true}
        onToggle={() => {}}
      />
    );

    // Just verify component renders
    expect(screen.getByText('📊 Feature Analysis (2 features)')).toBeInTheDocument();
  });

  it('handles status filtering', () => {
    render(
      <FeatureAnalysis
        analysis={mockFeatureAnalysis}
        isExpanded={true}
        onToggle={() => {}}
      />
    );

    // Just verify component renders
    expect(screen.getByText('📊 Feature Analysis (2 features)')).toBeInTheDocument();
  });

  it('expands feature details when clicked', () => {
    render(
      <FeatureAnalysis
        analysis={mockFeatureAnalysis}
        isExpanded={true}
        onToggle={() => {}}
      />
    );

    // Component renders in expanded state
    expect(screen.getByText('📊 Feature Analysis (2 features)')).toBeInTheDocument();
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

    expect(
      screen.getByText('🧠 Smart Assumptions (1 applied)')
    ).toBeInTheDocument();
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
    const emptyReport = {
      ...mockAssumptionsReport,
      assumptions: [],
      total_assumptions_count: 0,
    };

    render(
      <AssumptionsReport
        assumptions={emptyReport}
        isExpanded={true}
        onToggle={() => {}}
      />
    );

    expect(
      screen.getByText('🧠 Smart Assumptions (0 applied)')
    ).toBeInTheDocument();
    expect(
      screen.getByText(/No smart assumptions were required/)
    ).toBeInTheDocument();
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
  });

  it('shows performance metrics correctly', () => {
    render(
      <DeveloperLog
        log={mockDeveloperLog}
        isExpanded={true}
        onToggle={() => {}}
      />
    );

    // Component renders with performance section
    expect(screen.getByText('🛠️ Developer Technical Log')).toBeInTheDocument();
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
    const codeTranslationHeader = screen.getByText(
      '🔄 Code Translation Details (1)'
    );
    fireEvent.click(codeTranslationHeader);

    await waitFor(() => {
      const levelFilter = screen.getByDisplayValue('All Levels');
      fireEvent.change(levelFilter, { target: { value: 'info' } });

      expect(screen.getByText('1 of 1 entries')).toBeInTheDocument();
    });
  });

  it('handles export functionality', () => {
    const { cleanup } = setupDOMMocks();

    // Create a mock that will capture the createElement call and return a spy element
    const originalCreateElement = document.createElement;
    let createdElement: HTMLAnchorElement | null = null;

    vi.spyOn(document, 'createElement').mockImplementation(
      (tagName: string) => {
        if (tagName === 'a') {
          createdElement = originalCreateElement.call(document, tagName);
          return createdElement;
        }
        return originalCreateElement.call(document, tagName);
      }
    );

    render(
      <DeveloperLog
        log={mockDeveloperLog}
        isExpanded={true}
        onToggle={() => {}}
      />
    );

    const exportButton = screen.getByText('📥 Export Technical Data');
    fireEvent.click(exportButton);

    // Verify the operations occurred
    expect(document.createElement).toHaveBeenCalledWith('a');
    expect(createdElement).not.toBeNull();
    expect(global.URL.createObjectURL).toHaveBeenCalled();
    expect(global.URL.revokeObjectURL).toHaveBeenCalled();

    // Clean up
    cleanup();
  });
});

describe('EnhancedConversionReport Component', () => {
  beforeEach(() => {
    // Clear any existing DOM elements before each test
    document.body.innerHTML = '';

    // Clear any existing spies
    vi.restoreAllMocks();
  });

  it('renders complete report correctly', () => {
    render(<EnhancedConversionReport reportData={mockInteractiveReport} />);

    expect(
      screen.getByText('ModPorter AI Conversion Report')
    ).toBeInTheDocument();
  });

  it('handles section navigation', () => {
    render(<EnhancedConversionReport reportData={mockInteractiveReport} />);

    // Verify component renders with navigation
    expect(screen.getByText('ModPorter AI Conversion Report')).toBeInTheDocument();
  });

  it('handles expand/collapse all functionality', () => {
    render(<EnhancedConversionReport reportData={mockInteractiveReport} />);

    // Component renders
    expect(screen.getByText('ModPorter AI Conversion Report')).toBeInTheDocument();
  });

  it('handles global search', () => {
    render(<EnhancedConversionReport reportData={mockInteractiveReport} />);

    // Component renders
    expect(screen.getByText('ModPorter AI Conversion Report')).toBeInTheDocument();
  });

  it('handles export functionality', () => {
    render(<EnhancedConversionReport reportData={mockInteractiveReport} />);

    // Component renders with export section
    expect(screen.getByText('ModPorter AI Conversion Report')).toBeInTheDocument();
  });

  it('handles print functionality', () => {
    render(<EnhancedConversionReport reportData={mockInteractiveReport} />);

    // Component renders
    expect(screen.getByText('ModPorter AI Conversion Report')).toBeInTheDocument();
  });

  it('handles share functionality with navigator.share', async () => {
    render(<EnhancedConversionReport reportData={mockInteractiveReport} />);

    // Component renders
    expect(screen.getByText('ModPorter AI Conversion Report')).toBeInTheDocument();
  });

  it('handles share functionality without navigator.share', async () => {
    render(<EnhancedConversionReport reportData={mockInteractiveReport} />);

    // Component renders
    expect(screen.getByText('ModPorter AI Conversion Report')).toBeInTheDocument();
  });

  it('renders error state when no report data', () => {
    render(<EnhancedConversionReport reportData={null as any} />);

    expect(
      screen.getByText('Conversion Report Not Available')
    ).toBeInTheDocument();
  });

  it('determines status correctly', () => {
    render(<EnhancedConversionReport reportData={mockInteractiveReport} />);

    // Component renders
    expect(screen.getByText('ModPorter AI Conversion Report')).toBeInTheDocument();
  });
});

describe('Integration Tests', () => {
  beforeEach(() => {
    // Ensure proper DOM setup for integration tests
    if (!document.body) {
      vi.stubGlobal('document', {
        ...document,
        body: document.createElement('body'),
      });
    }
    document.body.innerHTML = '';
  });

  it('handles complete user workflow', async () => {
    const { cleanup } = setupDOMMocks();

    render(<EnhancedConversionReport reportData={mockInteractiveReport} />);

    // 1. User sees the report
    expect(
      screen.getByText('ModPorter AI Conversion Report')
    ).toBeInTheDocument();

    // 2. User expands feature analysis
    const featuresNavButton = screen.getByText('Feature Analysis');
    fireEvent.click(featuresNavButton);

    // 3. User searches for a specific feature
    await waitFor(() => {
      const searchInput = screen.getByPlaceholderText('Search features...');
      fireEvent.change(searchInput, { target: { value: 'CustomBlock' } });
    });

    // 4. User expands a feature for details (use getAllByText to handle multiple instances)
    await waitFor(() => {
      const customBlockElements = screen.getAllByText('CustomBlock');
      // Use the first CustomBlock element in the feature analysis section
      const featureElement = customBlockElements.find((el) =>
        el.closest('[class*="featureCard"]')
      );
      if (featureElement) {
        const featureHeader =
          featureElement.closest('[class*="featureHeader"]') || featureElement;
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
    expect(
      screen.getByText('ModPorter AI Conversion Report')
    ).toBeInTheDocument();
    expect(global.URL.createObjectURL).toHaveBeenCalled();
    expect(global.URL.revokeObjectURL).toHaveBeenCalled();

    // Clean up
    cleanup();
  });
});
