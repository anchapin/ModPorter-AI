import { render, screen } from '@testing-library/react';
import { vi, describe, test, expect } from 'vitest';
import QAReport from './QAReport';

// Mock the component's useState and useEffect to avoid async complications
vi.mock('react', async () => {
  const actual = await vi.importActual('react');
  return {
    ...actual,
    useState: vi.fn(),
    useEffect: vi.fn(),
  };
});

describe('QAReport', () => {
  test('shows loading state initially', () => {
    const { useState } = require('react');
    
    // Mock useState to return loading state
    useState
      .mockReturnValueOnce([null, vi.fn()]) // report state
      .mockReturnValueOnce([true, vi.fn()]) // loading state  
      .mockReturnValueOnce([null, vi.fn()]); // error state

    render(<QAReport taskId="test-task-123" />);

    expect(screen.getByText('Loading QA Report for Task ID: test-task-123...')).toBeInTheDocument();
  });

  test('shows error when no task ID provided', () => {
    const { useState } = require('react');
    
    // Mock useState to return error state
    useState
      .mockReturnValueOnce([null, vi.fn()]) // report state
      .mockReturnValueOnce([false, vi.fn()]) // loading state  
      .mockReturnValueOnce(['Task ID is required to fetch a QA report.', vi.fn()]); // error state

    render(<QAReport taskId="" />);

    expect(screen.getByText('Error: Task ID is required to fetch a QA report.')).toBeInTheDocument();
  });

  test('displays QA report data when loaded', () => {
    const { useState } = require('react');
    
    const mockReport = {
      report_id: 'report_test-task-123',
      task_id: 'test-task-123',
      conversion_id: 'conv_for_test-task-123',
      generated_at: new Date().toISOString(),
      overall_quality_score: 0.85,
      summary: {
        total_tests: 100,
        passed: 90,
      },
      functional_tests: { passed: 40, failed: 1 },
      performance_tests: { cpu_avg: "20%", memory_peak: "250MB" },
      compatibility_tests: { versions_tested: ["1.19.0", "1.20.0"] },
      recommendations: ["Review item placement logic."],
      severity_ratings: { critical: 0, major: 1, minor: 2 }
    };
    
    // Mock useState to return loaded report state
    useState
      .mockReturnValueOnce([mockReport, vi.fn()]) // report state
      .mockReturnValueOnce([false, vi.fn()]) // loading state  
      .mockReturnValueOnce([null, vi.fn()]); // error state

    render(<QAReport taskId="test-task-123" />);

    expect(screen.getByText('QA Report (Task ID: test-task-123)')).toBeInTheDocument();
    expect(screen.getByText(/Report ID:/)).toBeInTheDocument();
    expect(screen.getByText(/Overall Quality Score:/)).toBeInTheDocument();
  });
});