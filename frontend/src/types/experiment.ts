// types/experiment.ts
// Type definitions for A/B testing experiments

export interface Experiment {
  id: string;
  name: string;
  description: string | null;
  start_date: string | null;
  end_date: string | null;
  status: 'draft' | 'active' | 'paused' | 'completed';
  traffic_allocation: number;
  created_at: string;
  updated_at: string;
}

export interface ExperimentVariant {
  id: string;
  experiment_id: string;
  name: string;
  description: string | null;
  is_control: boolean;
  strategy_config: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

export interface ExperimentResult {
  id: string;
  variant_id: string;
  session_id: string;
  kpi_quality: number | null;
  kpi_speed: number | null;
  kpi_cost: number | null;
  user_feedback_score: number | null;
  user_feedback_text: string | null;
  metadata: Record<string, any> | null;
  created_at: string;
}