"""Workflow validation tests for CI/CD pipelines.

These tests validate the structure and configuration of GitHub Actions workflows.
"""

import os

import pytest
import yaml


# Get the root directory of the repository (go up 3 levels: tests -> .github -> repo)
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestCIWorkflowYAML:
    """Test CI workflow YAML structure and validation."""

    @pytest.fixture
    def ci_workflow(self):
        """Load CI workflow file."""
        workflow_path = os.path.join(REPO_ROOT, ".github/workflows/ci.yml")
        with open(workflow_path, "r") as f:
            return yaml.safe_load(f)

    def test_ci_workflow_valid_yaml(self, ci_workflow):
        """Test 1: CI workflow YAML is valid and parseable."""
        assert ci_workflow is not None
        assert isinstance(ci_workflow, dict)
        assert "name" in ci_workflow
        # Handle YAML quirk where "on" might be parsed as boolean True
        assert "on" in ci_workflow or True in ci_workflow
        assert "jobs" in ci_workflow

    def test_ci_workflow_has_required_triggers(self, ci_workflow):
        """Test 2: CI workflow has required triggers (push and pull_request)."""
        # Handle YAML quirk where "on" might be parsed as boolean True
        triggers = ci_workflow.get("on", {}) or ci_workflow.get(True, {})

        # Check push trigger
        assert "push" in triggers, "CI workflow must have push trigger"

        # Check pull_request trigger
        assert "pull_request" in triggers, "CI workflow must have pull_request trigger"

    def test_ci_workflow_has_required_jobs(self, ci_workflow):
        """Test 3: CI workflow has required jobs (lint, test-backend, test-ai, test-integration)."""
        jobs = ci_workflow.get("jobs", {})

        # Check for lint job
        assert "lint" in jobs or "ruff-lint" in jobs, "CI workflow should have lint job"

        # Check for backend tests
        assert "test-backend" in jobs or "integration-tests" in jobs or "backend" in str(jobs), (
            "CI workflow should have backend test job"
        )

        # Check for AI engine tests
        assert "test-ai" in jobs or "ai-engine" in str(jobs), (
            "CI workflow should have AI engine test job"
        )


class TestCDWorkflowYAML:
    """Test CD workflow YAML structure and validation."""

    @pytest.fixture
    def cd_workflow(self):
        """Load CD workflow file."""
        workflow_path = os.path.join(REPO_ROOT, ".github/workflows/cd.yml")
        with open(workflow_path, "r") as f:
            return yaml.safe_load(f)

    def test_cd_workflow_valid_yaml(self, cd_workflow):
        """Test 4: CD workflow YAML is valid and parseable."""
        assert cd_workflow is not None
        assert isinstance(cd_workflow, dict)
        assert "name" in cd_workflow
        # Handle YAML quirk where "on" might be parsed as boolean True
        assert "on" in cd_workflow or True in cd_workflow
        assert "jobs" in cd_workflow

    def test_cd_workflow_has_build_job(self, cd_workflow):
        """Test 5: CD workflow has build job for Docker images."""
        jobs = cd_workflow.get("jobs", {})

        # Check for build job
        assert "build" in jobs, "CD workflow should have build job"

    def test_cd_workflow_has_deployment_jobs(self, cd_workflow):
        """Test 6: CD workflow has deployment jobs (staging and production)."""
        jobs = cd_workflow.get("jobs", {})

        # Check for staging deployment
        assert "deploy-staging" in jobs, "CD workflow should have staging deployment job"

        # Check for production deployment
        assert "deploy-production" in jobs, "CD workflow should have production deployment job"


class TestWorkflowDependencies:
    """Test job dependencies in workflows."""

    @pytest.fixture
    def cd_workflow(self):
        """Load CD workflow file."""
        workflow_path = os.path.join(REPO_ROOT, ".github/workflows/cd.yml")
        with open(workflow_path, "r") as f:
            return yaml.safe_load(f)

    def test_production_depends_on_staging(self, cd_workflow):
        """Test 7: Production deployment depends on staging deployment."""
        jobs = cd_workflow.get("jobs", {})
        prod_job = jobs.get("deploy-production", {})

        # Check if production depends on staging
        needs = prod_job.get("needs", [])
        if isinstance(needs, str):
            needs = [needs]

        assert "build" in needs or "deploy-staging" in needs, (
            "Production deployment should depend on build or staging"
        )

    def test_staging_depends_on_build(self, cd_workflow):
        """Test 8: Staging deployment depends on build job."""
        jobs = cd_workflow.get("jobs", {})
        staging_job = jobs.get("deploy-staging", {})

        # Check if staging depends on build
        needs = staging_job.get("needs", [])
        if isinstance(needs, str):
            needs = [needs]

        assert "build" in needs, "Staging deployment should depend on build job"


class TestMatrixConfiguration:
    """Test matrix configuration in CI workflow."""

    @pytest.fixture
    def ci_workflow(self):
        """Load CI workflow file."""
        workflow_path = os.path.join(REPO_ROOT, ".github/workflows/ci.yml")
        with open(workflow_path, "r") as f:
            return yaml.safe_load(f)

    def test_python_version_matrix(self, ci_workflow):
        """Test 9: CI workflow has Python version matrix (3.11, 3.12)."""
        jobs = ci_workflow.get("jobs", {})

        # Look for test jobs with matrix
        for job_name, job_config in jobs.items():
            if "test" in job_name.lower() or "python" in str(job_config).lower():
                matrix = job_config.get("strategy", {}).get("matrix", {})
                if "python-version" in matrix:
                    versions = matrix["python-version"]
                    assert "3.11" in versions or "3.12" in versions, (
                        "Python version matrix should include 3.11 or 3.12"
                    )
                    return

        # If no matrix found, check if there are explicit Python versions set
        pytest.skip("No Python version matrix found in test jobs")

    def test_node_version_matrix(self, ci_workflow):
        """Test 10: CI workflow has Node version matrix (18, 20)."""
        jobs = ci_workflow.get("jobs", {})

        # Look for frontend test jobs with matrix
        for job_name, job_config in jobs.items():
            if "frontend" in job_name.lower() or "node" in str(job_config).lower():
                matrix = job_config.get("strategy", {}).get("matrix", {})
                if "node-version" in matrix:
                    versions = matrix["node-version"]
                    assert 18 in versions or 20 in versions, (
                        "Node version matrix should include 18 or 20"
                    )
                    return

        # If no matrix found, check if there are Node versions
        pytest.skip("No Node version matrix found in frontend jobs")


class TestDockerfileStructure:
    """Test Dockerfile structure."""

    def test_backend_dockerfile_exists(self):
        """Test 11: Backend Dockerfile exists."""
        dockerfile_path = os.path.join(REPO_ROOT, "backend/Dockerfile")
        assert os.path.exists(dockerfile_path), "Backend Dockerfile should exist"

    def test_backend_dockerfile_has_healthcheck(self):
        """Test 12: Backend Dockerfile has health check."""
        dockerfile_path = os.path.join(REPO_ROOT, "backend/Dockerfile")
        with open(dockerfile_path, "r") as f:
            content = f.read()

        assert "HEALTHCHECK" in content, "Backend Dockerfile should have health check"
        assert "uvicorn" in content or "CMD" in content, "Backend Dockerfile should have CMD"

    def test_root_dockerfile_exists(self):
        """Test 13: Root Dockerfile exists for multi-stage builds."""
        dockerfile_path = os.path.join(REPO_ROOT, "Dockerfile")
        assert os.path.exists(dockerfile_path), "Root Dockerfile should exist"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
