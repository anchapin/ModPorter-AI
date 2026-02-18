export interface ConversionHistoryItem {
  job_id: string;
  original_filename: string;
  status: 'completed' | 'failed' | 'processing' | 'queued';
  created_at: string;
  completed_at?: string;
  file_size?: number;
  error_message?: string;
  options?: {
    smartAssumptions: boolean;
    includeDependencies: boolean;
    modUrl?: string;
  };
}
