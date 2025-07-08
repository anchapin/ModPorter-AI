from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
import uuid
import time # For simulating delays

router = APIRouter()

# In-memory storage for POC (replace with database interaction later)
mock_benchmark_runs = {}
mock_benchmark_reports = {}
mock_scenarios = {
    "baseline_idle_001": {
      "scenario_id": "baseline_idle_001",
      "scenario_name": "Idle Performance",
      "description": "Measure performance impact when add-on is loaded but not actively used.",
      "type": "baseline",
      "duration_seconds": 300,
    },
    "stress_entity_001": {
      "scenario_id": "stress_entity_001",
      "scenario_name": "High Entity Count Stress Test",
      "description": "Test performance with a high number of custom entities.",
      "type": "stress_test",
      "duration_seconds": 600,
    }
}

class BenchmarkRunRequest(BaseModel):
    scenario_id: str
    # Potentially add conversion_id, device_type etc. later

class BenchmarkRunResponse(BaseModel):
    run_id: str
    status: str
    message: str

class BenchmarkStatusResponse(BaseModel):
    run_id: str
    status: str
    details: dict = None

class BenchmarkReportResponse(BaseModel):
    run_id: str
    status: str # e.g. "completed", "pending", "error"
    report_data: dict = None # This will eventually hold the full report from BenchmarkReporter
    error_message: str = None

def simulate_benchmark_execution(run_id: str, scenario_id: str):
    """
    Placeholder function to simulate running a benchmark.
    In a real system, this would trigger the PerformanceBenchmarkingSystem in ai-engine.
    """
    print(f"Simulating benchmark run {run_id} for scenario {scenario_id}...")
    mock_benchmark_runs[run_id] = {"status": "running", "scenario_id": scenario_id, "progress": 0}

    # Simulate time for benchmark
    time.sleep(2) # Short delay for POC, reduced from 5 to speed up testing if needed
    mock_benchmark_runs[run_id]["progress"] = 50
    time.sleep(2) # Reduced from 5
    mock_benchmark_runs[run_id]["progress"] = 100

    # Simulate completion and report generation
    mock_benchmark_runs[run_id]["status"] = "completed"
    mock_benchmark_reports[run_id] = {
        "run_id": run_id,
        "scenario_id": scenario_id,
        "overall_score": 85.5, # Example data
        "cpu_score": 80.0,
        "memory_score": 90.0,
        "network_score": 88.0,
        "summary": f"Benchmark for {scenario_id} completed successfully.",
        "details": {
            "java_metrics": {"cpu_usage": 60, "memory_mb": 200},
            "bedrock_metrics": {"cpu_usage": 50, "memory_mb": 180},
            "comparison": {"cpu_improvement_percent": -16.67, "memory_improvement_percent": -10.00}
        }
    }
    print(f"Benchmark run {run_id} simulation finished.")


@router.post("/run", response_model=BenchmarkRunResponse, status_code=202)
async def run_benchmark_endpoint(request: BenchmarkRunRequest, background_tasks: BackgroundTasks):
    """
    Triggers a new performance benchmark run for a given scenario.
    """
    if request.scenario_id not in mock_scenarios:
        raise HTTPException(status_code=404, detail=f"Scenario ID '{request.scenario_id}' not found.")

    run_id = str(uuid.uuid4())
    mock_benchmark_runs[run_id] = {"status": "pending", "scenario_id": request.scenario_id}

    background_tasks.add_task(simulate_benchmark_execution, run_id, request.scenario_id)

    return BenchmarkRunResponse(
        run_id=run_id,
        status="accepted",
        message=f"Benchmark run accepted for scenario '{request.scenario_id}'. Check status at /status/{run_id}"
    )

@router.get("/status/{run_id}", response_model=BenchmarkStatusResponse)
async def get_benchmark_status_endpoint(run_id: str):
    """
    Retrieves the status of an ongoing or completed benchmark run.
    """
    run_info = mock_benchmark_runs.get(run_id)
    if not run_info:
        raise HTTPException(status_code=404, detail=f"Benchmark run ID '{run_id}' not found.")

    return BenchmarkStatusResponse(run_id=run_id, status=run_info["status"], details=run_info)

@router.get("/report/{run_id}", response_model=BenchmarkReportResponse)
async def get_benchmark_report_endpoint(run_id: str):
    """
    Retrieves the performance benchmark report for a completed run.
    """
    run_info = mock_benchmark_runs.get(run_id)
    if not run_info:
        raise HTTPException(status_code=404, detail=f"Benchmark run ID '{run_id}' not found.")

    if run_info["status"] != "completed":
        return BenchmarkReportResponse(
            run_id=run_id,
            status=run_info["status"],
            report_data=None,
            error_message="Report not available yet. Benchmark is not completed."
        )

    report_data = mock_benchmark_reports.get(run_id)
    if not report_data:
        raise HTTPException(status_code=404, detail=f"Report data for run ID '{run_id}' not found, though run marked completed.")

    return BenchmarkReportResponse(run_id=run_id, status="completed", report_data=report_data)

@router.get("/scenarios", response_model=list[dict])
async def list_benchmark_scenarios_endpoint():
    """
    Lists available benchmark scenarios.
    """
    return [sc_info for sc_id, sc_info in mock_scenarios.items()]
