import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import App from '../App';

// Mock the API calls
jest.mock('axios', () => ({
  post: jest.fn(),
  get: jest.fn(),
}));

describe('App Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders ModPorter AI title', () => {
    render(<App />);
    const titleElement = screen.getByText(/ModPorter AI/i);
    expect(titleElement).toBeInTheDocument();
  });

  test('renders file upload area', () => {
    render(<App />);
    const uploadArea = screen.getByText(/upload/i);
    expect(uploadArea).toBeInTheDocument();
  });

  test('shows conversion options', () => {
    render(<App />);
    const optionsElement = screen.getByText(/conversion options/i);
    expect(optionsElement).toBeInTheDocument();
  });

  test('handles file upload', async () => {
    const user = userEvent.setup();
    render(<App />);
    
    const file = new File(['test content'], 'test-mod.jar', { type: 'application/java-archive' });
    const input = screen.getByLabelText(/upload mod file/i);
    
    await user.upload(input, file);
    
    expect(input).toHaveProperty('files', expect.arrayContaining([file]));
  });

  test('validates file type', async () => {
    const user = userEvent.setup();
    render(<App />);
    
    const invalidFile = new File(['test content'], 'test.txt', { type: 'text/plain' });
    const input = screen.getByLabelText(/upload mod file/i);
    
    await user.upload(input, invalidFile);
    
    await waitFor(() => {
      expect(screen.getByText(/invalid file type/i)).toBeInTheDocument();
    });
  });

  test('starts conversion process', async () => {
    const user = userEvent.setup();
    render(<App />);
    
    const file = new File(['test content'], 'test-mod.jar', { type: 'application/java-archive' });
    const input = screen.getByLabelText(/upload mod file/i);
    const convertButton = screen.getByRole('button', { name: /convert/i });
    
    await user.upload(input, file);
    await user.click(convertButton);
    
    await waitFor(() => {
      expect(screen.getByText(/conversion started/i)).toBeInTheDocument();
    });
  });

  test('displays conversion progress', async () => {
    render(<App />);
    
    // Mock conversion in progress
    const progressBar = screen.getByRole('progressbar');
    expect(progressBar).toBeInTheDocument();
  });

  test('shows conversion results', async () => {
    render(<App />);
    
    // Mock completed conversion
    const downloadButton = screen.getByRole('button', { name: /download/i });
    expect(downloadButton).toBeInTheDocument();
  });

  test('handles conversion errors', async () => {
    render(<App />);
    
    // Mock error state
    const errorMessage = screen.getByText(/conversion failed/i);
    expect(errorMessage).toBeInTheDocument();
  });
});