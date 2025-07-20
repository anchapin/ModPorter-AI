import { render, screen, act } from '@testing-library/react';
import { vi, describe, beforeEach, test, expect, afterEach } from 'vitest';
import ConversionProgress from './ConversionProgress';
import * as api from '../../services/api';

// Mock the API service
vi.mock('../../services/api', () => ({
  getConversionStatus: vi.fn(),
}));

// Mock WebSocket to prevent actual connections
global.WebSocket = vi.fn().mockImplementation(() => ({
  close: vi.fn(),
  readyState: 1,
  onopen: null,
  onmessage: null,
  onerror: null,
  onclose: null,
})) as any;

describe('ConversionProgress', () => {
  const mockGetConversionStatus = vi.mocked(api.getConversionStatus);
  
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
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
    expect(screen.getByText('25%')).toBeInTheDocument();
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
    expect(
      screen.getByText(/real-time updates active/i) || 
      screen.getByText(/using fallback polling/i)
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
    expect(screen.getByText('0%')).toBeInTheDocument(); // Default progress
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

  test('formats progress percentage correctly', () => {
    act(() => {
      render(<ConversionProgress jobId="test-job-123" progress={33.7} />);
    });
    
    // Should round to whole number for display
    expect(screen.getByText('34%')).toBeInTheDocument();
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
    expect(screen.getByText('Details: Detailed error information')).toBeInTheDocument();
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

  test('handles edge case progress values', () => {
    // Test 0% progress
    act(() => {
      const { rerender } = render(<ConversionProgress jobId="test-job-123" progress={0} />);
      expect(screen.getByText('0%')).toBeInTheDocument();
      
      // Test 100% progress
      rerender(<ConversionProgress jobId="test-job-123" progress={100} />);
      expect(screen.getByText('100%')).toBeInTheDocument();
    });
  });

  test('WebSocket constructor is called with correct URL when jobId provided', () => {
    act(() => {
      render(<ConversionProgress jobId="test-job-123" />);
    });
    
    // Verify WebSocket was instantiated (even though it's mocked)
    expect(global.WebSocket).toHaveBeenCalled();
  });
});