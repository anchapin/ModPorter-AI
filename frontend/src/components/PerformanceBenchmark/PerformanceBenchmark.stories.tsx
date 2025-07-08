import type { Meta, StoryObj } from '@storybook/react';
import { PerformanceBenchmark } from './PerformanceBenchmark';

const meta: Meta<typeof PerformanceBenchmark> = {
  title: 'Components/PerformanceBenchmark',
  component: PerformanceBenchmark,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof PerformanceBenchmark>;

export const Default: Story = {};

export const WithScenarios: Story = {
  parameters: {
    mockData: [
      {
        url: '/api/v1/performance/scenarios',
        method: 'GET',
        status: 200,
        response: {
          data: [
            {
              scenario_id: 'baseline_idle_001',
              scenario_name: 'Idle Performance',
              description: 'Measure performance impact when add-on is loaded but not actively used.',
              type: 'baseline',
              duration_seconds: 300,
              parameters: { load_level: 'none' },
              thresholds: { cpu: 5, memory: 50, fps: 30 }
            },
            {
              scenario_id: 'stress_entity_001',
              scenario_name: 'High Entity Count Stress Test',
              description: 'Test performance with a high number of custom entities.',
              type: 'stress_test',
              duration_seconds: 600,
              parameters: { entity_count: 1000, load_level: 'high' },
              thresholds: { cpu: 80, memory: 500, fps: 30 }
            }
          ]
        }
      }
    ]
  }
};

export const RunningBenchmark: Story = {
  parameters: {
    mockData: [
      {
        url: '/api/v1/performance/scenarios',
        method: 'GET',
        status: 200,
        response: {
          data: [
            {
              scenario_id: 'baseline_idle_001',
              scenario_name: 'Idle Performance',
              description: 'Measure performance impact when add-on is loaded but not actively used.',
              type: 'baseline',
              duration_seconds: 300,
              parameters: { load_level: 'none' },
              thresholds: { cpu: 5, memory: 50, fps: 30 }
            }
          ]
        }
      },
      {
        url: '/api/v1/performance/run',
        method: 'POST',
        status: 202,
        response: {
          data: {
            run_id: 'test-run-123',
            status: 'accepted',
            message: 'Benchmark run accepted'
          }
        }
      },
      {
        url: '/api/v1/performance/status/test-run-123',
        method: 'GET',
        status: 200,
        response: {
          data: {
            run_id: 'test-run-123',
            status: 'running',
            progress: 45,
            current_stage: 'running_load_tests'
          }
        }
      }
    ]
  }
};

export const CompletedBenchmark: Story = {
  parameters: {
    mockData: [
      {
        url: '/api/v1/performance/scenarios',
        method: 'GET',
        status: 200,
        response: {
          data: [
            {
              scenario_id: 'baseline_idle_001',
              scenario_name: 'Idle Performance',
              description: 'Measure performance impact when add-on is loaded but not actively used.',
              type: 'baseline',
              duration_seconds: 300,
              parameters: { load_level: 'none' },
              thresholds: { cpu: 5, memory: 50, fps: 30 }
            }
          ]
        }
      },
      {
        url: '/api/v1/performance/run',
        method: 'POST',
        status: 202,
        response: {
          data: {
            run_id: 'test-run-123',
            status: 'accepted',
            message: 'Benchmark run accepted'
          }
        }
      },
      {
        url: '/api/v1/performance/status/test-run-123',
        method: 'GET',
        status: 200,
        response: {
          data: {
            run_id: 'test-run-123',
            status: 'completed',
            progress: 100,
            current_stage: 'completed'
          }
        }
      },
      {
        url: '/api/v1/performance/report/test-run-123',
        method: 'GET',
        status: 200,
        response: {
          data: {
            run_id: 'test-run-123',
            benchmark: {
              overall_score: 85.5,
              cpu_score: 80.0,
              memory_score: 90.0,
              network_score: 88.0,
              scenario_name: 'Idle Performance',
              device_type: 'desktop'
            },
            metrics: [
              {
                metric_name: 'cpu_usage_percent',
                metric_category: 'cpu',
                java_value: 60.0,
                bedrock_value: 50.0,
                unit: 'percent',
                improvement_percentage: -16.67
              },
              {
                metric_name: 'memory_usage_mb',
                metric_category: 'memory',
                java_value: 200.0,
                bedrock_value: 180.0,
                unit: 'MB',
                improvement_percentage: -10.0
              }
            ],
            analysis: {
              identified_issues: ['No major performance issues detected'],
              optimization_suggestions: ['Performance appears within acceptable limits']
            },
            report_text: 'Performance Benchmark Report for Idle Performance\n================================================================\n\nScenario: baseline_idle_001\nDevice Type: desktop\nDuration: 300 seconds\n\nOverall Performance Score: 85.5/100\n- CPU Score: 80.0/100\n- Memory Score: 90.0/100\n- Network Score: 88.0/100\n\nKey Improvements:\n- CPU usage improved by 16.67% (Java: 60% → Bedrock: 50%)\n- Memory usage improved by 10.0% (Java: 200MB → Bedrock: 180MB)\n\nAnalysis: No major performance issues detected\nRecommendations: Performance appears within acceptable limits',
            optimization_suggestions: ['Performance appears within acceptable limits']
          }
        }
      }
    ]
  }
};

export const ErrorState: Story = {
  parameters: {
    mockData: [
      {
        url: '/api/v1/performance/scenarios',
        method: 'GET',
        status: 500,
        response: {
          detail: 'Failed to load scenarios'
        }
      }
    ]
  }
};