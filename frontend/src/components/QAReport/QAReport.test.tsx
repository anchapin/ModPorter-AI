import { render, screen, waitFor } from '@testing-library/react';
import { vi, describe, test, expect, beforeEach, afterEach } from 'vitest';
import QAReport from './QAReport';

describe('QAReport', () => {
  test('shows loading state initially', () => {
    render(<QAReport taskId="test-task-123" />);
    expect(screen.getByText('Loading QA Report for Task ID: test-task-123...')).toBeInTheDocument();
  });

  test('shows error when no task ID provided', () => {
    render(<QAReport taskId="" />);
    expect(screen.getByText('Error: Task ID is required to fetch a QA report.')).toBeInTheDocument();
  });

  test('displays QA report data after loading', async () => {
    render(<QAReport taskId="test-task-123" />);
    
    // Initially shows loading
    expect(screen.getByText('Loading QA Report for Task ID: test-task-123...')).toBeInTheDocument();
    
    // Wait for the component to update after the async timeout
    await waitFor(() => {
      expect(screen.getByText('QA Report (Task ID: test-task-123)')).toBeInTheDocument();
    }, { timeout: 3000 });
    
    expect(screen.getByText(/Report ID:/)).toBeInTheDocument();
    expect(screen.getByText(/Overall Quality Score:/)).toBeInTheDocument();
  });
});