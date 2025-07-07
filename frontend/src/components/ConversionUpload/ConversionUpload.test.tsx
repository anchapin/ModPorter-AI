/**
 * Test-driven development for PRD Feature 1: One-Click Modpack Ingestion
 * Visual learner-friendly component testing (updated for Vitest)
 */

import React, { act } from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { vi } from 'vitest'; // Keep for other potential mocks if needed, or remove if not used elsewhere
import { ConversionUpload } from './ConversionUpload';
import { ConversionStatusEnum } from '../../types/api';
// MSW server is set up in `src/test/setup.ts` and will intercept API calls.
// No need to mock '../../services/api' here if MSW is handling it.

// Helper function to create a mock file
const createMockFile = (name: string, size: number, type: string): File => {
  const file = new File(['a'.repeat(size)], name, { type });
  return file;
};


describe('ConversionUpload Component', () => {
  // beforeEach(() => {
  //   vi.clearAllMocks(); // If you have other vi.fn mocks, keep this. Otherwise, can be removed.
  // });

  // --- Existing Unit/UI Tests (can be kept, ensure they don't conflict with MSW) ---
  describe('Visual Interface and Form Logic', () => {
    test('renders upload interface with clear visual cues', () => {
      render(<ConversionUpload />);
      expect(screen.getByText(/drag.*drop/i)).toBeInTheDocument();
      expect(screen.getByText(/CurseForge.*Modrinth/)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /convert to bedrock/i })).toBeInTheDocument();
      expect(screen.getByLabelText(/file upload/i)).toBeInTheDocument();
    });

    test('displays supported file types clearly', () => {
      render(<ConversionUpload />);
      expect(screen.getByText(/\.jar files/i)).toBeInTheDocument();
      expect(screen.getByText(/\.zip modpack archives/i)).toBeInTheDocument();
    });

    test('shows URL input option as alternative', () => {
      render(<ConversionUpload />);
      expect(screen.getByPlaceholderText(/curseforge.*modrinth/i)).toBeInTheDocument();
      expect(screen.getByText(/or paste url/i)).toBeInTheDocument();
    });
  });

  describe('URL Validation', () => {
    test('validates URL types according to PRD specs', async () => {
      const user = userEvent.setup();
      render(<ConversionUpload />);
      const urlInput = screen.getByPlaceholderText(/curseforge.*modrinth/i);
      await act(async () => { await user.type(urlInput, 'https://invalid-site.com/mod'); });
      await waitFor(() => {
        expect(screen.getByText(/Please enter a valid CurseForge or Modrinth URL/)).toBeInTheDocument();
      });
    });

    test('accepts valid CurseForge URLs', async () => {
      const user = userEvent.setup();
      render(<ConversionUpload />);
      const urlInput = screen.getByPlaceholderText(/curseforge.*modrinth/i);
      await act(async () => { await user.type(urlInput, 'https://www.curseforge.com/minecraft/mc-mods/example-mod');});
      expect(screen.queryByText(/Invalid URL/)).not.toBeInTheDocument();
    });
  });

  describe('Smart Assumptions UI', () => {
    test('displays smart assumptions toggle with explanation', () => {
      render(<ConversionUpload />);
      const toggle = screen.getByRole('checkbox', { name: /enable smart assumptions/i });
      expect(toggle).toBeInTheDocument();
      expect(toggle).toBeChecked();
      expect(screen.getByText(/intelligent assumptions to convert incompatible features/i)).toBeInTheDocument();
    });

    test('shows smart assumptions examples when info button clicked', async () => {
      const user = userEvent.setup();
      render(<ConversionUpload />);
      const infoButton = screen.getByRole('button', { name: /learn more about smart assumptions/i });
      await act(async () => { await user.click(infoButton); });
      expect(screen.getByText(/Smart Assumptions/i)).toBeInTheDocument();
      expect(screen.getByText(/Custom Dimensions/i)).toBeInTheDocument();
    });
  });

  describe('Basic Functionality', () => {
    test('convert button is disabled without file or URL', () => {
      render(<ConversionUpload />);
      const convertButton = screen.getByRole('button', { name: /convert to bedrock/i });
      expect(convertButton).toBeDisabled();
    });

    test('shows dependencies toggle', () => {
      render(<ConversionUpload />);
      const dependenciesToggle = screen.getByRole('checkbox', { name: /include dependencies/i });
      expect(dependenciesToggle).toBeInTheDocument();
      expect(dependenciesToggle).toBeChecked();
    });
  });

  // --- New Integration Tests with MSW ---
  describe('API Integration Tests', () => {
    test('handles successful file upload, conversion, and download', async () => {
      const user = userEvent.setup({ delay: null }); // Use delay: null for faster user events in async tests
      const onConversionCompleteListener = vi.fn();
      render(<ConversionUpload onConversionComplete={onConversionCompleteListener} />);

      // 1. Upload a file
      const fileInput = screen.getByLabelText(/file upload/i);
      const mockFile = createMockFile('test-mod.zip', 1024, 'application/zip');
      await act(async () => { await user.upload(fileInput, mockFile); });

      expect(screen.getByText(mockFile.name)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /convert to bedrock/i })).not.toBeDisabled();

      // 2. Click convert
      await act(async () => { await user.click(screen.getByRole('button', { name: /convert to bedrock/i })); });

      // 3. Check for initial status (e.g., PENDING or ANALYZING from mock)
      // MSW handler for POST /convert returns PENDING with 10% progress initially
      await waitFor(() => {
        expect(screen.getByText(/Queued for processing.../i)).toBeInTheDocument();
      }, { timeout: 2000 }); // Wait for initial state after convertMod

      // Polling should occur (mocked by MSW to simulate progress)
      // Status progression: PENDING -> ANALYZING -> CONVERTING -> PACKAGING -> COMPLETED
      // Timeout for waitFor needs to be generous enough for multiple poll intervals (2s each)
      await waitFor(() => {
        expect(screen.getByText(/Analyzing mod structure \(25%\)\.\.\./i)).toBeInTheDocument();
      }, { timeout: 3000 }); // First poll update

      await waitFor(() => {
        expect(screen.getByText(/AI processing and converting \(50%\)\.\.\./i)).toBeInTheDocument();
      }, { timeout: 3000 }); // Second poll update

      await waitFor(() => {
        expect(screen.getByText(/Packaging Bedrock add-on \(75%\)\.\.\./i)).toBeInTheDocument();
      }, { timeout: 3000 }); // Third poll update

      // 4. Check for completed status
      await waitFor(() => {
        expect(screen.getByText(/Conversion successful!/i)).toBeInTheDocument();
      }, { timeout: 3000});

      expect(onConversionCompleteListener).toHaveBeenCalled();
      // Check if the download button is available
      const downloadButton = screen.getByRole('button', { name: /download converted mod/i });
      expect(downloadButton).toBeInTheDocument();

      // 5. Click download (actual download is mocked by MSW)
      // We can't check actual file system download, but can check if API was called
      // For now, just clicking is enough to see no errors.
      // If `downloadResult` in api.ts returned something or threw specific error, we could check that.
      window.URL.createObjectURL = vi.fn(() => 'mock-url'); // Mock createObjectURL
      window.URL.revokeObjectURL = vi.fn();

      await act(async () => { await user.click(downloadButton); });
      expect(window.URL.createObjectURL).toHaveBeenCalled();
      expect(window.URL.revokeObjectURL).toHaveBeenCalled();

      // 6. Check for "Start New Conversion" button
      expect(screen.getByRole('button', { name: /start new conversion/i })).toBeInTheDocument();
    }, 15000); // Increase timeout for this long test

    test('handles conversion failure reported by API', async () => {
      const user = userEvent.setup({ delay: null });
      // Modify MSW handler for status to return FAILED
      // For this, we might need to enhance msw-handlers.ts or use server.use() here
      // For simplicity, let's assume msw-handlers.ts can be configured for this
      // (e.g., by setting a flag that pollJobStatus handler checks)
      // Or, more directly, override the specific handler for this test:
      const { server } = await import('../../test/setup'); // get the msw server instance
      const { http, HttpResponse } = await import('msw');
      const API_BASE_URL = 'http://localhost:8000/api/v1';

      server.use(
        http.get(`${API_BASE_URL}/convert/:id/status`, () => {
          return HttpResponse.json({
            conversionId: 'mock-fail-id',
            status: ConversionStatusEnum.FAILED,
            progress: 50, // Or whatever progress it failed at
            error: 'Mocked conversion failure: Something went wrong during conversion.',
            overallSuccessRate: 0,
            convertedMods: [],
            failedMods: [],
            smartAssumptionsApplied: [],
            detailedReport: { stage: 'Failed', progress: 50, logs: [], technicalDetails: {} },
          });
        })
      );

      render(<ConversionUpload />);
      const fileInput = screen.getByLabelText(/file upload/i);
      const mockFile = createMockFile('fail-mod.zip', 512, 'application/zip');
      await act(async () => { await user.upload(fileInput, mockFile); });
      await act(async () => { await user.click(screen.getByRole('button', { name: /convert to bedrock/i })); });

      // Wait for the failure status to be displayed
      await waitFor(() => {
        expect(screen.getByText(/Conversion process failed. Please review the error message below./i)).toBeInTheDocument();
      }, { timeout: 5000 }); // Timeout for initial conversion and first poll

      await waitFor(() => {
         expect(screen.getByText(/Mocked conversion failure: Something went wrong during conversion./i)).toBeInTheDocument();
      }, {timeout: 1000});


      // Check for "Start New Conversion" button
      expect(screen.getByRole('button', { name: /start new conversion/i })).toBeInTheDocument();
    });

    test('handles user cancelling the conversion', async () => {
      const user = userEvent.setup({ delay: null });
      render(<ConversionUpload />);

      const fileInput = screen.getByLabelText(/file upload/i);
      const mockFile = createMockFile('cancel-mod.zip', 1024, 'application/zip');
      await act(async () => { await user.upload(fileInput, mockFile); });
      await act(async () => { await user.click(screen.getByRole('button', { name: /convert to bedrock/i })); });

      // Wait for some initial progress to ensure cancel button is available and job is "in progress"
      await waitFor(() => {
        expect(screen.getByText(/upload complete, conversion pending.../i)).toBeInTheDocument();
      }, { timeout: 2000 });

      // Cancel button should be visible now
      const cancelButton = screen.getByRole('button', { name: /cancel conversion/i });
      expect(cancelButton).toBeInTheDocument();
      await act(async () => { await user.click(cancelButton); });

      // Check for cancelled status message
      // The msw-handler for DELETE /api/v1/convert/:id should result in CANCELLED state in component
      await waitFor(() => {
        expect(screen.getByText(/Conversion has been cancelled. You can start a new conversion./i)).toBeInTheDocument();
      }, { timeout: 2000 });

      // Check for "Start New Conversion" button
      expect(screen.getByRole('button', { name: /start new conversion/i })).toBeInTheDocument();
    });

  });
});