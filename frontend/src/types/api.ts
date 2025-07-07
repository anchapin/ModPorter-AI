/**
 * TypeScript definitions matching PRD API specifications
 */

export interface ConversionRequest {
  file?: File;
  modUrl?: string;
  smartAssumptions: boolean;
  includeDependencies: boolean;
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