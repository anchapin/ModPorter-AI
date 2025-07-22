/**
 * Performance Benchmark Component
 * Provides interface for running performance benchmarks and viewing results
 */

import React, { useState, useEffect, useCallback } from 'react';
import { performanceBenchmarkAPI } from '../../services/api';
import './PerformanceBenchmark.css';

interface Scenario {
  scenario_id: string;
  scenario_name: string;
  description: string;
  type: string;
  duration_seconds: number;
  parameters: Record<string, any>;
  thresholds: Record<string, number>;
}

interface BenchmarkRun {
  run_id: string;
  status: string;
  progress: number;
  current_stage: string;
  estimated_completion?: string;
}

interface BenchmarkReport {
  run_id: string;
  benchmark: {
    overall_score: number;
    cpu_score: number;
    memory_score: number;
    network_score: number;
    scenario_name: string;
    device_type: string;
  };
  metrics: Array<{
    metric_name: string;
    metric_category: string;
    java_value: number;
    bedrock_value: number;
    unit: string;
    improvement_percentage: number;
  }>;
  analysis: {
    identified_issues: string[];
    optimization_suggestions: string[];
  };
  report_text: string;
  optimization_suggestions: string[];
}

interface CustomScenarioData {
  scenario_name: string;
  description: string;
  type: string;
  duration_seconds: number;
  parameters: Record<string, any>;
  thresholds: Record<string, number>;
}

export const PerformanceBenchmark: React.FC = () => {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [selectedScenario, setSelectedScenario] = useState<string>('');
  const [deviceType, setDeviceType] = useState<string>('desktop');
  const [conversionId, setConversionId] = useState<string>('');
  const [currentRun, setCurrentRun] = useState<BenchmarkRun | null>(null);
  const [currentReport, setCurrentReport] = useState<BenchmarkReport | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showCreateScenario, setShowCreateScenario] = useState(false);
  const [customScenario, setCustomScenario] = useState<CustomScenarioData>({
    scenario_name: '',
    description: '',
    type: 'custom',
    duration_seconds: 300,
    parameters: {},
    thresholds: {}
  });

  const loadScenarios = async () => {
    try {
      const response = await performanceBenchmarkAPI.getScenarios();
      setScenarios(response.data);
    } catch (err) {
      setError('Failed to load scenarios');
      console.error('Error loading scenarios:', err);
    }
  };

  const loadBenchmarkReport = useCallback(async (runId: string) => {
    try {
      const response = await performanceBenchmarkAPI.getBenchmarkReport(runId);
      setCurrentReport(response.data);
    } catch (err) {
      setError('Failed to load benchmark report');
      console.error('Error loading report:', err);
    }
  }, []);

  const pollBenchmarkStatus = useCallback(async () => {
    if (!currentRun) return;

    try {
      const response = await performanceBenchmarkAPI.getBenchmarkStatus(currentRun.run_id);
      const status = response.data;

      setCurrentRun(status);

      if (status.status === 'completed') {
        setIsRunning(false);
        await loadBenchmarkReport(currentRun.run_id);
      } else if (status.status === 'failed') {
        setIsRunning(false);
        setError('Benchmark failed');
      }
    } catch (err) {
      console.error('Error polling benchmark status:', err);
    }
  }, [currentRun, loadBenchmarkReport]);

  // Load scenarios on component mount
  useEffect(() => {
    loadScenarios();
  }, []);

  // Poll for updates when a benchmark is running
  useEffect(() => {
    if (isRunning && currentRun) {
      const interval = setInterval(() => {
        pollBenchmarkStatus();
      }, 2000);

      return () => clearInterval(interval);
    }
  }, [isRunning, currentRun, pollBenchmarkStatus]);

  const runBenchmark = async () => {
    if (!selectedScenario) {
      setError('Please select a scenario');
      return;
    }

    setIsRunning(true);
    setError(null);
    setCurrentReport(null);

    try {
      const response = await performanceBenchmarkAPI.runBenchmark({
        scenario_id: selectedScenario,
        device_type: deviceType,
        conversion_id: conversionId || undefined
      });

      setCurrentRun({
        run_id: response.data.run_id,
        status: 'pending',
        progress: 0,
        current_stage: 'initializing'
      });

      // Start polling for status updates
      setTimeout(pollBenchmarkStatus, 1000);
    } catch (err) {
      setError('Failed to start benchmark');
      setIsRunning(false);
      console.error('Error starting benchmark:', err);
    }
  };


  const createCustomScenario = async () => {
    if (!customScenario.scenario_name || !customScenario.description) {
      setError('Please provide scenario name and description');
      return;
    }

    try {
      const response = await performanceBenchmarkAPI.createCustomScenario(customScenario);
      setScenarios([...scenarios, response.data]);
      setShowCreateScenario(false);
      setCustomScenario({
        scenario_name: '',
        description: '',
        type: 'custom',
        duration_seconds: 300,
        parameters: {},
        thresholds: {}
      });
    } catch (err) {
      setError('Failed to create custom scenario');
      console.error('Error creating scenario:', err);
    }
  };

  const selectedScenarioData = scenarios.find(s => s.scenario_id === selectedScenario);

  return (
    <div className="performance-benchmark">
      <h2>Performance Benchmarking</h2>
      
      {error && (
        <div className="error-message">
          <span className="error-icon">⚠️</span>
          {error}
        </div>
      )}

      <div className="benchmark-controls">
        <div className="control-group">
          <label htmlFor="scenario-select">Select Scenario:</label>
          <select
            id="scenario-select"
            value={selectedScenario}
            onChange={(e) => setSelectedScenario(e.target.value)}
            disabled={isRunning}
          >
            <option value="">-- Choose a scenario --</option>
            {scenarios.map(scenario => (
              <option key={scenario.scenario_id} value={scenario.scenario_id}>
                {scenario.scenario_name} ({scenario.type})
              </option>
            ))}
          </select>
        </div>

        {selectedScenarioData && (
          <div className="scenario-details">
            <h3>Scenario Details</h3>
            <p><strong>Description:</strong> {selectedScenarioData.description}</p>
            <p><strong>Type:</strong> {selectedScenarioData.type}</p>
            <p><strong>Duration:</strong> {selectedScenarioData.duration_seconds} seconds</p>
            <p><strong>Parameters:</strong> {JSON.stringify(selectedScenarioData.parameters)}</p>
            <p><strong>Thresholds:</strong> {JSON.stringify(selectedScenarioData.thresholds)}</p>
          </div>
        )}

        <div className="control-group">
          <label htmlFor="device-type">Device Type:</label>
          <select
            id="device-type"
            value={deviceType}
            onChange={(e) => setDeviceType(e.target.value)}
            disabled={isRunning}
          >
            <option value="desktop">Desktop</option>
            <option value="mobile">Mobile</option>
            <option value="server">Server</option>
          </select>
        </div>

        <div className="control-group">
          <label htmlFor="conversion-id">Conversion ID (optional):</label>
          <input
            id="conversion-id"
            type="text"
            value={conversionId}
            onChange={(e) => setConversionId(e.target.value)}
            placeholder="Enter conversion ID to link benchmark"
            disabled={isRunning}
          />
        </div>

        <div className="button-group">
          <button
            onClick={runBenchmark}
            disabled={isRunning || !selectedScenario}
            className="run-benchmark-btn"
          >
            {isRunning ? 'Running...' : 'Run Benchmark'}
          </button>
          
          <button
            onClick={() => setShowCreateScenario(true)}
            disabled={isRunning}
            className="create-scenario-btn"
          >
            Create Custom Scenario
          </button>
        </div>
      </div>

      {/* Custom Scenario Creation Modal */}
      {showCreateScenario && (
        <div className="custom-scenario-modal">
          <div className="modal-content">
            <h3>Create Custom Scenario</h3>
            
            <div className="form-group">
              <label>Scenario Name:</label>
              <input
                type="text"
                value={customScenario.scenario_name}
                onChange={(e) => setCustomScenario({...customScenario, scenario_name: e.target.value})}
                placeholder="Enter scenario name"
              />
            </div>

            <div className="form-group">
              <label>Description:</label>
              <textarea
                value={customScenario.description}
                onChange={(e) => setCustomScenario({...customScenario, description: e.target.value})}
                placeholder="Describe the scenario"
              />
            </div>

            <div className="form-group">
              <label>Type:</label>
              <select
                value={customScenario.type}
                onChange={(e) => setCustomScenario({...customScenario, type: e.target.value})}
              >
                <option value="custom">Custom</option>
                <option value="stress">Stress Test</option>
                <option value="load">Load Test</option>
                <option value="memory">Memory Test</option>
              </select>
            </div>

            <div className="form-group">
              <label>Duration (seconds):</label>
              <input
                type="number"
                value={customScenario.duration_seconds}
                onChange={(e) => setCustomScenario({...customScenario, duration_seconds: parseInt(e.target.value)})}
                min="60"
                max="3600"
              />
            </div>

            <div className="modal-buttons">
              <button onClick={createCustomScenario}>Create Scenario</button>
              <button onClick={() => setShowCreateScenario(false)}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Benchmark Progress */}
      {currentRun && isRunning && (
        <div className="benchmark-progress">
          <h3>Benchmark Progress</h3>
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${currentRun.progress}%` }}
            ></div>
          </div>
          <p>Status: {currentRun.status}</p>
          <p>Stage: {currentRun.current_stage}</p>
          <p>Progress: {currentRun.progress}%</p>
        </div>
      )}

      {/* Benchmark Report */}
      {currentReport && (
        <div className="benchmark-report">
          <h3>Benchmark Report</h3>
          
          <div className="score-summary">
            <div className="score-item">
              <span className="score-label">Overall Score:</span>
              <span className="score-value">{currentReport.benchmark.overall_score}/100</span>
            </div>
            <div className="score-item">
              <span className="score-label">CPU Score:</span>
              <span className="score-value">{currentReport.benchmark.cpu_score}/100</span>
            </div>
            <div className="score-item">
              <span className="score-label">Memory Score:</span>
              <span className="score-value">{currentReport.benchmark.memory_score}/100</span>
            </div>
            <div className="score-item">
              <span className="score-label">Network Score:</span>
              <span className="score-value">{currentReport.benchmark.network_score}/100</span>
            </div>
          </div>

          <div className="metrics-table">
            <h4>Performance Metrics</h4>
            <table>
              <thead>
                <tr>
                  <th>Metric</th>
                  <th>Category</th>
                  <th>Java Value</th>
                  <th>Bedrock Value</th>
                  <th>Improvement</th>
                </tr>
              </thead>
              <tbody>
                {currentReport.metrics.map((metric, index) => (
                  <tr key={index}>
                    <td>{metric.metric_name}</td>
                    <td>{metric.metric_category}</td>
                    <td>{metric.java_value} {metric.unit}</td>
                    <td>{metric.bedrock_value} {metric.unit}</td>
                    <td className={metric.improvement_percentage < 0 ? 'improvement' : 'regression'}>
                      {metric.improvement_percentage.toFixed(1)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="analysis-section">
            <h4>Analysis</h4>
            <div className="issues">
              <h5>Identified Issues:</h5>
              <ul>
                {currentReport.analysis.identified_issues.map((issue, index) => (
                  <li key={index}>{issue}</li>
                ))}
              </ul>
            </div>
            <div className="suggestions">
              <h5>Optimization Suggestions:</h5>
              <ul>
                {currentReport.analysis.optimization_suggestions.map((suggestion, index) => (
                  <li key={index}>{suggestion}</li>
                ))}
              </ul>
            </div>
          </div>

          <div className="report-text">
            <h4>Detailed Report</h4>
            <pre>{currentReport.report_text}</pre>
          </div>
        </div>
      )}
    </div>
  );
};