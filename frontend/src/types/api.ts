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

// This interface will match the backend's ConversionStatus model
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

// Status enum for frontend type checking
export enum ConversionStatusEnum {
  PENDING = 'queued',
  UPLOADING = 'uploading',
  IN_PROGRESS = 'preprocessing',
  ANALYZING = 'analyzing',
  CONVERTING = 'ai_conversion',
  PACKAGING = 'postprocessing',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled',
}

// Extended interfaces for rich reporting (maintaining backward compatibility)
export interface ExtendedConversionResponse extends ConversionResponse {
  overallSuccessRate?: number;
  convertedMods?: ConvertedMod[];
  failedMods?: FailedMod[];
  smartAssumptionsApplied?: SmartAssumption[];
  downloadUrl?: string;
  detailedReport?: DetailedReport;
}
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

export interface DetailedReport {
  stage: string;
  progress: number;
  logs: string[];
  technicalDetails: any;
}