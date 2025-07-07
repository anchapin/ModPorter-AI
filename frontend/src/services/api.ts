/**
 * API service for communicating with ModPorter AI backend
 * Implements PRD API specifications
 */

import { ConversionRequest, ConversionResponse, ConversionStatus, UploadResponse, InitiateConversionParams } from '../types/api'; // Added UploadResponse, InitiateConversionParams

// Use relative URL for production (proxied by nginx) or localhost for development
const API_BASE_URL = process.env.VITE_API_URL || 
  (process.env.NODE_ENV === 'production' ? '/api/v1' : 'http://localhost:8080/api/v1');

class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
    this.name = 'ApiError';
  }
}

export const uploadFileActual = async (file: File): Promise<UploadResponse> => {
  const formData = new FormData();
  formData.append('file', file); // Match backend parameter name 'file'

  const response = await fetch(`${API_BASE_URL}/upload`, { // Corrected endpoint
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Upload failed with unknown error' }));
    throw new ApiError(errorData.detail || 'File upload failed', response.status);
  }

  return response.json();
};

export const convertMod = async (params: InitiateConversionParams): Promise<ConversionResponse> => {
  if (!params.file) {
    // As per instructions, conversion via modUrl alone without a file upload step is not currently supported
    // by the backend's /api/v1/convert endpoint (which is start_conversion).
    throw new Error("File is required for conversion.");
  }

  // Step 1: Upload the file
  const uploadResponse = await uploadFileActual(params.file);

  // Step 2: Construct the ConversionRequest payload for the backend
  const backendRequestPayload: ConversionRequest = {
    file_id: uploadResponse.file_id,
    original_filename: uploadResponse.original_filename,
    target_version: params.target_version, // Pass through target_version
    options: {
      smartAssumptions: params.smartAssumptions,
      includeDependencies: params.includeDependencies,
      // modUrl can be part of options if needed by backend logic tied to a file_id
      ...(params.modUrl && { modUrl: params.modUrl }),
    },
  };

  const response = await fetch(`${API_BASE_URL}/convert`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(backendRequestPayload),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new ApiError(errorData.detail || 'Conversion failed', response.status);
  }

  return response.json();
};

export const getConversionStatus = async (conversionId: string): Promise<ConversionStatus> => { // Return type changed
  // Endpoint corrected: /api/convert/{job_id} instead of /api/convert/{job_id}/status
  // This path /api/v1/convert/{job_id} is handled by get_conversion on backend, which is fine.
  const response = await fetch(`${API_BASE_URL}/convert/${conversionId}`);
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new ApiError(errorData.detail || 'Failed to get status', response.status);
  }

  return response.json();
};

export const downloadConvertedMod = async (conversionId: string): Promise<Blob> => {
  const response = await fetch(`${API_BASE_URL}/convert/${conversionId}/download`);
  
  if (!response.ok) {
    throw new ApiError('Download failed', response.status);
  }

  return response.blob();
};