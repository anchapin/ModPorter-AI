import { render, screen, act } from '@testing-library/react';
import { vi, describe, beforeEach, test, expect, afterEach } from 'vitest';
import ConversionProgress from './ConversionProgress';
import { getConversionStatus } from '../../services/api';

// Mock the API service
vi.mock('../../services/api', () => ({
  getConversionStatus: vi.fn(),
}));

const mockedGetConversionStatus = vi.mocked(getConversionStatus);

// Enhanced WebSocket mock with proper constructor implementation
class MockWebSocket {
  url: string;
  close: ReturnType<typeof vi.fn>;
  readyState: number;
  onopen: any;
  onmessage: any;
  onerror: any;
  onclose: any;
  addEventListener: ReturnType<typeof vi.fn>;
  removeEventListener: ReturnType<typeof vi.fn>;
  send: ReturnType<typeof vi.fn>;

  constructor(url: string) {
    this.url = url;
    this.close = vi.fn();
    this.readyState = MockWebSocket.CONNECTING;
    this.onopen = null;
    this.onmessage = null;
    this.onerror = null;
    this.onclose = null;
    this.addEventListener = vi.fn();
    this.removeEventListener = vi.fn();
    this.send = vi.fn();
    
    // Store constructor calls for testing
    MockWebSocket.instances.push(this);
    
    // Simulate connection opening after construction
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      if (this.onopen) {
        this.onopen({ type: 'open' });
      }
    }, 0);
  }
  
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;
  static instances: MockWebSocket[] = [];
  static clearInstances = () => {
    MockWebSocket.instances = [];
  };
}

// Replace global WebSocket with the mock directly
global.WebSocket = MockWebSocket as any;
global.WebSocket.CONNECTING = MockWebSocket.CONNECTING;
global.WebSocket.OPEN = MockWebSocket.OPEN;
global.WebSocket.CLOSING = MockWebSocket.CLOSING;
global.WebSocket.CLOSED = MockWebSocket.CLOSED;
global.WebSocket.instances = MockWebSocket.instances;
global.WebSocket.clearInstances = MockWebSocket.clearInstances;

describe('ConversionProgress', () => {
  // const mockGetConversionStatus = vi.mocked(api.getConversionStatus);
  
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    MockWebSocket.clearInstances();
    
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
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  test('renders "No conversion in progress" when no jobId provided', () => {
    act(() => {
      render(<ConversionProgress jobId={null} />);
    });
    expect(screen.getByText('No conversion in progress')).toBeInTheDocument();
  });

  test('renders initial progress information when jobId provided', () => {
    act(() => {
      render(<ConversionProgress jobId="test-job-123" status="running" progress={25} />);
    });
    
    expect(screen.getByText('Conversion Progress (ID: test-job-123)')).toBeInTheDocument();
    expect(screen.getByText('running')).toBeInTheDocument();
    
    // Progress percentage is now inside the progress bar
    const progressBar = screen.getByRole('progressbar');
    expect(progressBar).toHaveTextContent('25%');
  });

  test('displays progress bar with correct value', () => {
    act(() => {
      render(<ConversionProgress jobId="test-job-123" progress={75} />);
    });
    
    const progressBar = screen.getByRole('progressbar');
    expect(progressBar).toHaveAttribute('aria-valuenow', '75');
    expect(progressBar).toHaveAttribute('aria-valuemin', '0');
    expect(progressBar).toHaveAttribute('aria-valuemax', '100');
    expect(progressBar).toHaveStyle({ width: '75%' });
  });

  test('shows error message when conversion fails', () => {
    act(() => {
      render(
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
      render(
        <ConversionProgress 
          jobId="test-job-123" 
          status="running"
        />
      );
    });
    
    expect(screen.getByText('Estimated Time Remaining:')).toBeInTheDocument();
    expect(screen.getByText('N/A')).toBeInTheDocument(); // When no estimated time
  });

  test('displays connection method indicator', () => {
    act(() => {
      render(<ConversionProgress jobId="test-job-123" />);
    });
    
    // Should show either WebSocket or polling indicator
    // In tests, WebSocket is mocked so it will typically show polling
    expect(
      screen.queryByText('Real-time updates active') || 
      screen.queryByText('Using fallback polling')
    ).toBeInTheDocument();
  });

  test('shows completed status with proper styling', () => {
    act(() => {
      render(
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
      render(
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
      render(
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
      render(
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
      render(<ConversionProgress jobId="test-job-123" progress={33.7} />);
      await vi.advanceTimersByTimeAsync(100);
    });
    
    // Should round to whole number for display (inside progress bar)
    const progressBar = screen.getByRole('progressbar');
    expect(progressBar).toHaveTextContent('34%');
  });

  test('shows error section when status is failed', () => {
    act(() => {
      render(
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
      render(<ConversionProgress jobId={longJobId} />);
    });
    
    expect(screen.getByText(`Conversion Progress (ID: ${longJobId})`)).toBeInTheDocument();
  });

  test('displays all required progress information sections', () => {
    act(() => {
      render(
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
    const { unmount: unmount1 } = render(<ConversionProgress jobId="test-job-123" progress={0} />);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });
    
    // Progress percentage is now inside the progress bar
    let progressBar = screen.getByRole('progressbar');
    expect(progressBar).toHaveTextContent('0%');
    
    // Clean up first render
    unmount1();
    
    // Test 100% progress with new render
    const { unmount: unmount2 } = render(<ConversionProgress jobId="test-job-456" progress={100} />);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });
    
    progressBar = screen.getByRole('progressbar');
    expect(progressBar).toHaveTextContent('100%');
    
    unmount2();
  });

  test('WebSocket constructor is called with correct URL when jobId provided', async () => {
    await act(async () => {
      render(<ConversionProgress jobId="test-job-123" />);
      await vi.advanceTimersByTimeAsync(100);
    });
    
    // Verify WebSocket was instantiated (even though it's mocked)
    expect(MockWebSocket.instances).toHaveLength(1);
    expect(MockWebSocket.instances[0].url).toBe('ws://localhost:8080/ws/v1/convert/test-job-123/progress');
  });
});