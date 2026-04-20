import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import ConversionHistory from './ConversionHistory';
import { ConversionHistoryItem } from './types';
import React from 'react';

// Mock the API module
vi.mock('../../services/api', () => ({
  listConversions: vi.fn(),
  billingAPI: {
    getSubscriptionStatus: vi.fn(),
    getUsageInfo: vi.fn(),
  },
  downloadConversionReport: vi.fn(),
  triggerDownload: vi.fn(),
}));

import { listConversions, billingAPI } from '../../services/api';

const mockUsageInfo = {
  tier: 'free',
  period_year: 2026,
  period_month: 4,
  web_conversions: 5,
  api_conversions: 0,
  monthly_limit: 10,
  api_limit: 100,
  remaining: 5,
  api_remaining: 100,
  is_at_limit: false,
  is_api_at_limit: false,
  should_upgrade: false,
  upgrade_message: null,
};

describe('ConversionHistory', () => {
  const mockApiHistoryItems = [
    {
      conversion_id: 'job-1',
      original_filename: 'test-mod.jar',
      status: 'completed',
      created_at: '2026-02-18T00:37:20.000Z',
      updated_at: '2026-02-18T00:37:25.000Z',
    },
    {
      conversion_id: 'job-2',
      original_filename: 'another-mod.zip',
      status: 'processing',
      created_at: '2026-02-18T00:37:10.000Z',
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    (listConversions as ReturnType<typeof vi.fn>).mockResolvedValue({
      conversions: mockApiHistoryItems,
      total: 2,
      page: 1,
      page_size: 20,
    });
    (
      billingAPI.getSubscriptionStatus as ReturnType<typeof vi.fn>
    ).mockResolvedValue(null);
    (billingAPI.getUsageInfo as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockUsageInfo
    );
  });

  it('renders history items from API', async () => {
    render(<ConversionHistory />);

    await waitFor(() => {
      expect(screen.getByText('test-mod.jar')).toBeInTheDocument();
      expect(screen.getByText('another-mod.zip')).toBeInTheDocument();
    });

    const completedStatuses = screen.getAllByText('Completed');
    const statusSpans = completedStatuses.filter(
      (el) => el.className === 'status'
    );
    expect(statusSpans.length).toBeGreaterThanOrEqual(1);

    const processingStatuses = screen.getAllByText('Processing');
    const processingStatusSpans = processingStatuses.filter(
      (el) => el.className === 'status'
    );
    expect(processingStatusSpans.length).toBeGreaterThanOrEqual(1);
  });

  it('handles item selection', async () => {
    render(<ConversionHistory />);

    await waitFor(() => {
      expect(screen.getByText('test-mod.jar')).toBeInTheDocument();
    });

    const checkbox = screen.getByLabelText('Select test-mod.jar');
    fireEvent.click(checkbox);

    expect(screen.getByText(/Delete Selected/i)).toBeInTheDocument();
  });

  it('deletes an item after confirmation', async () => {
    render(<ConversionHistory />);

    await waitFor(() => {
      expect(screen.getByText('test-mod.jar')).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByTitle('Remove from history');
    fireEvent.click(deleteButtons[0]);

    const confirmButton = await screen.findByTitle('Confirm deletion');
    expect(confirmButton).toBeInTheDocument();

    fireEvent.click(confirmButton);

    await waitFor(() => {
      expect(screen.queryByText('test-mod.jar')).not.toBeInTheDocument();
    });
  });
});
