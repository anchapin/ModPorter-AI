/**
 * TypeScript definitions matching PRD API specifications
 */

export interface ConversionRequest {
  file_id: string; // Made mandatory for the actual call to /api/v1/convert
  original_filename: string; // Made mandatory for the actual call to /api/v1/convert
  target_version?: string;
  options?: {
    smartAssumptions: boolean;
    includeDependencies: boolean;
    modUrl?: string; // modUrl can be part of options
    // any other relevant options
  };
}

export interface UploadResponse {
  file_id: string;
  original_filename: string;
  saved_filename: string;
  size: number;
  content_type?: string;
  message: string;
  filename: string; // This seems to be the same as original_filename
}

export interface InitiateConversionParams {
  file?: File; // User provides a file
  modUrl?: string; // Or a URL
  smartAssumptions: boolean;
  includeDependencies: boolean;
  target_version?: string; // Added
}

export interface ConversionResponse {
  job_id: string; // Matches backend
  status: string; // General status like 'queued', 'processing', etc.
  message: string;
  estimated_time?: number; // Initial estimated time for completion
}

// This new interface will match the backend's ConversionStatus model
export interface ConversionStatus {
  job_id: string;
  status: string; // e.g., "queued", "preprocessing", "ai_conversion", "postprocessing", "completed", "failed", "cancelled"
  progress: number; // Percentage 0-100
  message: string;
  stage?: string | null; // Descriptive stage name
  estimated_time_remaining?: number | null; // In seconds
  result_url?: string | null;
  error?: string | null;
  created_at: string; // ISO date string
}

// The following interfaces seem to be part of an older/different API design.
// Leaving them here for now, but they are not directly used by
// ConversionUpload, ConversionProgress for job status/initiation.
export interface ConvertedMod {
  name: string;
  version: string;
  status: 'success' | 'partial' | 'failed';
  features: ModFeature[];
  warnings: string[];
}

export interface FailedMod {
  name: string;
  reason: string;
  suggestions: string[];
}

export interface SmartAssumption {
  originalFeature: string;
  assumptionApplied: string;
  impact: 'low' | 'medium' | 'high';
  description: string;
}

export interface ModFeature {
  name: string;
  type: 'block' | 'item' | 'entity' | 'dimension' | 'gui' | 'logic';
  converted: boolean;
  changes?: string;
}

export interface DetailedReport { // This might be for a more detailed report page, not the primary status.
  stage: string;
  progress: number;
  logs: string[];
  technicalDetails: any;
}