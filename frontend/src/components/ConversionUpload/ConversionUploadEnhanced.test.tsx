import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConversionUploadEnhanced } from './ConversionUploadEnhanced';
import { describe, test, expect, vi } from 'vitest';

// Mock the API calls
vi.mock('../../services/api', () => ({
  convertMod: vi.fn(),
  getConversionStatus: vi.fn(),
  cancelJob: vi.fn(),
  downloadResult: vi.fn(),
}));

// Mock the WebSocket service
vi.mock('../../services/websocket', () => ({
  createConversionWebSocket: vi.fn(() => ({
    onStatus: vi.fn(),
    onMessage: vi.fn(),
    connect: vi.fn(),
    destroy: vi.fn(),
  })),
}));

describe('ConversionUploadEnhanced Accessibility', () => {
  test('Smart Assumptions info button has correct accessibility attributes', () => {
    render(<ConversionUploadEnhanced />);

    // Find the info button
    const infoButton = screen.getByText('?');

    // Check initial state
    expect(infoButton).toHaveClass('info-button');
    expect(infoButton).toHaveAttribute('aria-label', 'Learn more about smart assumptions');
    // These are the new attributes we expect to add
    expect(infoButton).toHaveAttribute('aria-expanded', 'false');
    expect(infoButton).toHaveAttribute('aria-controls', 'smart-assumptions-info');

    // Click to expand
    fireEvent.click(infoButton);

    // Check expanded state
    expect(infoButton).toHaveAttribute('aria-expanded', 'true');

    // Check if the info panel appears and has the correct ID
    const infoPanel = screen.getByText(/When enabled, our AI will make intelligent assumptions/i).closest('.info-panel');
    expect(infoPanel).toBeInTheDocument();
    expect(infoPanel).toHaveAttribute('id', 'smart-assumptions-info');
  });

  test('Remove file button has accessible name', async () => {
    const user = userEvent.setup();
    render(<ConversionUploadEnhanced />);

    // Upload a file
    const file = new File(['dummy content'], 'test-mod.jar', { type: 'application/java-archive' });
    const fileInput = screen.getByLabelText(/file upload/i);

    await user.upload(fileInput, file);

    // Wait for the file preview to appear
    await waitFor(() => {
      expect(screen.getByText('test-mod.jar')).toBeInTheDocument();
    });

    // Find the remove button
    const removeButton = screen.getByText('✕');

    // Check if it has an aria-label
    expect(removeButton).toHaveAttribute('aria-label', 'Remove test-mod.jar');
  });

  test('Error message has role="alert"', async () => {
    const user = userEvent.setup();
    render(<ConversionUploadEnhanced />);

    // Trigger an error via invalid URL
    const urlInput = screen.getByPlaceholderText(/curseforge/i);
    await user.type(urlInput, 'invalid-url');

    await waitFor(() => {
      expect(screen.getByText(/Please enter a valid URL/i)).toBeInTheDocument();
    });

    const errorMessage = screen.getByText(/Please enter a valid URL/i).closest('.error-message');
    expect(errorMessage).toHaveAttribute('role', 'alert');
  });
});
