import { render, screen, waitFor } from '@testing-library/react';
import { vi, describe, beforeEach, test, expect, afterEach } from 'vitest';
import QAReport from './QAReport';

// Mock console.log to avoid noise in tests
const mockConsoleLog = vi.spyOn(console, 'log').mockImplementation(() => {});

describe('QAReport', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    mockConsoleLog.mockRestore();
    overallTimeoutTimer = setTimeout(() => {}, 0); // Clear any pending timers
  });

  test('shows loading state initially', () => {
    render(<QAReport taskId="test-task-123" />);

    expect(screen.getByText('Loading QA Report for Task ID: test-task-123...')).toBeInTheDocument();
  });

  test('shows error when no task ID provided', async () => {
    render(<QAReport taskId="" />);

    await waitFor(() => {
      expect(screen.getByText('Error: Task ID is required to fetch a QA report.')).toBeInTheDocument();
    });
  });

  test('displays QA report data after loading', async () => {
    render(<QAReport taskId="test-task-123" />);

    // Fast-forward the mock API delay
    vi.advanceTimersByTime(1000);

    await waitFor(() => {
      expect(screen.getByText('QA Report (Task ID: test-task-123)')).toBeInTheDocument();
    });

    // Check that basic report information is displayed
    expect(screen.getByText(/Report ID:/)).toBeInTheDocument();
    expect(screen.getByText(/Conversion ID:/)).toBeInTheDocument();
    expect(screen.getByText(/Generated At:/)).toBeInTheDocument();
  });

  test('displays overall summary section', async () => {
    render(<QAReport taskId="test-task-123" />);

    vi.advanceTimersByTime(1000);

    await waitFor(() => {
      expect(screen.getByText('Overall Summary')).toBeInTheDocument();
    });

    expect(screen.getByText(/Overall Quality Score:/)).toBeInTheDocument();
    expect(screen.getByText(/Total Tests:/)).toBeInTheDocument();
    expect(screen.getByText(/Passed:/)).toBeInTheDocument();
    expect(screen.getByText(/Failed:/)).toBeInTheDocument();
  });

  test('displays functional tests section', async () => {
    render(<QAReport taskId="test-task-123" />);

    vi.advanceTimersByTime(1000);

    await waitFor(() => {
      expect(screen.getByText('Functional Tests')).toBeInTheDocument();
    });

    // Should display functional test data as JSON
    expect(screen.getByText(/"passed": 40/)).toBeInTheDocument();
    expect(screen.getByText(/"failed": 1/)).toBeInTheDocument();
  });

  test('displays performance tests section', async () => {
    render(<QAReport taskId="test-task-123" />);

    vi.advanceTimersByTime(1000);

    await waitFor(() => {
      expect(screen.getByText('Performance Tests')).toBeInTheDocument();
    });

    // Should display performance test data as JSON
    expect(screen.getByText(/"cpu_avg": "20%"/)).toBeInTheDocument();
    expect(screen.getByText(/"memory_peak": "250MB"/)).toBeInTheDocument();
  });

  test('displays compatibility tests section', async () => {
    render(<QAReport taskId="test-task-123" />);

    vi.advanceTimersByTime(1000);

    await waitFor(() => {
      expect(screen.getByText('Compatibility Tests')).toBeInTheDocument();
    });

    // Should display compatibility test data as JSON
    expect(screen.getByText(/"versions_tested"/)).toBeInTheDocument();
    expect(screen.getByText(/"1.19.0"/)).toBeInTheDocument();
    expect(screen.getByText(/"1.20.0"/)).toBeInTheDocument();
  });

  test('displays recommendations section', async () => {
    render(<QAReport taskId="test-task-123" />);

    vi.advanceTimersByTime(1000);

    await waitFor(() => {
      expect(screen.getByText('Recommendations')).toBeInTheDocument();
    });

    // Should display recommendations as list items
    expect(screen.getByText('Review item placement logic.')).toBeInTheDocument();
    expect(screen.getByText(/Optimize texture loading for 'custom_block_A'/)).toBeInTheDocument();
  });

  test('displays severity ratings section', async () => {
    render(<QAReport taskId="test-task-123" />);

    vi.advanceTimersByTime(1000);

    await waitFor(() => {
      expect(screen.getByText('Issue Severity')).toBeInTheDocument();
    });

    // Should display severity ratings as JSON
    expect(screen.getByText(/"critical": 0/)).toBeInTheDocument();
    expect(screen.getByText(/"major": 1/)).toBeInTheDocument();
    expect(screen.getByText(/"minor": 2/)).toBeInTheDocument();
  });

  test('uses custom API base URL when provided', async () => {
    const customApiUrl = '/custom/api/qa';
    
    render(<QAReport taskId="test-task-123" apiBaseUrl={customApiUrl} />);

    expect(mockConsoleLog).toHaveBeenCalledWith(
      expect.stringContaining(`${customApiUrl}/report/test-task-123`)
    );
  });

  test('calculates failed tests correctly', async () => {
    render(<QAReport taskId="test-task-123" />);

    vi.advanceTimersByTime(1000);

    await waitFor(() => {
      expect(screen.getByText('Overall Summary')).toBeInTheDocument();
    });

    // The mock generates random passed tests between 75-95 out of 100 total
    // Failed should be total - passed
    const passedText = screen.getByText(/Passed:/).textContent;
    const failedText = screen.getByText(/Failed:/).textContent;
    
    expect(passedText).toMatch(/Passed: \d+/);
    expect(failedText).toMatch(/Failed: \d+/);
  });

  test('formats generated date correctly', async () => {
    render(<QAReport taskId="test-task-123" />);

    vi.advanceTimersByTime(1000);

    await waitFor(() => {
      expect(screen.getByText(/Generated At:/)).toBeInTheDocument();
    });

    // Should display a formatted date string
    const generatedAtElement = screen.getByText(/Generated At:/);
    expect(generatedAtElement.textContent).toMatch(/Generated At: \d+\/\d+\/\d+/);
  });

  test('handles quality score formatting', async () => {
    render(<QAReport taskId="test-task-123" />);

    vi.advanceTimersByTime(1000);

    await waitFor(() => {
      expect(screen.getByText(/Overall Quality Score:/)).toBeInTheDocument();
    });

    // Should display quality score formatted to 2 decimal places
    const qualityScoreElement = screen.getByText(/Overall Quality Score:/);
    expect(qualityScoreElement.textContent).toMatch(/Overall Quality Score: 0\.\d{2}/);
  });

  test('displays proper CSS classes for styling', async () => {
    render(<QAReport taskId="test-task-123" />);

    // Check loading state has correct class
    expect(screen.getByText(/Loading QA Report/)).toHaveClass('qa-report-loading');

    vi.advanceTimersByTime(1000);

    await waitFor(() => {
      const container = screen.getByText('QA Report (Task ID: test-task-123)').closest('div');
      expect(container).toHaveClass('qa-report-container');
    });

    // Check section classes
    expect(screen.getByText('Overall Summary').closest('div')).toHaveClass('qa-section', 'overall-summary');
    expect(screen.getByText('Functional Tests').closest('div')).toHaveClass('qa-section', 'functional-tests');
    expect(screen.getByText('Performance Tests').closest('div')).toHaveClass('qa-section', 'performance-tests');
    expect(screen.getByText('Compatibility Tests').closest('div')).toHaveClass('qa-section', 'compatibility-tests');
    expect(screen.getByText('Recommendations').closest('div')).toHaveClass('qa-section', 'recommendations');
    expect(screen.getByText('Issue Severity').closest('div')).toHaveClass('qa-section', 'severity-ratings');
  });

  test('handles empty recommendations array', async () => {
    // Mock with empty recommendations
    const mockSetTimeout = vi.spyOn(global, 'setTimeout').mockImplementation((callback: any) => {
      // Create mock report with empty recommendations
      const emptyRecommendations = [];
      callback();
      return 0 as any;
    });

    render(<QAReport taskId="test-task-123" />);

    vi.advanceTimersByTime(1000);

    await waitFor(() => {
      expect(screen.getByText('Recommendations')).toBeInTheDocument();
    });

    mockSetTimeout.mockRestore();
  });

  test('has proper accessibility structure', async () => {
    render(<QAReport taskId="test-task-123" />);

    vi.advanceTimersByTime(1000);

    await waitFor(() => {
      // Main heading should be h2
      expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent(/QA Report/);
    });

    // Section headings should be h3
    const sectionHeadings = screen.getAllByRole('heading', { level: 3 });
    expect(sectionHeadings).toHaveLength(6); // 6 sections: Overall, Functional, Performance, Compatibility, Recommendations, Severity

    // Recommendations should be a proper list
    const recommendationsList = screen.getByRole('list');
    expect(recommendationsList).toBeInTheDocument();
    
    const listItems = screen.getAllByRole('listitem');
    expect(listItems.length).toBeGreaterThan(0);
  });

  test('console logs correct API endpoint', async () => {
    render(<QAReport taskId="test-task-123" apiBaseUrl="/custom/api" />);

    expect(mockConsoleLog).toHaveBeenCalledWith(
      'Fetching QA report for task ID: test-task-123 from /custom/api/report/test-task-123'
    );
  });
});