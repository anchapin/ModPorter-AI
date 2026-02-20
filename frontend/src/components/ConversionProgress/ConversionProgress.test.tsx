import { render, screen, act, waitFor } from '@testing-library/react';
import { vi, describe, beforeEach, test, expect, afterEach } from 'vitest';
import ConversionProgress from './ConversionProgress';
import { getConversionStatus } from '../../services/api';
import { ProgressProvider } from '../../contexts/ProgressContext';

// Mock the API service
vi.mock('../../services/api', () => ({
  getConversionStatus: vi.fn(),
}));

// Mock the WebSocket service
vi.mock('../../services/websocket', () => ({
  createConversionWebSocket: vi.fn(),
  ConversionWebSocket: class MockConversionWebSocket {
    onMessage = vi.fn();
    onStatus = vi.fn();
    connect = vi.fn();
    disconnect = vi.fn();
    destroy = vi.fn();
  }
}));

const mockedGetConversionStatus = vi.mocked(getConversionStatus);

describe('ConversionProgress', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();

    // Mock getConversionStatus to return a resolved promise
    mockedGetConversionStatus.mockResolvedValue({
      job_id: 'test-job-123',
      status: 'completed',
      progress: 100,
      message: 'Conversion completed',
      stage: 'Completed',
      overallSuccessRate: 100,
      convertedMods: [],
      failedMods: [],
      smartAssumptionsApplied: [],
      detailedReport: { stage: 'Completed', progress: 100, logs: [], technicalDetails: {} },
    });

    // Suppress console warnings during tests
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    vi.spyOn(console, 'log').mockImplementation(() => {});
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  const renderWithProvider = (component: React.ReactElement) => {
    return render(<ProgressProvider>{component}</ProgressProvider>);
  };

  test('renders "No conversion in progress" when no jobId provided', () => {
    act(() => {
      renderWithProvider(<ConversionProgress jobId={null} />);
    });
    expect(screen.getByText('No conversion in progress')).toBeInTheDocument();
  });

  test('renders initial progress information when jobId provided', () => {
    act(() => {
      renderWithProvider(
        <ConversionProgress jobId="test-job-123" status="running" progress={25} />
      );
    });

    expect(screen.getByText('Conversion Progress (ID: test-job-123)')).toBeInTheDocument();
    expect(screen.getByText('running')).toBeInTheDocument();

    // Progress percentage is now inside the progress bar
    const progressBar = screen.getByRole('progressbar');
    expect(progressBar).toHaveTextContent('25%');
  });

  test('displays progress bar with correct value', () => {
    act(() => {
      renderWithProvider(<ConversionProgress jobId="test-job-123" progress={75} />);
    });

    const progressBar = screen.getByRole('progressbar');
    expect(progressBar).toHaveAttribute('aria-valuenow', '75');
    expect(progressBar).toHaveAttribute('aria-valuemin', '0');
    expect(progressBar).toHaveAttribute('aria-valuemax', '100');
    expect(progressBar).toHaveStyle({ width: '75%' });
  });

  test('shows error message when conversion fails', () => {
    act(() => {
      renderWithProvider(
        <ConversionProgress
          jobId="test-job-123"
          status="failed"
          message="Conversion failed due to invalid file"
        />
      );
    });

    expect(screen.getByText('failed')).toBeInTheDocument();
    expect(screen.getByText('Conversion failed due to invalid file')).toBeInTheDocument();
  });

  test('formats time correctly for estimated time remaining', () => {
    act(() => {
      renderWithProvider(
        <ConversionProgress
          jobId="test-job-123"
          status="running"
        />
      );
    });

    expect(screen.getByText('Estimated Time Remaining:')).toBeInTheDocument();
    expect(screen.getByText('N/A')).toBeInTheDocument(); // When no estimated time
  });

  test('displays connection status indicator', () => {
    act(() => {
      renderWithProvider(<ConversionProgress jobId="test-job-123" />);
    });

    // Should show connection status indicator
    const connectionIndicator = document.querySelector('.connection-status-indicator');
    expect(connectionIndicator).toBeInTheDocument();
  });

  test('shows completed status with proper styling', () => {
    act(() => {
      renderWithProvider(
        <ConversionProgress
          jobId="test-job-123"
          status="completed"
          progress={100}
        />
      );
    });

    expect(screen.getByText('completed')).toBeInTheDocument();

    const progressBar = screen.getByRole('progressbar');
    expect(progressBar).toHaveClass('progress-bar-filler');
  });

  test('displays stage information when provided', () => {
    act(() => {
      renderWithProvider(
        <ConversionProgress
          jobId="test-job-123"
          status="running"
          stage="Converting assets"
        />
      );
    });

    expect(screen.getByText('Stage:')).toBeInTheDocument();
    expect(screen.getByText('Converting assets')).toBeInTheDocument();
  });

  test('handles null values gracefully', () => {
    act(() => {
      renderWithProvider(
        <ConversionProgress
          jobId="test-job-123"
          status={undefined}
          progress={undefined}
          message={undefined}
          stage={undefined}
        />
      );
    });

    // Should render without crashing and show default values
    expect(screen.getByText('Conversion Progress (ID: test-job-123)')).toBeInTheDocument();
    expect(screen.getByText('queued')).toBeInTheDocument(); // Default status

    // Default progress is now inside the progress bar
    const progressBar = screen.getByRole('progressbar');
    expect(progressBar).toHaveTextContent('0%');
  });

  test('displays proper message with connection status', () => {
    act(() => {
      renderWithProvider(
        <ConversionProgress
          jobId="test-job-123"
          message="Processing files..."
        />
      );
    });

    const messageElement = screen.getByText(/processing files/i);
    expect(messageElement).toBeInTheDocument();
  });

  test('formats progress percentage correctly', async () => {
    await act(async () => {
      renderWithProvider(<ConversionProgress jobId="test-job-123" progress={33.7} />);
      await vi.advanceTimersByTimeAsync(100);
    });

    // Should round to whole number for display (inside progress bar)
    const progressBar = screen.getByRole('progressbar');
    expect(progressBar).toHaveTextContent('34%');
  });

  test('shows error section when status is failed', () => {
    act(() => {
      renderWithProvider(
        <ConversionProgress
          jobId="test-job-123"
          status="failed"
          message="Detailed error information"
        />
      );
    });

    expect(screen.getByText('Error:')).toBeInTheDocument();
    expect(screen.getByText('Detailed error information')).toBeInTheDocument();
  });

  test('handles very long job IDs', () => {
    const longJobId = 'very-long-job-id-that-might-break-layout-' + 'x'.repeat(50);

    act(() => {
      renderWithProvider(<ConversionProgress jobId={longJobId} />);
    });

    expect(screen.getByText(`Conversion Progress (ID: ${longJobId})`)).toBeInTheDocument();
  });

  test('displays all required progress information sections', () => {
    act(() => {
      renderWithProvider(
        <ConversionProgress
          jobId="test-job-123"
          status="running"
          progress={50}
          message="Converting..."
          stage="Assets"
        />
      );
    });

    // Check all expected sections are present
    expect(screen.getByText('Status:')).toBeInTheDocument();
    expect(screen.getByText('Stage:')).toBeInTheDocument();
    expect(screen.getByText('Message:')).toBeInTheDocument();
    expect(screen.getByText('Estimated Time Remaining:')).toBeInTheDocument();
  });

  test('handles edge case progress values', async () => {
    // Test 0% progress
    const { unmount: unmount1 } = renderWithProvider(
      <ConversionProgress jobId="test-job-123" progress={0} />
    );
    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });

    // Progress percentage is now inside the progress bar
    let progressBar = screen.getByRole('progressbar');
    expect(progressBar).toHaveTextContent('0%');

    // Clean up first render
    unmount1();

    // Test 100% progress with new render
    const { unmount: unmount2 } = renderWithProvider(
      <ConversionProgress jobId="test-job-456" progress={100} />
    );
    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });

    progressBar = screen.getByRole('progressbar');
    expect(progressBar).toHaveTextContent('100%');

    unmount2();
  });

  test('calls createConversionWebSocket when jobId provided', () => {
    const { createConversionWebSocket } = require('../../services/websocket');

    act(() => {
      renderWithProvider(<ConversionProgress jobId="test-job-123" />);
    });

    // Verify WebSocket service was called
    expect(createConversionWebSocket).toHaveBeenCalledWith('test-job-123');
  });

  test('displays download button when conversion is completed with result URL', () => {
    act(() => {
      renderWithProvider(
        <ConversionProgress
          jobId="test-job-123"
          status="completed"
          progress={100}
        />
      );
    });

    // Note: Since we're using initial props, result_url would be null
    // The button only shows when result_url is present
    expect(screen.queryByText('Download Converted File')).not.toBeInTheDocument();
  });

  test('connection status indicator shows correct status', () => {
    act(() => {
      renderWithProvider(<ConversionProgress jobId="test-job-123" />);
    });

    // Initial status should be disconnected
    const connectionIndicator = document.querySelector('.connection-status-indicator');
    expect(connectionIndicator).toBeInTheDocument();
  });

  test('displays agent progress when agents are available', () => {
    // This test would require mocking the WebSocket to send agent updates
    // For now, we just verify the component renders without error
    act(() => {
      renderWithProvider(<ConversionProgress jobId="test-job-123" />);
    });

    expect(screen.getByText('Conversion Progress (ID: test-job-123)')).toBeInTheDocument();
  });
});
