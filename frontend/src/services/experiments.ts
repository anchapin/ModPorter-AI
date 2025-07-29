// services/experiments.ts
// Service functions for A/B testing experiments API

import { Experiment, ExperimentVariant, ExperimentResult } from '../types/experiment';

const API_BASE_URL = '/api/v1/experiments';

// Helper function for API requests
const apiRequest = async (url: string, options: { [key: string]: any } = {}) => {
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
  }

  return response.json();
};

// Experiment API functions

export const fetchExperiments = async (): Promise<Experiment[]> => {
  return apiRequest(`${API_BASE_URL}/experiments`);
};

export const fetchExperiment = async (id: string): Promise<Experiment> => {
  return apiRequest(`${API_BASE_URL}/experiments/${id}`);
};

export const createExperiment = async (experiment: Omit<Experiment, 'id' | 'created_at' | 'updated_at'>): Promise<Experiment> => {
  return apiRequest(`${API_BASE_URL}/experiments`, {
    method: 'POST',
    body: JSON.stringify(experiment),
  });
};

export const updateExperiment = async (id: string, experiment: Partial<Experiment>): Promise<Experiment> => {
  return apiRequest(`${API_BASE_URL}/experiments/${id}`, {
    method: 'PUT',
    body: JSON.stringify(experiment),
  });
};

export const deleteExperiment = async (id: string): Promise<void> => {
  await apiRequest(`${API_BASE_URL}/experiments/${id}`, {
    method: 'DELETE',
  });
};

// Experiment Variant API functions

export const fetchExperimentVariants = async (experimentId: string): Promise<ExperimentVariant[]> => {
  return apiRequest(`${API_BASE_URL}/experiments/${experimentId}/variants`);
};

export const fetchExperimentVariant = async (experimentId: string, variantId: string): Promise<ExperimentVariant> => {
  return apiRequest(`${API_BASE_URL}/experiments/${experimentId}/variants/${variantId}`);
};

export const createExperimentVariant = async (
  experimentId: string, 
  variant: Omit<ExperimentVariant, 'id' | 'experiment_id' | 'created_at' | 'updated_at'>
): Promise<ExperimentVariant> => {
  return apiRequest(`${API_BASE_URL}/experiments/${experimentId}/variants`, {
    method: 'POST',
    body: JSON.stringify(variant),
  });
};

export const updateExperimentVariant = async (
  experimentId: string, 
  variantId: string, 
  variant: Partial<ExperimentVariant>
): Promise<ExperimentVariant> => {
  return apiRequest(`${API_BASE_URL}/experiments/${experimentId}/variants/${variantId}`, {
    method: 'PUT',
    body: JSON.stringify(variant),
  });
};

export const deleteExperimentVariant = async (experimentId: string, variantId: string): Promise<void> => {
  await apiRequest(`${API_BASE_URL}/experiments/${experimentId}/variants/${variantId}`, {
    method: 'DELETE',
  });
};

// Experiment Result API functions

export const fetchExperimentResults = async (
  variantId?: string,
  sessionId?: string
): Promise<ExperimentResult[]> => {
  const params = new URLSearchParams();
  if (variantId) params.append('variant_id', variantId);
  if (sessionId) params.append('session_id', sessionId);
  
  const queryString = params.toString() ? `?${params.toString()}` : '';
  return apiRequest(`${API_BASE_URL}/experiment_results${queryString}`);
};

export const createExperimentResult = async (
  result: Omit<ExperimentResult, 'id' | 'created_at'>
): Promise<ExperimentResult> => {
  return apiRequest(`${API_BASE_URL}/experiment_results`, {
    method: 'POST',
    body: JSON.stringify(result),
  });
};