from fastapi import APIRouter, HTTPException, BackgroundTasks
import uuid
import time
import json
import os
from datetime import datetime
from typing import Dict, Any, List

from models import (
    BenchmarkRunRequest,
    BenchmarkRunResponse,
    BenchmarkStatusResponse,
    BenchmarkReportResponse,
    ScenarioDefinition,
    CustomScenarioRequest,
    PerformanceBenchmark,
    PerformanceMetric,
)

router = APIRouter()

# In-memory storage for POC (replace with database interaction later)
mock_benchmark_runs: Dict[str, Dict[str, Any]] = {}
mock_benchmark_reports: Dict[str, Dict[str, Any]] = {}


# Load scenarios from JSON files
def load_scenarios_from_files():
    """Load benchmark scenarios from JSON files in ai-engine/src/benchmarking/scenarios/"""
    scenarios = {}
    scenarios_dir = os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "..",
        "ai-engine",
        "src",
        "benchmarking",
        "scenarios",
    )

    if os.path.exists(scenarios_dir):
        for filename in os.listdir(scenarios_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(scenarios_dir, filename)
                try:
                    with open(filepath, "r") as f:
                        scenario_data = json.load(f)
                        scenario_id = scenario_data.get(
                            "scenario_id", filename.replace(".json", "")
                        )
                        scenarios[scenario_id] = scenario_data
                except Exception as e:
                    print(f"Error loading scenario from {filepath}: {e}")

    # Fallback scenarios if files don't exist
    if not scenarios:
        scenarios = {
            "baseline_idle_001": {
                "scenario_id": "baseline_idle_001",
                "scenario_name": "Idle Performance",
                "description": "Measure performance impact when add-on is loaded but not actively used.",
                "type": "baseline",
                "duration_seconds": 300,
                "parameters": {"load_level": "none"},
                "thresholds": {"cpu": 5, "memory": 50, "fps": 30},
            },
            "stress_entity_001": {
                "scenario_id": "stress_entity_001",
                "scenario_name": "High Entity Count Stress Test",
                "description": "Test performance with a high number of custom entities.",
                "type": "stress_test",
                "duration_seconds": 600,
                "parameters": {"entity_count": 1000, "load_level": "high"},
                "thresholds": {"cpu": 80, "memory": 500, "fps": 30},
            },
        }

    return scenarios


mock_scenarios = load_scenarios_from_files()


def simulate_benchmark_execution(
    run_id: str, scenario_id: str, device_type: str = "desktop"
):
    """
    Function to integrate with the actual PerformanceBenchmarkingSystem in ai-engine.
    Currently simulates execution but includes proper integration structure.
    """
    print(
        f"Starting benchmark run {run_id} for scenario {scenario_id} on {device_type}..."
    )

    # Update status to running
    mock_benchmark_runs[run_id].update(
        {"status": "running", "progress": 0.0, "current_stage": "initializing"}
    )

    try:
        # TODO: Import and integrate with actual PerformanceBenchmarkingSystem
        # from ai_engine.src.benchmarking.performance_system import PerformanceBenchmarkingSystem
        # benchmark_system = PerformanceBenchmarkingSystem()

        scenario = mock_scenarios.get(scenario_id)
        if not scenario:
            raise ValueError(f"Scenario {scenario_id} not found")

        # Simulate the benchmark execution stages
        stages = [
            ("initializing", 10),
            ("collecting_baseline", 30),
            ("running_load_tests", 60),
            ("analyzing_results", 80),
            ("generating_report", 100),
        ]

        for stage_name, progress in stages:
            mock_benchmark_runs[run_id].update(
                {"progress": progress, "current_stage": stage_name}
            )
            time.sleep(1)  # Simulate work

        # Simulate successful completion with detailed results
        benchmark_result = PerformanceBenchmark(
            id=run_id,
            scenario_id=scenario_id,
            scenario_name=scenario.get("scenario_name", "Unknown"),
            device_type=device_type,
            overall_score=85.5,
            cpu_score=80.0,
            memory_score=90.0,
            network_score=88.0,
            status="completed",
        )

        # Mock performance metrics
        metrics = [
            PerformanceMetric(
                benchmark_id=run_id,
                metric_name="cpu_usage_percent",
                metric_category="cpu",
                java_value=60.0,
                bedrock_value=50.0,
                unit="percent",
                improvement_percentage=-16.67,
            ),
            PerformanceMetric(
                benchmark_id=run_id,
                metric_name="memory_usage_mb",
                metric_category="memory",
                java_value=200.0,
                bedrock_value=180.0,
                unit="MB",
                improvement_percentage=-10.0,
            ),
        ]

        analysis = {
            "identified_issues": ["No major performance issues detected"],
            "optimization_suggestions": [
                "Performance appears within acceptable limits"
            ],
        }

        comparison_results = {
            "cpu": {
                "cpu_usage_percent": {
                    "java_value": 60.0,
                    "bedrock_value": 50.0,
                    "improvement_percentage": -16.67,
                }
            },
            "memory": {
                "memory_usage_mb": {
                    "java_value": 200.0,
                    "bedrock_value": 180.0,
                    "improvement_percentage": -10.0,
                }
            },
        }

        report_text = f"""
Performance Benchmark Report for {scenario.get("scenario_name", "Unknown")}
================================================================

Scenario: {scenario_id}
Device Type: {device_type}
Duration: {scenario.get("duration_seconds", 0)} seconds

Overall Performance Score: {benchmark_result.overall_score}/100
- CPU Score: {benchmark_result.cpu_score}/100
- Memory Score: {benchmark_result.memory_score}/100
- Network Score: {benchmark_result.network_score}/100

Key Improvements:
- CPU usage improved by 16.67% (Java: 60% → Bedrock: 50%)
- Memory usage improved by 10.0% (Java: 200MB → Bedrock: 180MB)

Analysis: {analysis["identified_issues"][0]}
Recommendations: {analysis["optimization_suggestions"][0]}
"""

        mock_benchmark_runs[run_id].update(
            {"status": "completed", "progress": 100.0, "current_stage": "completed"}
        )

        mock_benchmark_reports[run_id] = {
            "benchmark": benchmark_result.model_dump(),
            "metrics": [m.model_dump() for m in metrics],
            "analysis": analysis,
            "comparison_results": comparison_results,
            "report_text": report_text,
        }

        print(f"Benchmark run {run_id} completed successfully.")

    except Exception as e:
        print(f"Benchmark run {run_id} failed: {e}")
        mock_benchmark_runs[run_id].update({"status": "failed", "error": str(e)})


@router.post("/run", response_model=BenchmarkRunResponse, status_code=202)
async def run_benchmark_endpoint(
    request: BenchmarkRunRequest, background_tasks: BackgroundTasks
):
    """
    Triggers a new performance benchmark run for a given scenario.
    """
    if request.scenario_id not in mock_scenarios:
        raise HTTPException(
            status_code=404, detail=f"Scenario ID '{request.scenario_id}' not found."
        )

    run_id = str(uuid.uuid4())
    mock_benchmark_runs[run_id] = {
        "status": "pending",
        "scenario_id": request.scenario_id,
        "device_type": request.device_type,
        "conversion_id": request.conversion_id,
        "created_at": datetime.now(datetime.UTC).isoformat(),
        "progress": 0.0,
        "current_stage": "pending",
    }

    background_tasks.add_task(
        simulate_benchmark_execution, run_id, request.scenario_id, request.device_type
    )

    return BenchmarkRunResponse(
        run_id=run_id,
        status="accepted",
        message=f"Benchmark run accepted for scenario '{request.scenario_id}'. Check status at /status/{run_id}",
    )


@router.get("/status/{run_id}", response_model=BenchmarkStatusResponse)
async def get_benchmark_status_endpoint(run_id: str):
    """
    Retrieves the status of an ongoing or completed benchmark run.
    """
    run_info = mock_benchmark_runs.get(run_id)
    if not run_info:
        raise HTTPException(
            status_code=404, detail=f"Benchmark run ID '{run_id}' not found."
        )

    return BenchmarkStatusResponse(
        run_id=run_id,
        status=run_info["status"],
        progress=run_info.get("progress", 0.0),
        current_stage=run_info.get("current_stage", "unknown"),
        estimated_completion=None,  # TODO: Calculate based on progress
    )


@router.get("/report/{run_id}", response_model=BenchmarkReportResponse)
async def get_benchmark_report_endpoint(run_id: str):
    """
    Retrieves the performance benchmark report for a completed run.
    """
    run_info = mock_benchmark_runs.get(run_id)
    if not run_info:
        raise HTTPException(
            status_code=404, detail=f"Benchmark run ID '{run_id}' not found."
        )

    if run_info["status"] != "completed":
        return BenchmarkReportResponse(
            run_id=run_id,
            benchmark=None,
            metrics=[],
            analysis={},
            comparison_results={},
            report_text=f"Report not available yet. Benchmark status: {run_info['status']}",
            optimization_suggestions=[],
        )

    report_data = mock_benchmark_reports.get(run_id)
    if not report_data:
        raise HTTPException(
            status_code=404,
            detail=f"Report data for run ID '{run_id}' not found, though run marked completed.",
        )

    return BenchmarkReportResponse(
        run_id=run_id,
        benchmark=report_data["benchmark"],
        metrics=report_data["metrics"],
        analysis=report_data["analysis"],
        comparison_results=report_data["comparison_results"],
        report_text=report_data["report_text"],
        optimization_suggestions=report_data["analysis"].get(
            "optimization_suggestions", []
        ),
    )


@router.get("/scenarios", response_model=List[ScenarioDefinition])
async def list_benchmark_scenarios_endpoint():
    """
    Lists available benchmark scenarios.
    """
    scenarios = []
    for scenario_id, scenario_data in mock_scenarios.items():
        scenarios.append(
            ScenarioDefinition(
                scenario_id=scenario_id,
                scenario_name=scenario_data.get("scenario_name", "Unknown"),
                description=scenario_data.get("description", ""),
                type=scenario_data.get("type", "unknown"),
                duration_seconds=scenario_data.get("duration_seconds", 300),
                parameters=scenario_data.get("parameters", {}),
                thresholds=scenario_data.get("thresholds", {}),
            )
        )
    return scenarios


@router.post("/scenarios", response_model=ScenarioDefinition, status_code=201)
async def create_custom_scenario_endpoint(request: CustomScenarioRequest):
    """
    Creates a custom benchmark scenario.
    """
    scenario_id = f"custom_{str(uuid.uuid4()).replace('-', '')[:8]}"

    scenario_data = {
        "scenario_id": scenario_id,
        "scenario_name": request.scenario_name,
        "description": request.description,
        "type": request.type,
        "duration_seconds": request.duration_seconds,
        "parameters": request.parameters,
        "thresholds": request.thresholds,
        "created_at": datetime.now(datetime.UTC).isoformat(),
        "custom": True,
    }

    mock_scenarios[scenario_id] = scenario_data

    return ScenarioDefinition(**scenario_data)


@router.get("/history", response_model=List[Dict[str, Any]])
async def get_benchmark_history_endpoint(limit: int = 50, offset: int = 0):
    """
    Retrieves historical benchmark run data for performance tracking.
    """
    # Convert to list and sort by creation time
    all_runs = []
    for run_id, run_data in mock_benchmark_runs.items():
        if run_data.get("status") == "completed":
            report_data = mock_benchmark_reports.get(run_id, {})
            all_runs.append(
                {
                    "run_id": run_id,
                    "scenario_id": run_data.get("scenario_id"),
                    "device_type": run_data.get("device_type", "desktop"),
                    "created_at": run_data.get("created_at"),
                    "overall_score": report_data.get("benchmark", {}).get(
                        "overall_score", 0
                    ),
                    "cpu_score": report_data.get("benchmark", {}).get("cpu_score", 0),
                    "memory_score": report_data.get("benchmark", {}).get(
                        "memory_score", 0
                    ),
                    "network_score": report_data.get("benchmark", {}).get(
                        "network_score", 0
                    ),
                }
            )

    # Sort by creation time (newest first)
    all_runs.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    # Apply pagination
    return all_runs[offset : offset + limit]
