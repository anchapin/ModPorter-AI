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
  conversionId: string;
  status: ConversionStatus;
  progress?: number; // Added progress
  error?: string; // Added error message for failed status
  overallSuccessRate: number;
  convertedMods: ConvertedMod[];
  failedMods: FailedMod[];
  smartAssumptionsApplied: SmartAssumption[];
  downloadUrl?: string;
  detailedReport: DetailedReport;
}

export enum ConversionStatus {
  PENDING = 'PENDING',
  UPLOADING = 'UPLOADING', // If you have a distinct upload phase before backend processing
  IN_PROGRESS = 'IN_PROGRESS', // General "processing" state from backend
  ANALYZING = 'ANALYZING',
  CONVERTING = 'CONVERTING',
  PACKAGING = 'PACKAGING',
  COMPLETED = 'COMPLETED',
  FAILED = 'FAILED',
  CANCELLED = 'CANCELLED', // Frontend specific status
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