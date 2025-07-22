/**
 * Test-driven development for PRD Feature 1: One-Click Modpack Ingestion
 * Visual learner-friendly component testing (updated for Vitest)
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { ConversionUpload } from './ConversionUpload';
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
      expect(screen.getByRole('button', { name: /upload/i })).toBeInTheDocument();
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
    test('displays smart assumptions toggle with explanation', async () => {
      const user = userEvent.setup();
      render(<ConversionUpload />);
      const toggle = screen.getByRole('checkbox', { name: /enable smart assumptions/i });
      expect(toggle).toBeInTheDocument();
      expect(toggle).toBeChecked();
      
      // Click the info button to expand the explanation
      const infoButton = screen.getByLabelText(/learn more about smart assumptions/i);
      await user.click(infoButton);
      
      await waitFor(() => {
        expect(screen.getByText(/intelligent assumptions to convert incompatible features/i)).toBeInTheDocument();
      });
    });

    test('shows smart assumptions examples when info button clicked', async () => {
      const user = userEvent.setup();
      render(<ConversionUpload />);
      const infoButton = screen.getByRole('button', { name: /learn more about smart assumptions/i });
      await act(async () => { await user.click(infoButton); });
      expect(screen.getByText(/Custom dimensions.*Large structures/i)).toBeInTheDocument();
      expect(screen.getByText(/Complex machinery.*Simplified blocks/i)).toBeInTheDocument();
    });
  });

  describe('Basic Functionality', () => {
    test('convert button is disabled without file or URL', () => {
      render(<ConversionUpload />);
      const convertButton = screen.getByRole('button', { name: /upload/i });
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
    test('handles file upload and conversion initiation', async () => {
      const user = userEvent.setup({ delay: null });
      render(<ConversionUpload />);

      // 1. Upload a file
      const fileInput = screen.getByLabelText(/file upload/i);
      const mockFile = createMockFile('test-mod.zip', 1024, 'application/zip');
      await act(async () => { await user.upload(fileInput, mockFile); });

      expect(screen.getByText(mockFile.name)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /upload/i })).not.toBeDisabled();

      // 2. Click convert
      await act(async () => { await user.click(screen.getByRole('button', { name: /upload/i })); });

      // 3. Check that conversion starts (button changes to "Uploading...")
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /uploading.../i })).toBeInTheDocument();
      }, { timeout: 2000 });

      // 4. Verify cancel button appears
      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
    });

    test('shows cancel button during conversion', async () => {
      const user = userEvent.setup({ delay: null });
      render(<ConversionUpload />);

      const fileInput = screen.getByLabelText(/file upload/i);
      const mockFile = createMockFile('cancel-mod.zip', 1024, 'application/zip');
      await act(async () => { await user.upload(fileInput, mockFile); });
      await act(async () => { await user.click(screen.getByRole('button', { name: /upload/i })); });

      // Wait for conversion to start (button text changes)
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /uploading.../i })).toBeInTheDocument();
      }, { timeout: 2000 });

      // Cancel button should be visible now
      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      expect(cancelButton).toBeInTheDocument();
      expect(cancelButton).not.toBeDisabled();
    });

  });
});