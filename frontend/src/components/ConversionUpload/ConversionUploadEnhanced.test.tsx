import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConversionUploadEnhanced } from './ConversionUploadEnhanced';
import { describe, test, expect, vi } from 'vitest';
import { convertMod } from '../../services/api';

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
    const removeButton = screen.getByText('✕').closest('button');

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

  test('URL input has an accessible label', () => {
    render(<ConversionUploadEnhanced />);
    const urlInput = screen.getByLabelText('Modpack URL');
    expect(urlInput).toBeInTheDocument();
  });

  test('Button shows spinner when processing', async () => {
    const user = userEvent.setup();
    render(<ConversionUploadEnhanced />);

    // Check initial button text
    const submitButton = screen.getByText('Upload & Convert');
    expect(submitButton).toBeInTheDocument();
    expect(submitButton).toBeDisabled();

    // Upload a file
    const file = new File(['dummy content'], 'test-mod.jar', { type: 'application/java-archive' });
    const fileInput = screen.getByLabelText(/file upload/i);
    await user.upload(fileInput, file);

    // Wait for the file preview to appear and button to be enabled
    await waitFor(() => {
      expect(screen.getByText('test-mod.jar')).toBeInTheDocument();
      expect(submitButton).not.toBeDisabled();
    });

    // Mock the convertMod function to return a promise that doesn't resolve immediately
    // or resolves after a delay to allow us to check the loading state
    // Note: The existing mock is a simple fn(), we might need to adjust it or just rely on state changes
    // But since we are mocking module '../services/api', we rely on how it was mocked at top of file.
    // It is `convertMod: vi.fn()`.

    // Mock the convertMod function
    vi.mocked(convertMod).mockImplementation(() => new Promise(resolve => setTimeout(() => resolve({ job_id: '123' } as any), 100)));

    // Click submit
    await user.click(submitButton);

    // Check for spinner
    await waitFor(() => {
        // Check if button text changed (either Uploading or Processing, depending on timing)
        // Since the mock resolves fast, it likely goes to Processing
        const button = screen.getByRole('button', { name: /Processing|Uploading/i });
        expect(button).toBeInTheDocument();

        // Check if spinner exists by class name
        // React Testing Library doesn't recommend querying by class, but for this specific visual element it's acceptable
        // or we can query by aria-hidden, but that's not specific enough.
        // We can check if the span with class conversion-spinner is present in the document.
        const spinner = document.querySelector('.conversion-spinner');
        expect(spinner).toBeInTheDocument();
        expect(spinner).toHaveAttribute('aria-hidden', 'true');
    });
  });
});
