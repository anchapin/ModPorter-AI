import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Progress } from '../ui/progress';
// Simple icon replacements for lucide-react icons
const PlayCircle = () => <span>▶</span>;
const Download = () => <span>⬇</span>;
const RefreshCw = () => <span>↻</span>;

interface TestScenario {
  scenario: string;
  steps: Array<Record<string, any>>;
  expected_outcome?: string;
  timeout_ms?: number;
  fail_fast?: boolean;
}

interface BehavioralTestProps {
  conversionId: string;
  onTestComplete?: (results: any) => void;
}

interface TestResult {
  test_id: string;
  status: string;
  total_scenarios: number;
  passed_scenarios: number;
  failed_scenarios: number;
  behavioral_score?: number;
  execution_time_ms: number;
  created_at: string;
}

export const BehavioralTest: React.FC<BehavioralTestProps> = ({
  conversionId,
  onTestComplete
}) => {
  const [isRunning, setIsRunning] = useState(false);
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const defaultScenarios: TestScenario[] = [
    {
      scenario: "Block Interaction Test",
      steps: [
        { action: "place_block", position: [0, 60, 0], block_type: "custom_block" },
        { action: "right_click", target: "custom_block" },
        { action: "verify_state", key: "gui_opened_for_custom_block_A", expected: "main_menu_mock_value" }
      ],
      expected_outcome: "Block GUI opens correctly"
    },
    {
      scenario: "Entity Behavior Test",
      steps: [
        { action: "spawn_entity", type: "custom_mob", position: [10, 60, 10] },
        { action: "player_approach", target: "custom_mob", distance: 5 },
        { action: "verify_behavior", expected_behavior_id: "hostile_reaction" }
      ],
      expected_outcome: "Entity attacks player when approached"
    },
    {
      scenario: "Item Usage Test",
      steps: [
        { action: "give_item", item_type: "custom_tool", quantity: 1 },
        { action: "use_item", target: "custom_tool" },
        { action: "verify_state", key: "item_effect_active", expected: true }
      ],
      expected_outcome: "Custom item effect activates"
    }
  ];

  const startBehavioralTest = async () => {
    setIsRunning(true);
    setError(null);
    setProgress(0);

    try {
      const testRequest = {
        conversion_id: conversionId,
        test_scenarios: defaultScenarios,
        test_environment: "bedrock_test",
        minecraft_version: "1.20.0",
        test_config: {
          report_format: "json",
          timeout_per_scenario: 30000
        }
      };

      const response = await fetch('/api/behavioral-testing/tests', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(testRequest),
      });

      if (!response.ok) {
        throw new Error(`Test creation failed: ${response.statusText}`);
      }

      const result = await response.json();
      setTestResult(result);

      // Poll for test completion
      await pollTestProgress(result.test_id);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error occurred');
      setIsRunning(false);
    }
  };

  const pollTestProgress = async (testId: string) => {
    const pollInterval = 2000; // 2 seconds
    const maxPollTime = 300000; // 5 minutes
    const startTime = Date.now();

    const poll = async (): Promise<void> => {
      try {
        if (Date.now() - startTime > maxPollTime) {
          throw new Error('Test timeout - taking longer than expected');
        }

        const response = await fetch(`/api/behavioral-testing/tests/${testId}`);
        if (!response.ok) {
          throw new Error(`Failed to get test status: ${response.statusText}`);
        }

        const result = await response.json();
        setTestResult(result);

        // Update progress based on completion
        if (result.status === 'RUNNING') {
          const elapsed = Date.now() - startTime;
          const estimatedProgress = Math.min((elapsed / maxPollTime) * 100, 90);
          setProgress(estimatedProgress);
          
          setTimeout(poll, pollInterval);
        } else {
          setProgress(100);
          setIsRunning(false);
          
          if (onTestComplete) {
            onTestComplete(result);
          }
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Polling error');
        setIsRunning(false);
      }
    };

    await poll();
  };

  const downloadReport = async () => {
    if (!testResult) return;

    try {
      const response = await fetch(`/api/behavioral-testing/tests/${testResult.test_id}/report?format=json`);
      if (!response.ok) {
        throw new Error('Failed to download report');
      }

      const reportData = await response.json();
      const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      
      const a = document.createElement('a');
      a.href = url;
      a.download = `behavioral_test_report_${testResult.test_id}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to download report');
    }
  };

  const getStatusBadgeVariant = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
      case 'success':
        return 'default';
      case 'running':
        return 'secondary';
      case 'failed':
      case 'error':
        return 'destructive';
      default:
        return 'outline';
    }
  };

  const getBehavioralScoreColor = (score?: number) => {
    if (!score) return 'text-gray-500';
    if (score >= 0.9) return 'text-green-600';
    if (score >= 0.7) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <PlayCircle className="h-5 w-5" />
            Behavioral Testing
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Button
              onClick={startBehavioralTest}
              disabled={isRunning}
              className="flex items-center gap-2"
            >
              {isRunning ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  Running Tests...
                </>
              ) : (
                <>
                  <PlayCircle className="h-4 w-4" />
                  Start Behavioral Test
                </>
              )}
            </Button>

            {testResult && !isRunning && (
              <Button
                onClick={downloadReport}
                variant="outline"
                className="flex items-center gap-2"
              >
                <Download className="h-4 w-4" />
                Download Report
              </Button>
            )}
          </div>

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-red-700 text-sm">{error}</p>
            </div>
          )}

          {isRunning && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Test Progress</span>
                <span>{Math.round(progress)}%</span>
              </div>
              <Progress value={progress} className="w-full" />
            </div>
          )}

          {testResult && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-3 bg-gray-50 rounded-lg">
                  <div className="text-sm text-gray-600">Status</div>
                  <Badge variant={getStatusBadgeVariant(testResult.status)}>
                    {testResult.status}
                  </Badge>
                </div>

                <div className="p-3 bg-gray-50 rounded-lg">
                  <div className="text-sm text-gray-600">Total Scenarios</div>
                  <div className="text-lg font-medium">{testResult.total_scenarios}</div>
                </div>

                <div className="p-3 bg-gray-50 rounded-lg">
                  <div className="text-sm text-gray-600">Success Rate</div>
                  <div className="text-lg font-medium">
                    {testResult.total_scenarios > 0
                      ? `${Math.round((testResult.passed_scenarios / testResult.total_scenarios) * 100)}%`
                      : '0%'
                    }
                  </div>
                </div>

                <div className="p-3 bg-gray-50 rounded-lg">
                  <div className="text-sm text-gray-600">Behavioral Score</div>
                  <div className={`text-lg font-medium ${getBehavioralScoreColor(testResult.behavioral_score)}`}>
                    {testResult.behavioral_score
                      ? `${Math.round(testResult.behavioral_score * 100)}%`
                      : 'N/A'
                    }
                  </div>
                </div>
              </div>

              <div className="p-4 border rounded-lg">
                <h4 className="font-medium mb-2">Test Summary</h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                  <div>
                    <span className="text-green-600">Passed:</span> {testResult.passed_scenarios}
                  </div>
                  <div>
                    <span className="text-red-600">Failed:</span> {testResult.failed_scenarios}
                  </div>
                  <div>
                    <span className="text-gray-600">Duration:</span> {Math.round(testResult.execution_time_ms / 1000)}s
                  </div>
                </div>
              </div>
            </div>
          )}

          <div className="p-4 border rounded-lg">
            <h4 className="font-medium mb-2">Default Test Scenarios</h4>
            <div className="space-y-2">
              {defaultScenarios.map((scenario, index) => (
                <div key={index} className="flex justify-between items-center p-2 bg-gray-50 rounded">
                  <span className="text-sm font-medium">{scenario.scenario}</span>
                  <span className="text-xs text-gray-600">{scenario.steps.length} steps</span>
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default BehavioralTest;