export interface ConversionHistoryItem {
  job_id: string;
  original_filename: string;
  status: 'completed' | 'failed' | 'processing' | 'queued' | 'partial';
  created_at: string;
  completed_at?: string;
  file_size?: number;
  error_message?: string;
  complexity_tier?: 'simple' | 'moderate' | 'complex' | 'unknown';
  features_converted?: string[];
  features_skipped?: string[];
  warnings?: string[];
  options?: {
    smartAssumptions: boolean;
    includeDependencies: boolean;
    modUrl?: string;
  };
}

export interface ConversionHistoryItemFromAPI {
  conversion_id: string;
  status: string;
  progress: number;
  message: string;
  created_at: string;
  updated_at?: string;
  original_filename?: string;
  error?: string;
  result_url?: string;
  complexity_tier?: 'simple' | 'moderate' | 'complex' | 'unknown';
  features_converted?: string[];
  features_skipped?: string[];
  warnings?: string[];
}
