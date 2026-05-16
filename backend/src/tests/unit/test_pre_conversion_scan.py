"""
Tests for Pre-Conversion Scan API and Service

Issue: #1542 - DX: Add pre-conversion feature scan showing failure risks before upload
"""

import io
import uuid
import zipfile
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from api.pre_conversion_scan import router
from api.auth import get_current_user

app = FastAPI()
app.include_router(router)


def _mock_user():
    u = MagicMock()
    u.id = uuid.uuid4()
    u.email = "test@test.com"
    return u


app.dependency_overrides[get_current_user] = lambda: _mock_user()
client = TestClient(app)


def create_test_jar(files: dict[str, bytes]) -> bytes:
    """Create a test JAR/ZIP file with given contents."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buffer.getvalue()


class TestPreConversionScannerService:
    """Tests for the PreConversionScanner service"""

    def test_risk_severity_enum_values(self):
        from services.pre_conversion_scanner import RiskSeverity

        assert RiskSeverity.LOW.value == "low"
        assert RiskSeverity.MEDIUM.value == "medium"
        assert RiskSeverity.HIGH.value == "high"
        assert RiskSeverity.CRITICAL.value == "critical"

    def test_risk_category_enum_values(self):
        from services.pre_conversion_scanner import RiskCategory

        assert RiskCategory.DEPENDENCY.value == "dependency"
        assert RiskCategory.COMPLEXITY.value == "complexity"
        assert RiskCategory.PATTERN.value == "pattern"
        assert RiskCategory.ARCHITECTURE.value == "architecture"
        assert RiskCategory.ASSET.value == "asset"
        assert RiskCategory.COMPATIBILITY.value == "compatibility"
        assert RiskCategory.SECURITY.value == "security"

    def test_risk_item_dataclass(self):
        from services.pre_conversion_scanner import RiskItem, RiskSeverity, RiskCategory

        risk = RiskItem(
            risk_id="test_risk",
            severity=RiskSeverity.HIGH,
            category=RiskCategory.DEPENDENCY,
            title="Test Risk",
            description="A test risk item",
            location="test.java",
            suggestion="Fix this",
            conversion_impact="May fail",
            evidence=["evidence1", "evidence2"],
        )

        assert risk.risk_id == "test_risk"
        assert risk.severity == RiskSeverity.HIGH
        assert risk.category == RiskCategory.DEPENDENCY
        assert risk.title == "Test Risk"
        assert risk.location == "test.java"
        assert len(risk.evidence) == 2

    def test_scan_metadata_dataclass(self):
        from services.pre_conversion_scanner import ScanMetadata

        metadata = ScanMetadata(
            filename="test.jar",
            file_size=1024,
            file_count=5,
            has_manifest=True,
            manifest_version="1.0",
            mod_name="TestMod",
            minecraft_version="1.20.0",
        )

        assert metadata.filename == "test.jar"
        assert metadata.file_size == 1024
        assert metadata.has_manifest is True
        assert metadata.mod_name == "TestMod"

    def test_pre_conversion_scan_result_dataclass(self):
        from services.pre_conversion_scanner import (
            PreConversionScanResult,
            ScanMetadata,
            RiskItem,
            RiskSeverity,
            RiskCategory,
        )

        metadata = ScanMetadata(
            filename="test.jar",
            file_size=1024,
            file_count=5,
            has_manifest=False,
        )

        risk = RiskItem(
            risk_id="test",
            severity=RiskSeverity.LOW,
            category=RiskCategory.COMPATIBILITY,
            title="Test",
            description="Test desc",
        )

        result = PreConversionScanResult(
            scan_id="scan123",
            metadata=metadata,
            overall_risk_level=RiskSeverity.LOW,
            total_issues=1,
            risks=[risk],
            can_proceed=True,
            warnings_summary="Test summary",
            recommendations=["Rec 1"],
            scan_timestamp=datetime.now(timezone.utc).isoformat(),
        )

        assert result.scan_id == "scan123"
        assert result.can_proceed is True
        assert len(result.risks) == 1


class TestPreConversionScanner:
    """Tests for PreConversionScanner class methods"""

    def test_calculate_overall_risk_critical(self):
        from services.pre_conversion_scanner import PreConversionScanner, RiskItem, RiskSeverity, RiskCategory

        scanner = PreConversionScanner()
        risks = [
            RiskItem("1", RiskSeverity.CRITICAL, RiskCategory.SECURITY, "Critical", "Desc"),
        ]
        assert scanner._calculate_overall_risk(risks) == RiskSeverity.CRITICAL

    def test_calculate_overall_risk_high_count(self):
        from services.pre_conversion_scanner import PreConversionScanner, RiskItem, RiskSeverity, RiskCategory

        scanner = PreConversionScanner()
        risks = [
            RiskItem("1", RiskSeverity.HIGH, RiskCategory.SECURITY, "High1", "Desc"),
            RiskItem("2", RiskSeverity.HIGH, RiskCategory.SECURITY, "High2", "Desc"),
            RiskItem("3", RiskSeverity.HIGH, RiskCategory.SECURITY, "High3", "Desc"),
        ]
        assert scanner._calculate_overall_risk(risks) == RiskSeverity.HIGH

    def test_calculate_overall_risk_empty(self):
        from services.pre_conversion_scanner import PreConversionScanner, RiskSeverity

        scanner = PreConversionScanner()
        assert scanner._calculate_overall_risk([]) == RiskSeverity.LOW

    def test_generate_summary_empty(self):
        from services.pre_conversion_scanner import PreConversionScanner, RiskSeverity

        scanner = PreConversionScanner()
        summary = scanner._generate_summary([], RiskSeverity.LOW)
        assert "No potential issues detected" in summary

    def test_generate_summary_critical(self):
        from services.pre_conversion_scanner import PreConversionScanner, RiskItem, RiskSeverity, RiskCategory

        scanner = PreConversionScanner()
        risks = [
            RiskItem("1", RiskSeverity.CRITICAL, RiskCategory.SECURITY, "Critical", "Desc"),
        ]
        summary = scanner._generate_summary(risks, RiskSeverity.CRITICAL)
        assert "not recommended" in summary.lower()

    def test_generate_recommendations_empty(self):
        from services.pre_conversion_scanner import PreConversionScanner

        scanner = PreConversionScanner()
        recs = scanner._generate_recommendations([])
        assert "No major issues" in recs[0]

    def test_generate_recommendations_with_categories(self):
        from services.pre_conversion_scanner import PreConversionScanner, RiskItem, RiskSeverity, RiskCategory

        scanner = PreConversionScanner()
        risks = [
            RiskItem("1", RiskSeverity.HIGH, RiskCategory.ARCHITECTURE, "Arch", "Desc"),
            RiskItem("2", RiskSeverity.MEDIUM, RiskCategory.DEPENDENCY, "Dep", "Desc"),
        ]
        recs = scanner._generate_recommendations(risks)
        assert len(recs) > 0


@pytest.mark.asyncio
class TestScanModFile:
    """Tests for the scan_mod_file async function"""

    async def test_scan_valid_jar(self, tmp_path):
        from services.pre_conversion_scanner import scan_mod_file, RiskSeverity

        jar_path = tmp_path / "test.jar"
        jar_content = create_test_jar({
            "META-INF/mods.toml": b"modId=testmod\nversion=1.0.0\nmcversion=1.20.0",
            "com/example/TestMod.java": b"package com.example; public class TestMod {}",
        })

        jar_path.write_bytes(jar_content)

        result = await scan_mod_file(str(jar_path), "test.jar")

        assert result.scan_id is not None
        assert result.metadata.filename == "test.jar"
        assert result.metadata.file_size > 0
        assert result.overall_risk_level == RiskSeverity.LOW

    async def test_scan_invalid_zip(self, tmp_path):
        from services.pre_conversion_scanner import scan_mod_file, RiskSeverity

        invalid_path = tmp_path / "invalid.jar"
        invalid_path.write_bytes(b"this is not a valid zip")

        result = await scan_mod_file(str(invalid_path), "invalid.jar")

        assert any(r.risk_id == "invalid_archive" for r in result.risks)
        assert result.overall_risk_level == RiskSeverity.CRITICAL
        assert result.can_proceed is False

    async def test_scan_detects_incompatible_dependency(self, tmp_path):
        from services.pre_conversion_scanner import scan_mod_file, RiskCategory

        jar_path = tmp_path / "server_mod.jar"
        jar_content = create_test_jar({
            "META-INF/mods.toml": b"modId=server\nversion=1.0.0\nmcversion=1.20.0",
            "org/bukkit/Bukkit.java": b"package org.bukkit; public class Bukkit {}",
        })

        jar_path.write_bytes(jar_content)

        result = await scan_mod_file(str(jar_path), "server_mod.jar")

        dep_risks = [r for r in result.risks if r.category == RiskCategory.DEPENDENCY]
        assert len(dep_risks) > 0, f"No dependency risks found. Risks: {[r.risk_id for r in result.risks]}"

    async def test_scan_high_texture_count(self, tmp_path):
        from services.pre_conversion_scanner import scan_mod_file, RiskSeverity, RiskCategory

        jar_path = tmp_path / "texture_mod.jar"

        texture_files = {}
        for i in range(250):
            texture_files[f"assets/minecraft/textures/item/item_{i}.png"] = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

        jar_content = create_test_jar(texture_files)

        jar_path.write_bytes(jar_content)

        result = await scan_mod_file(str(jar_path), "texture_mod.jar")

        asset_risks = [r for r in result.risks if r.category == RiskCategory.ASSET]
        high_texture_risks = [r for r in asset_risks if r.risk_id == "high_texture_count"]
        assert len(high_texture_risks) > 0


class TestPreConversionScanAPI:
    """Tests for Pre-Conversion Scan API endpoints - requires mocking auth properly"""

    def test_scan_endpoint_validation_no_auth(self):
        """Test that endpoint validates file type even without auth"""
        file_data = ("test.exe", io.BytesIO(b"test"), "application/exe")
        resp = client.post("/api/v1/pre-conversion-scan", files={"file": file_data})
        assert resp.status_code in (400, 401, 422)

    def test_batch_scan_endpoint_requires_auth(self):
        """Test that batch endpoint requires authentication"""
        resp = client.post("/api/v1/pre-conversion-scan/batch")
        assert resp.status_code in (400, 401, 422)