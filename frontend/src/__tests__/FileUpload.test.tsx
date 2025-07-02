import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

// Mock FileUpload component (to be created)
const FileUpload = ({ onFileSelect, acceptedTypes, maxSize }: {
  onFileSelect: (file: File) => void;
  acceptedTypes: string[];
  maxSize: number;
}) => {
  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      onFileSelect(file);
    }
  };

  return (
    <div>
      <input
        type="file"
        onChange={handleFileChange}
        accept={acceptedTypes.join(',')}
        aria-label="Upload mod file"
      />
      <p>Max file size: {maxSize}MB</p>
      <p>Accepted types: {acceptedTypes.join(', ')}</p>
    </div>
  );
};

describe('FileUpload Component', () => {
  const mockOnFileSelect = jest.fn();
  const defaultProps = {
    onFileSelect: mockOnFileSelect,
    acceptedTypes: ['.jar', '.zip', '.mcaddon'],
    maxSize: 100,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders file input', () => {
    render(<FileUpload {...defaultProps} />);
    const input = screen.getByLabelText(/upload mod file/i);
    expect(input).toBeInTheDocument();
  });

  test('displays accepted file types', () => {
    render(<FileUpload {...defaultProps} />);
    const typesText = screen.getByText(/accepted types.*\.jar.*\.zip.*\.mcaddon/i);
    expect(typesText).toBeInTheDocument();
  });

  test('displays max file size', () => {
    render(<FileUpload {...defaultProps} />);
    const sizeText = screen.getByText(/max file size.*100mb/i);
    expect(sizeText).toBeInTheDocument();
  });

  test('calls onFileSelect when file is selected', async () => {
    const user = userEvent.setup();
    render(<FileUpload {...defaultProps} />);
    
    const file = new File(['test content'], 'test-mod.jar', { type: 'application/java-archive' });
    const input = screen.getByLabelText(/upload mod file/i);
    
    await user.upload(input, file);
    
    expect(mockOnFileSelect).toHaveBeenCalledWith(file);
  });

  test('handles multiple file selection (should only select first)', async () => {
    const user = userEvent.setup();
    render(<FileUpload {...defaultProps} />);
    
    const file1 = new File(['test content 1'], 'test-mod1.jar', { type: 'application/java-archive' });
    const file2 = new File(['test content 2'], 'test-mod2.jar', { type: 'application/java-archive' });
    const input = screen.getByLabelText(/upload mod file/i);
    
    await user.upload(input, [file1, file2]);
    
    expect(mockOnFileSelect).toHaveBeenCalledWith(file1);
    expect(mockOnFileSelect).toHaveBeenCalledTimes(1);
  });

  test('sets correct accept attribute', () => {
    render(<FileUpload {...defaultProps} />);
    const input = screen.getByLabelText(/upload mod file/i);
    expect(input).toHaveAttribute('accept', '.jar,.zip,.mcaddon');
  });
});