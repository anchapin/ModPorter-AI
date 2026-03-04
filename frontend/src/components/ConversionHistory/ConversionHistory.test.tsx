import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import ConversionHistory from './ConversionHistory';
import { ConversionHistoryItem } from './types';
import React from 'react';

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value.toString();
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

// Mock fetch
global.fetch = vi.fn();

describe('ConversionHistory', () => {
  const mockHistoryItems: ConversionHistoryItem[] = [
    {
      job_id: 'job-1',
      original_filename: 'test-mod.jar',
      status: 'completed',
      created_at: '2026-02-18T00:37:20.000Z', // Fixed date for consistency
      file_size: 1024 * 1024, // 1MB
    },
    {
      job_id: 'job-2',
      original_filename: 'another-mod.zip',
      status: 'processing',
      created_at: '2026-02-18T00:37:10.000Z',
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();
    // Setup initial localStorage data
    localStorageMock.setItem(
      'modporter_conversion_history',
      JSON.stringify(mockHistoryItems)
    );
  });

  it('renders history items from localStorage', async () => {
    render(<ConversionHistory />);

    // Check items loaded
    await waitFor(() => {
      expect(screen.getByText('test-mod.jar')).toBeInTheDocument();
      expect(screen.getByText('another-mod.zip')).toBeInTheDocument();
    });

    // Check status icons/text
    expect(screen.getByText('Completed')).toBeInTheDocument();
    expect(screen.getByText('Processing')).toBeInTheDocument();
  });

  it('handles item selection', async () => {
    render(<ConversionHistory />);

    await waitFor(() => {
      expect(screen.getByText('test-mod.jar')).toBeInTheDocument();
    });

    const checkbox = screen.getByLabelText('Select test-mod.jar');
    fireEvent.click(checkbox);

    // Check if delete selected button appears
    expect(screen.getByText(/Delete Selected/i)).toBeInTheDocument();
  });

  it('deletes an item after confirmation', async () => {
    render(<ConversionHistory />);

    await waitFor(() => {
      expect(screen.getByText('test-mod.jar')).toBeInTheDocument();
    });

    // 1. Click delete button (trash icon)
    const deleteButtons = screen.getAllByTitle('Remove from history');
    fireEvent.click(deleteButtons[0]);

    // 2. Expect confirmation buttons to appear
    const confirmButton = await screen.findByTitle('Confirm deletion');
    expect(confirmButton).toBeInTheDocument();

    // 3. Click confirm
    fireEvent.click(confirmButton);

    // 4. Verify item is removed
    await waitFor(() => {
      expect(screen.queryByText('test-mod.jar')).not.toBeInTheDocument();
    });

    // Verify localStorage update
    expect(localStorageMock.setItem).toHaveBeenCalled();
  });
});
