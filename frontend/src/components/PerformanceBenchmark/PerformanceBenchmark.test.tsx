import { render, screen, waitFor, act } from '@testing-library/react';
import { vi, describe, beforeEach, test, expect } from 'vitest';
import { PerformanceBenchmark } from './PerformanceBenchmark';

// Mock the API service
vi.mock('../../services/api', () => ({
  performanceBenchmarkAPI: {
    getScenarios: vi.fn(),
    runBenchmark: vi.fn(),
    getBenchmarkStatus: vi.fn(),
    getBenchmarkReport: vi.fn(),
    createCustomScenario: vi.fn(),
  },
}));

describe('PerformanceBenchmark', () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    // Mock successful scenarios loading by default
    const { performanceBenchmarkAPI } = await import('../../services/api');
    performanceBenchmarkAPI.getScenarios.mockResolvedValue({ data: [] });
  });

  test('renders without crashing', async () => {
    await act(async () => {
      render(<PerformanceBenchmark />);
    });
    expect(screen.getByText('Performance Benchmarking')).toBeInTheDocument();
  });

  test('displays scenario selection dropdown', async () => {
    await act(async () => {
      render(<PerformanceBenchmark />);
    });
    expect(screen.getByLabelText('Select Scenario:')).toBeInTheDocument();
  });

  test('displays device type selection', async () => {
    await act(async () => {
      render(<PerformanceBenchmark />);
    });
    expect(screen.getByLabelText('Device Type:')).toBeInTheDocument();
  });

  test('displays conversion ID input', async () => {
    await act(async () => {
      render(<PerformanceBenchmark />);
    });
    expect(screen.getByLabelText('Conversion ID (optional):')).toBeInTheDocument();
  });

  test('displays run benchmark button', async () => {
    await act(async () => {
      render(<PerformanceBenchmark />);
    });
    expect(screen.getByRole('button', { name: 'Run Benchmark' })).toBeInTheDocument();
  });

  test('displays create custom scenario button', async () => {
    await act(async () => {
      render(<PerformanceBenchmark />);
    });
    expect(screen.getByRole('button', { name: 'Create Custom Scenario' })).toBeInTheDocument();
  });

  test('run benchmark button is disabled when no scenario is selected', async () => {
    await act(async () => {
      render(<PerformanceBenchmark />);
    });
    const runButton = screen.getByRole('button', { name: 'Run Benchmark' });
    expect(runButton).toBeDisabled();
  });

  test('loads scenarios on mount', async () => {
    const mockGetScenarios = vi.fn().mockResolvedValue({
      data: [
        {
          scenario_id: 'test-scenario',
          scenario_name: 'Test Scenario',
          description: 'Test description',
          type: 'baseline',
          duration_seconds: 300,
          parameters: {},
          thresholds: {}
        }
      ]
    });

    const { performanceBenchmarkAPI } = await import('../../services/api');
    (performanceBenchmarkAPI.getScenarios as any).mockImplementation(mockGetScenarios);

    await act(async () => {
      render(<PerformanceBenchmark />);
    });

    await waitFor(() => {
      expect(mockGetScenarios).toHaveBeenCalledTimes(1);
    });
  });

  test('displays error message when scenarios fail to load', async () => {
    const mockGetScenarios = vi.fn().mockRejectedValue(new Error('Failed to load'));

    const { performanceBenchmarkAPI } = await import('../../services/api');
    (performanceBenchmarkAPI.getScenarios as any).mockImplementation(mockGetScenarios);

    await act(async () => {
      render(<PerformanceBenchmark />);
    });

    await waitFor(() => {
      expect(screen.getByText('Failed to load scenarios')).toBeInTheDocument();
    });
  });
});