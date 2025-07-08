/**
 * TypeScript definitions matching PRD API specifications
 */

// --- Existing API types (mostly unchanged) ---

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
  result_url?: string | null; // This might be part of the SummaryReport now or still relevant here
  error?: string | null;
  created_at: string; // ISO date string
}

export interface ModConversionStatus {
  name: string;
  version: string;
  status: string; // e.g., "Converted", "Partially Converted", "Failed"
  warnings?: string[] | null;
  errors?: string[] | null;
}

export interface SmartAssumption {
  originalFeature: string;
  assumptionApplied: string;
  impact: 'low' | 'medium' | 'high';
  description: string;
  userExplanation?: string;
  visualExamples?: string[] | null;
}

export interface SummaryReport {
  overall_success_rate: number;
  total_features: number;
  converted_features: number;
  partially_converted_features: number;
  failed_features: number;
  assumptions_applied_count: number;
  processing_time_seconds: number;
  download_url: string | null;
  quick_statistics: Record<string, any>;
}

export interface FeatureConversionDetail {
  feature_name: string;
  status: string;
  compatibility_notes: string;
  visual_comparison_before?: string | null;
  visual_comparison_after?: string | null;
  impact_of_assumption?: string | null;
}

export interface FeatureAnalysis {
  per_feature_status: FeatureConversionDetail[];
  compatibility_mapping_summary: string;
  visual_comparisons_overview?: string | null;
  impact_assessment_summary: string;
}

export interface AssumptionDetail { // Detailed version for AssumptionsReport
  assumption_id: string;
  feature_affected: string;
  description: string;
  reasoning: string;
  impact_level: string; // "Low", "Medium", "High"
  user_explanation: string;
  technical_notes?: string | null;
}

export interface AssumptionsReport {
  assumptions: AssumptionDetail[];
}

export interface LogEntry {
  timestamp: string; // ISO date string
  level: string; // "INFO", "WARNING", "ERROR"
  message: string;
  details?: Record<string, any> | null;
}

export interface DeveloperLog {
  code_translation_details: LogEntry[];
  api_mapping_issues: LogEntry[];
  file_processing_log: LogEntry[];
  performance_metrics: Record<string, any>; // e.g., { "total_time_seconds": 60.5, "memory_peak_mb": 256 }
  error_summary: Array<Record<string, any>>; // { "error_message": "...", "stack_trace": "..." }
}

export interface InteractiveReport { // This is the main model for the detailed report page
  job_id: string;
  report_generation_date: string; // ISO date string
  summary: SummaryReport;
  converted_mods: ModConversionStatus[];
  failed_mods: ModConversionStatus[];
  feature_analysis?: FeatureAnalysis | null;
  smart_assumptions_report?: AssumptionsReport | null; // Uses AssumptionDetail
  developer_log?: DeveloperLog | null;
}


// --- Potentially legacy or alternative types (review if still needed) ---
// The following interfaces seem to be part of an older/different API design.
// Leaving them here for now, but they are not directly used by
// ConversionUpload, ConversionProgress for job status/initiation.
// Or by the new InteractiveReport structure.

export interface ConvertedMod { // Might be replaced by ModConversionStatus or be part of a different view
  name: string;
  version: string;
  status: 'success' | 'partial' | 'failed'; // ModConversionStatus has more generic string status
  features: ModFeature[]; // ModFeature is also defined below
  warnings: string[]; // ModConversionStatus also has warnings
}

export interface FailedMod { // Might be replaced by ModConversionStatus
  name: string;
  reason: string; // ModConversionStatus uses 'errors' field
  suggestions: string[];
}

export interface ModFeature { // Used by ConvertedMod above
  name: string;
  type: 'block' | 'item' | 'entity' | 'dimension' | 'gui' | 'logic';
  converted: boolean;
  changes?: string;
}

export interface DetailedReport { // This is likely superseded by InteractiveReport
  stage: string;
  progress: number;
  logs: string[];
  technicalDetails: any;
}

// Status enum for frontend type checking
export const ConversionStatusEnum = {
  PENDING: 'queued',
  UPLOADING: 'uploading',
  IN_PROGRESS: 'preprocessing',
  ANALYZING: 'analyzing',
  CONVERTING: 'ai_conversion',
  PACKAGING: 'postprocessing',
  COMPLETED: 'completed',
  FAILED: 'failed',
  CANCELLED: 'cancelled'
} as const;

export type ConversionStatusType = typeof ConversionStatusEnum[keyof typeof ConversionStatusEnum];

// Extended interfaces for rich reporting (maintaining backward compatibility)
export interface ExtendedConversionResponse extends ConversionResponse {
  overallSuccessRate?: number;
  convertedMods?: ConvertedMod[];
  failedMods?: FailedMod[];
  smartAssumptionsApplied?: SmartAssumption[];
  downloadUrl?: string;
  detailedReport?: DetailedReport;
}