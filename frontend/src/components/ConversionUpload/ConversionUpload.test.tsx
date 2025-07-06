/**
 * Test-driven development for PRD Feature 1: One-Click Modpack Ingestion
 * Visual learner-friendly component testing (updated for Vitest)
 */

import React, { act } from 'react';
import { render, screen, waitFor } from '@testing-library/react';
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
      expect(screen.getByText(/\.jar files/i)).toBeInTheDocument();
      expect(screen.getByText(/\.zip modpack archives/i)).toBeInTheDocument();
    });

    test('shows URL input option as alternative', () => {
      render(<ConversionUpload />);
      
      // PRD Feature 1: URLs from major mod repositories
      expect(screen.getByPlaceholderText(/curseforge.*modrinth/i)).toBeInTheDocument();
      expect(screen.getByText(/or paste url/i)).toBeInTheDocument();
    });
  });

  describe('URL Validation', () => {
    test('validates URL types according to PRD specs', async () => {
      const user = userEvent.setup();
      render(<ConversionUpload />);
      
      const urlInput = screen.getByPlaceholderText(/curseforge.*modrinth/i);
      
      // Test invalid URL
      await act(async () => {
        await user.type(urlInput, 'https://invalid-site.com/mod');
      });
      
      await waitFor(() => {
        expect(screen.getByText(/Invalid URL.*CurseForge or Modrinth/)).toBeInTheDocument();
      });
    });

    test('accepts valid CurseForge URLs', async () => {
      const user = userEvent.setup();
      render(<ConversionUpload />);
      
      const urlInput = screen.getByPlaceholderText(/curseforge.*modrinth/i);
      
      await act(async () => {
        await user.type(urlInput, 'https://www.curseforge.com/minecraft/mc-mods/example-mod');
      });
      
      // Should not show error for valid URL
      expect(screen.queryByText(/Invalid URL/)).not.toBeInTheDocument();
    });
  });

  describe('Smart Assumptions UI', () => {
    test('displays smart assumptions toggle with explanation', () => {
      render(<ConversionUpload />);
      
      const toggle = screen.getByRole('checkbox', { name: /enable smart assumptions/i });
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

  describe('Basic Functionality', () => {
    test('convert button is disabled without file or URL', () => {
      render(<ConversionUpload />);
      
      const convertButton = screen.getByRole('button', { name: /convert/i });
      expect(convertButton).toBeDisabled();
    });

    test('shows dependencies toggle', () => {
      render(<ConversionUpload />);
      
      const dependenciesToggle = screen.getByRole('checkbox', { name: /include dependencies/i });
      expect(dependenciesToggle).toBeInTheDocument();
      expect(dependenciesToggle).toBeChecked(); // Default enabled
    });
  });
});