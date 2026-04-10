import logging
from pathlib import Path
from typing import Dict, Any, List
from pydantic import BaseModel

from qa.context import QAContext
from qa.orchestrator import QAOrchestrator

logger = logging.getLogger(__name__)


class QASettings(BaseModel):
    enabled: bool = False


class QAIntegrationHook:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.orchestrator = QAOrchestrator()

    def run_post_conversion_qa(self, job_dir: Path) -> Dict[str, Any]:
        if not self.enabled:
            logger.info("QA disabled, skipping post-conversion QA")
            return {"skipped": True, "reason": "QA disabled"}

        logger.info("Running post-conversion QA", job_dir=str(job_dir))

        context = self.create_qa_context_from_job_dir(job_dir)

        result = self.orchestrator.run_qa_pipeline(context)

        summary = self._create_summary(result)

        return summary

    def create_qa_context_from_job_dir(self, job_dir: Path) -> QAContext:
        source_java_files = self._discover_java_files(job_dir)
        output_bedrock_files = self._discover_bedrock_files(job_dir)

        metadata = {
            "source_java_count": len(source_java_files),
            "source_java_files": [str(f) for f in source_java_files],
            "output_bedrock_count": len(output_bedrock_files),
            "output_bedrock_files": [str(f) for f in output_bedrock_files],
        }

        job_dir_path = job_dir.resolve()
        source_path = job_dir / "source_java"
        output_path = job_dir / "output_bedrock"

        if not source_path.exists():
            source_path = job_dir

        if not output_path.exists():
            output_path = job_dir

        return QAContext(
            job_id=job_dir.name,
            job_dir=job_dir_path,
            source_java_path=source_path,
            output_bedrock_path=output_path,
            metadata=metadata,
        )

    def _discover_java_files(self, job_dir: Path) -> List[Path]:
        java_files = []
        if job_dir.exists():
            java_files = list(job_dir.rglob("*.java"))
        return java_files

    def _discover_bedrock_files(self, job_dir: Path) -> List[Path]:
        bedrock_files = []
        behavior_pack = job_dir / "behavior_pack"
        resource_pack = job_dir / "resource_pack"

        if behavior_pack.exists():
            bedrock_files.extend(behavior_pack.rglob("*"))
            bedrock_files = [f for f in bedrock_files if f.is_file()]

        if resource_pack.exists():
            bedrock_files.extend(resource_pack.rglob("*"))
            bedrock_files = [f for f in bedrock_files if f.is_file()]

        return bedrock_files

    def _create_summary(self, context: QAContext) -> Dict[str, Any]:
        agents_run = list(context.validation_results.keys())
        successful_agents = [
            name
            for name, result in context.validation_results.items()
            if result.get("success", False)
        ]
        failed_agents = [
            name
            for name, result in context.validation_results.items()
            if not result.get("success", False) and not result.get("skipped", False)
        ]
        skipped_agents = [
            name
            for name, result in context.validation_results.items()
            if result.get("skipped", False)
        ]

        return {
            "job_id": context.job_id,
            "agents_run": agents_run,
            "successful_agents": successful_agents,
            "failed_agents": failed_agents,
            "skipped_agents": skipped_agents,
            "validation_results": context.validation_results,
            "overall_success": len(failed_agents) == 0,
        }


def run_post_conversion_qa(job_dir: Path, enabled: bool = True) -> Dict[str, Any]:
    hook = QAIntegrationHook(enabled=enabled)
    return hook.run_post_conversion_qa(job_dir)
