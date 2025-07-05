/**
 * Test-driven development for PRD Feature 1: One-Click Modpack Ingestion
 * Visual learner-friendly component testing (updated for Vitest)
 */

import React, { act } from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { vi } from 'vitest';
import { ConversionUpload } from './ConversionUpload';

// Mock the API service
vi.mock('../../services/api', () => ({
  convertMod: vi.fn(),
  getConversionStatus: vi.fn(),
}));

describe('ConversionUpload Component - PRD Feature 1', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Visual Interface Requirements', () => {
    test('renders upload interface with clear visual cues', () => {
      render(<ConversionUpload />);
      
      // PRD Feature 1: "drag and drop my CurseForge modpack zip file"
      expect(screen.getByText(/drag.*drop/i)).toBeInTheDocument();
      expect(screen.getByText(/CurseForge.*Modrinth/)).toBeInTheDocument();
      
      // Visual elements for user guidance
      expect(screen.getByRole('button', { name: /convert/i })).toBeInTheDocument();
      expect(screen.getByLabelText(/file upload/i)).toBeInTheDocument();
    });

    test('displays supported file types clearly', () => {
      render(<ConversionUpload />);
      
      // PRD Feature 1 Acceptance Criteria: .jar files, .zip modpack archives
      expect(screen.getByText(/\.jar/i)).toBeInTheDocument();
      expect(screen.getByText(/\.zip/i)).toBeInTheDocument();
      expect(screen.getByText(/modpack archive/i)).toBeInTheDocument();
    });

    test('shows URL input option as alternative', () => {
      render(<ConversionUpload />);
      
      // PRD Feature 1: URLs from major mod repositories
      expect(screen.getByPlaceholderText(/curseforge.*modrinth/i)).toBeInTheDocument();
      expect(screen.getByText(/or paste url/i)).toBeInTheDocument();
    });
  });

  describe('File Upload Functionality', () => {
    test('handles file selection and shows preview', async () => {
      const user = userEvent.setup();
      render(<ConversionUpload />);
      
      const file = new File(['mock mod content'], 'test-mod.jar', {
        type: 'application/java-archive'
      });
      
      const fileInput = screen.getByLabelText(/file upload/i);
      
      await act(async () => {
        await user.upload(fileInput, file);
      });
      
      // Visual feedback for file selection
      expect(screen.getByText('test-mod.jar')).toBeInTheDocument();
      expect(screen.getByText(/ready to convert/i)).toBeInTheDocument();
    });

    test('validates file types according to PRD specs', async () => {
      render(<ConversionUpload />);
      
      // Test invalid file type via drag and drop which bypasses accept filter
      const dropZone = screen.getByText(/drag.*drop/i).closest('div');
      const invalidFile = new File(['content'], 'test.txt', { type: 'text/plain' });
      
      await act(async () => {
        const mockDataTransfer = {
          files: [invalidFile],
          items: [],
          types: []
        };
        fireEvent.drop(dropZone!, {
          dataTransfer: mockDataTransfer
        });
      });
      
      await waitFor(() => {
        expect(screen.getByText(/Unsupported file type.*\.jar or \.zip files only/)).toBeInTheDocument();
      });
    });

    test('handles drag and drop functionality', async () => {
      render(<ConversionUpload />);
      
      const dropZone = screen.getByText(/drag.*drop/i).closest('div');
      const file = new File(['content'], 'modpack.zip', { type: 'application/zip' });
      
      await act(async () => {
        fireEvent.dragEnter(dropZone!);
      });
      expect(dropZone).toHaveClass('drag-active'); // Visual feedback
      
      await act(async () => {
        const mockDataTransfer = {
          files: [file],
          items: [],
          types: []
        };
        fireEvent.drop(dropZone!, {
          dataTransfer: mockDataTransfer
        });
      });
      
      await waitFor(() => {
        expect(screen.getByText('modpack.zip')).toBeInTheDocument();
      });
    });
  });

  describe('Conversion Initiation', () => {
    test('initiates conversion with file upload', async () => {
      const { convertMod } = await import('../../services/api');
      const mockConvert = vi.mocked(convertMod);
      mockConvert.mockResolvedValue({ 
        conversionId: 'test-123',
        status: 'processing',
        overallSuccessRate: 0,
        convertedMods: [],
        failedMods: [],
        smartAssumptionsApplied: [],
        detailedReport: {}
      });
      
      const user = userEvent.setup();
      render(<ConversionUpload />);
      
      // Upload file
      const file = new File(['content'], 'test.jar', { type: 'application/java-archive' });
      const fileInput = screen.getByLabelText(/file upload/i);
      
      await act(async () => {
        await user.upload(fileInput, file);
      });
      
      // Click convert
      const convertButton = screen.getByRole('button', { name: /convert/i });
      await act(async () => {
        await user.click(convertButton);
      });
      
      expect(mockConvert).toHaveBeenCalledWith({
        file: expect.any(File),
        smartAssumptions: true,
        includeDependencies: true
      });
    });

    test('shows loading state during conversion', async () => {
      const { convertMod } = await import('../../services/api');
      const mockConvert = vi.mocked(convertMod);
      mockConvert.mockImplementation(() => new Promise(resolve => 
        setTimeout(() => resolve({
          conversionId: 'test',
          status: 'processing',
          overallSuccessRate: 0,
          convertedMods: [],
          failedMods: [],
          smartAssumptionsApplied: [],
          detailedReport: {}
        }), 1000)
      ));
      
      const user = userEvent.setup();
      render(<ConversionUpload />);
      
      // Setup and trigger conversion
      const file = new File(['content'], 'test.jar', { type: 'application/java-archive' });
      const fileInput = screen.getByLabelText(/file upload/i);
      
      await act(async () => {
        await user.upload(fileInput, file);
      });
      
      const convertButton = screen.getByRole('button', { name: /convert/i });
      await act(async () => {
        await user.click(convertButton);
      });
      
      // Visual loading indicators
      expect(screen.getByText(/converting/i)).toBeInTheDocument();
      expect(screen.getByRole('progressbar')).toBeInTheDocument();
      expect(convertButton).toBeDisabled();
    });
  });

  describe('Smart Assumptions UI', () => {
    test('displays smart assumptions toggle with explanation', () => {
      render(<ConversionUpload />);
      
      const toggle = screen.getByLabelText(/smart assumptions/i);
      expect(toggle).toBeInTheDocument();
      expect(toggle).toBeChecked(); // Default enabled per PRD
      
      // Explanatory text for visual learners
      expect(screen.getByText(/ai will make intelligent compromises/i)).toBeInTheDocument();
    });

    test('shows smart assumptions examples when enabled', async () => {
      const user = userEvent.setup();
      render(<ConversionUpload />);
      
      const infoButton = screen.getByRole('button', { name: /learn more/i });
      await act(async () => {
        await user.click(infoButton);
      });
      
      // PRD Table of Smart Assumptions examples
      expect(screen.getByText(/custom dimensions/i)).toBeInTheDocument();
      expect(screen.getByText(/complex machinery/i)).toBeInTheDocument();
      expect(screen.getByText(/custom gui/i)).toBeInTheDocument();
    });
  });
});