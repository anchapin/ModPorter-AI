/**
 * API service for communicating with ModPorter AI backend
 * Implements PRD API specifications
 */

import { ConversionRequest, ConversionResponse } from '../types/api';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
    this.name = 'ApiError';
  }
}

export const convertMod = async (request: ConversionRequest): Promise<ConversionResponse> => {
  const formData = new FormData();
  
  if (request.file) {
    formData.append('mod_file', request.file);
  }
  
  // Add other request data
  formData.append('smart_assumptions', request.smartAssumptions.toString());
  formData.append('include_dependencies', request.includeDependencies.toString());
  
  if (request.modUrl) {
    formData.append('mod_url', request.modUrl);
  }

  const response = await fetch(`${API_BASE_URL}/convert`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new ApiError(errorData.detail || 'Conversion failed', response.status);
  }

  return response.json();
};

export const pollJobStatus = async (conversionId: string): Promise<ConversionResponse> => {
  const response = await fetch(`${API_BASE_URL}/convert/${conversionId}/status`);
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new ApiError(errorData.detail || 'Failed to get status', response.status);
  }

  return response.json();
};

export const downloadResult = async (conversionId: string): Promise<Blob> => {
  const response = await fetch(`${API_BASE_URL}/convert/${conversionId}/download`);
  
  if (!response.ok) {
    throw new ApiError('Download failed', response.status);
  }

  return response.blob();
};

export const cancelJob = async (conversionId: string): Promise<void> => {
  const response = await fetch(`${API_BASE_URL}/convert/${conversionId}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new ApiError(errorData.detail || 'Failed to cancel job', response.status);
  }
};