/**
 * API client for ModPorter-AI web interface
 * Handles file uploads, job tracking, and result retrieval
 */

import { ConversionStatus, UploadResponse } from '../types/api';

// Use relative URL for production (proxied by nginx) or localhost for development
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL
  ? import.meta.env.VITE_API_BASE_URL + '/api/v1'
  : import.meta.env.VITE_API_URL
    ? import.meta.env.VITE_API_URL.replace(/\/api\/v1$/, '') + '/api/v1'
    : '/api/v1';

// Configuration
const MAX_FILE_SIZE = 100 * 1024 * 1024; // 100MB
const ALLOWED_EXTENSIONS = ['.jar', '.zip', '.mcaddon'];
const ALLOWED_CONTENT_TYPES = [
  'application/java-archive',
  'application/zip',
  'application/x-java-archive',
];

// Types
export interface UploadOptions {
  onProgress?: (progress: number) => void;
}

export interface JobCreateRequest {
  file_path: string;
  original_filename: string;
  options?: JobOptions;
}

export interface JobOptions {
  conversion_mode?: 'simple' | 'standard' | 'complex';
  target_version?: string;
  output_format?: 'mcaddon' | 'zip';
  webhook_url?: string;
}

export interface JobResponse {
  job_id: string;
  user_id: string;
  original_filename: string;
  status: string;
  progress: number;
  current_step: string;
  result_url?: string | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
  completed_at?: string | null;
}

export interface ConversionResult {
  job_id: string;
  status: 'completed' | 'failed' | 'cancelled';
  progress: number;
  result_url?: string;
  download_url?: string;
  error_message?: string;
  summary?: {
    overall_success_rate: number;
    total_features: number;
    converted_features: number;
    partially_converted_features: number;
    failed_features: number;
    processing_time_seconds: number;
  };
}

// API Client Class
class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  /**
   * Validate file before upload
   */
  validateFile(file: File): { valid: boolean; error?: string } {
    // Check file extension
    const ext = file.name.toLowerCase().slice(file.name.lastIndexOf('.'));
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      return {
        valid: false,
        error: `Invalid file type. Allowed: ${ALLOWED_EXTENSIONS.join(', ')}`,
      };
    }

    // Check file size
    if (file.size > MAX_FILE_SIZE) {
      return {
        valid: false,
        error: `File size exceeds the limit of ${MAX_FILE_SIZE / (1024 * 1024)}MB`,
      };
    }

    // Check content type
    if (
      file.type &&
      !ALLOWED_CONTENT_TYPES.includes(file.type) &&
      file.type !== 'application/octet-stream'
    ) {
      return {
        valid: false,
        error: `Invalid content type: ${file.type}`,
      };
    }

    return { valid: true };
  }

  /**
   * Upload a file with progress tracking
   */
  async uploadFile(
    file: File,
    options?: UploadOptions
  ): Promise<UploadResponse> {
    const validation = this.validateFile(file);
    if (!validation.valid) {
      throw new Error(validation.error);
    }

    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      const formData = new FormData();
      formData.append('file', file);

      // Progress handler
      if (options?.onProgress) {
        xhr.upload.addEventListener('progress', (event) => {
          if (event.lengthComputable) {
            const progress = Math.round((event.loaded / event.total) * 100);
            options.onProgress(progress);
          }
        });
      }

      // Load handler
      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const response = JSON.parse(xhr.responseText);
            resolve(response);
          } catch {
            reject(new Error('Invalid response from server'));
          }
        } else {
          try {
            const errorData = JSON.parse(xhr.responseText);
            reject(new Error(errorData.detail || 'File upload failed'));
          } catch {
            reject(new Error('File upload failed'));
          }
        }
      });

      // Error handler
      xhr.addEventListener('error', () => {
        reject(new Error('Network error during upload'));
      });

      // Abort handler
      xhr.addEventListener('abort', () => {
        reject(new Error('Upload cancelled'));
      });

      xhr.open('POST', `${this.baseUrl}/upload`);
      xhr.send(formData);
    });
  }

  /**
   * Create a conversion job
   */
  async createJob(request: JobCreateRequest): Promise<JobResponse> {
    const response = await fetch(`${this.baseUrl}/jobs`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const errorData = await response
        .json()
        .catch(() => ({ detail: 'Failed to create job' }));
      throw new Error(errorData.detail || 'Failed to create job');
    }

    return response.json();
  }

  /**
   * Get job status
   */
  async getJobStatus(jobId: string): Promise<JobResponse> {
    const response = await fetch(`${this.baseUrl}/jobs/${jobId}`);

    if (!response.ok) {
      const errorData = await response
        .json()
        .catch(() => ({ detail: 'Failed to get job status' }));
      throw new Error(errorData.detail || 'Failed to get job status');
    }

    return response.json();
  }

  /**
   * Poll for job completion
   */
  async waitForCompletion(
    jobId: string,
    onProgress: (status: JobResponse) => void,
    pollingInterval: number = 2000,
    maxAttempts: number = 300
  ): Promise<JobResponse> {
    let attempts = 0;

    return new Promise((resolve, reject) => {
      const poll = async () => {
        try {
          const status = await this.getJobStatus(jobId);
          onProgress(status);

          if (
            status.status === 'completed' ||
            status.status === 'failed' ||
            status.status === 'cancelled'
          ) {
            resolve(status);
            return;
          }

          attempts++;
          if (attempts >= maxAttempts) {
            reject(new Error('Job polling timeout'));
            return;
          }

          setTimeout(poll, pollingInterval);
        } catch (error) {
          reject(error);
        }
      };

      poll();
    });
  }

  /**
   * Get conversion results
   */
  async getResults(jobId: string): Promise<ConversionResult> {
    const response = await fetch(`${this.baseUrl}/jobs/${jobId}/results`);

    if (!response.ok) {
      const errorData = await response
        .json()
        .catch(() => ({ detail: 'Failed to get results' }));
      throw new Error(errorData.detail || 'Failed to get results');
    }

    return response.json();
  }

  /**
   * Cancel a job
   */
  async cancelJob(jobId: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/jobs/${jobId}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      const errorData = await response
        .json()
        .catch(() => ({ detail: 'Failed to cancel job' }));
      throw new Error(errorData.detail || 'Failed to cancel job');
    }
  }

  /**
   * List user jobs
   */
  async listJobs(
    limit: number = 10,
    offset: number = 0
  ): Promise<{ jobs: JobResponse[]; total: number }> {
    const response = await fetch(
      `${this.baseUrl}/jobs?limit=${limit}&offset=${offset}`
    );

    if (!response.ok) {
      const errorData = await response
        .json()
        .catch(() => ({ detail: 'Failed to list jobs' }));
      throw new Error(errorData.detail || 'Failed to list jobs');
    }

    return response.json();
  }

  /**
   * Download result file
   */
  downloadResult(url: string, filename: string): void {
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  /**
   * Get download URL for a completed job
   */
  getDownloadUrl(jobId: string): string {
    return `${this.baseUrl}/jobs/${jobId}/download`;
  }
}

// Export singleton instance
export const apiClient = new ApiClient();

// Export class for testing
export { ApiClient };
