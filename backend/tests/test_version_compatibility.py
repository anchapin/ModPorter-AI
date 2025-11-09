"""
Comprehensive tests for Version Compatibility System API
"""
import pytest
import json
from uuid import uuid4
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


class TestVersionCompatibilityAPI:
    """Test suite for Version Compatibility System endpoints"""

    @pytest.mark.asyncio
    async def test_create_compatibility_entry(self, async_client: AsyncClient):
        """Test creating a new compatibility entry"""
        compatibility_data = {
            "source_version": "1.18.2",
            "target_version": "1.19.2",
            "compatibility_score": 0.85,
            "conversion_complexity": "medium",
            "breaking_changes": [
                {"type": "method_removal", "impact": "high", "affected_apis": ["Block.setState"]},
                {"type": "parameter_change", "impact": "medium", "affected_apis": ["Item.register"]}
            ],
            "migration_guide": {
                "steps": [
                    {"step": 1, "action": "update_block_registry", "description": "Use new registry method"},
                    {"step": 2, "action": "fix_item_properties", "description": "Update property names"}
                ],
                "estimated_time": "2-4 hours",
                "required_tools": ["migrate_tool", "code_analyzer"]
            },
            "test_results": {
                "success_rate": 0.9,
                "total_tests": 50,
                "failed_tests": 5,
                "known_issues": ["texture_mapping", "sound_events"]
            }
        }
        
        response = await async_client.post("/api/version-compatibility/entries/", json=compatibility_data)
        assert response.status_code == 201
        
        data = response.json()
        assert data["source_version"] == "1.18.2"
        assert data["target_version"] == "1.19.2"
        assert data["compatibility_score"] == 0.85
        assert len(data["breaking_changes"]) == 2

    @pytest.mark.asyncio
    async def test_get_compatibility_matrix(self, async_client: AsyncClient):
        """Test getting the full compatibility matrix"""
        response = await async_client.get("/api/version-compatibility/matrix/")
        assert response.status_code == 200
        
        data = response.json()
        assert "matrix" in data
        assert "versions" in data
        assert "metadata" in data
        assert "last_updated" in data

    @pytest.mark.asyncio
    async def test_get_version_compatibility(self, async_client: AsyncClient):
        """Test getting compatibility between specific versions"""
        # Create compatibility entry first
        compatibility_data = {
            "source_version": "1.17.1",
            "target_version": "1.18.2",
            "compatibility_score": 0.75,
            "conversion_complexity": "high"
        }
        
        await async_client.post("/api/version-compatibility/entries/", json=compatibility_data)
        
        # Get compatibility info
        response = await async_client.get("/api/version-compatibility/compatibility/1.17.1/1.18.2")
        assert response.status_code == 200
        
        data = response.json()
        assert data["source_version"] == "1.17.1"
        assert data["target_version"] == "1.18.2"
        assert data["compatibility_score"] == 0.75

    @pytest.mark.asyncio
    async def test_find_migration_paths(self, async_client: AsyncClient):
        """Test finding migration paths between versions"""
        response = await async_client.get("/api/version-compatibility/paths/1.16.5/1.19.2")
        assert response.status_code == 200
        
        data = response.json()
        assert "paths" in data
        assert "optimal_path" in data
        assert "alternatives" in data
        
        if data["paths"]:
            path = data["paths"][0]
            assert "steps" in path
            assert "total_complexity" in path
            assert "estimated_time" in path

    @pytest.mark.asyncio
    async def test_get_migration_guide(self, async_client: AsyncClient):
        """Test getting detailed migration guide"""
        # Create compatibility entry with migration guide
        guide_data = {
            "source_version": "1.18.1",
            "target_version": "1.19.2",
            "compatibility_score": 0.8,
            "migration_guide": {
                "overview": "Migration from 1.18.1 to 1.19.2",
                "prerequisites": ["backup_world", "update_dependencies"],
                "steps": [
                    {
                        "step": 1,
                        "title": "Update Mod Dependencies",
                        "description": "Update all mod dependencies to 1.19.2 compatible versions",
                        "commands": ["./gradlew updateDependencies"],
                        "verification": "Check build.gradle for updated versions"
                    },
                    {
                        "step": 2,
                        "title": "Migrate Block Registry",
                        "description": "Update block registration to use new Forge registry system",
                        "code_changes": [
                            {"file": "Registry.java", "old": "OLD_REGISTRY.register()", "new": "NEW_REGISTRY.register()"}
                        ]
                    }
                ],
                "common_issues": [
                    {"issue": "Block state not loading", "solution": "Update block state mapping"},
                    {"issue": "Texture missing", "solution": "Update texture resource location"}
                ],
                "testing": ["run_integration_tests", "verify_world_loading", "check_block_functionality"]
            }
        }
        
        await async_client.post("/api/version-compatibility/entries/", json=guide_data)
        
        # Get migration guide
        response = await async_client.get("/api/version-compatibility/migration-guide/1.18.1/1.19.2")
        assert response.status_code == 200
        
        data = response.json()
        assert "overview" in data
        assert "steps" in data
        assert "common_issues" in data
        assert "testing" in data
        assert len(data["steps"]) >= 2

    @pytest.mark.asyncio
    async def test_get_version_statistics(self, async_client: AsyncClient):
        """Test getting version compatibility statistics"""
        response = await async_client.get("/api/version-compatibility/statistics/")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_version_pairs" in data
        assert "average_compatibility_score" in data
        assert "most_compatible_versions" in data
        assert "least_compatible_versions" in data
        assert "version_adoption_trend" in data

    @pytest.mark.asyncio
    async def test_validate_compatibility_data(self, async_client: AsyncClient):
        """Test validating compatibility data"""
        validation_data = {
            "source_version": "1.18.2",
            "target_version": "1.19.2",
            "breaking_changes": [
                {"type": "method_removal", "affected_apis": ["Block.oldMethod"]},
                {"type": "class_restructure", "affected_classes": ["ItemBlock"]}
            ],
            "test_results": {
                "successful_conversions": 45,
                "failed_conversions": 5,
                "total_conversions": 50
            }
        }
        
        response = await async_client.post("/api/version-compatibility/validate/", json=validation_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "is_valid" in data
        assert "validation_errors" in data
        assert "warnings" in data
        assert "suggested_improvements" in data

    @pytest.mark.asyncio
    async def test_update_compatibility_entry(self, async_client: AsyncClient):
        """Test updating an existing compatibility entry"""
        # Create entry first
        create_data = {
            "source_version": "1.17.1",
            "target_version": "1.18.2",
            "compatibility_score": 0.7
        }
        
        create_response = await async_client.post("/api/version-compatibility/entries/", json=create_data)
        entry_id = create_response.json()["id"]
        
        # Update entry
        update_data = {
            "compatibility_score": 0.75,
            "breaking_changes": [
                {"type": "minor_change", "impact": "low", "description": "Updated parameter names"}
            ],
            "migration_guide": {
                "steps": [
                    {"step": 1, "action": "update_parameters", "description": "Update method parameters"}
                ]
            }
        }
        
        response = await async_client.put(f"/api/version-compatibility/entries/{entry_id}", json=update_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["compatibility_score"] == 0.75
        assert len(data["breaking_changes"]) == 1

    @pytest.mark.asyncio
    async def test_delete_compatibility_entry(self, async_client: AsyncClient):
        """Test deleting a compatibility entry"""
        # Create entry
        create_data = {
            "source_version": "1.16.5",
            "target_version": "1.17.1",
            "compatibility_score": 0.6
        }
        
        create_response = await async_client.post("/api/version-compatibility/entries/", json=create_data)
        entry_id = create_response.json()["id"]
        
        # Delete entry
        response = await async_client.delete(f"/api/version-compatibility/entries/{entry_id}")
        assert response.status_code == 204
        
        # Verify deletion
        get_response = await async_client.get(f"/api/version-compatibility/entries/{entry_id}")
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_batch_import_compatibility(self, async_client: AsyncClient):
        """Test batch import of compatibility data"""
        batch_data = {
            "entries": [
                {
                    "source_version": "1.15.2",
                    "target_version": "1.16.5",
                    "compatibility_score": 0.65,
                    "conversion_complexity": "medium"
                },
                {
                    "source_version": "1.16.5",
                    "target_version": "1.17.1",
                    "compatibility_score": 0.7,
                    "conversion_complexity": "low"
                },
                {
                    "source_version": "1.17.1",
                    "target_version": "1.18.2",
                    "compatibility_score": 0.8,
                    "conversion_complexity": "low"
                }
            ],
            "import_options": {
                "validate_data": True,
                "overwrite_existing": False,
                "create_migration_guides": True
            }
        }
        
        response = await async_client.post("/api/version-compatibility/batch-import/", json=batch_data)
        assert response.status_code == 202  # Accepted for processing
        
        data = response.json()
        assert "batch_id" in data
        assert "status" in data
        assert "total_entries" in data

    @pytest.mark.asyncio
    async def test_get_compatibility_trends(self, async_client: AsyncClient):
        """Test getting compatibility trends over time"""
        response = await async_client.get("/api/version-compatibility/trends/", params={
            "start_version": "1.15.2",
            "end_version": "1.19.2",
            "metric": "compatibility_score"
        })
        assert response.status_code == 200
        
        data = response.json()
        assert "trends" in data
        assert "time_series" in data
        assert "summary" in data
        assert "insights" in data

    @pytest.mark.asyncio
    async def test_get_version_family_info(self, async_client: AsyncClient):
        """Test getting information about a version family"""
        response = await async_client.get("/api/version-compatibility/family/1.19")
        assert response.status_code == 200
        
        data = response.json()
        assert "family_name" in data
        assert "versions" in data
        assert "characteristics" in data
        assert "migration_patterns" in data
        assert "known_issues" in data

    @pytest.mark.asyncio
    async def test_predict_compatibility(self, async_client: AsyncClient):
        """Test predicting compatibility for untested version pairs"""
        prediction_data = {
            "source_version": "1.18.2",
            "target_version": "1.20.0",
            "context": {
                "mod_type": "forge",
                "complexity_indicators": ["custom_blocks", "entities", "networking"],
                "codebase_size": "medium"
            }
        }
        
        response = await async_client.post("/api/version-compatibility/predict/", json=prediction_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "predicted_score" in data
        assert "confidence_interval" in data
        assert "risk_factors" in data
        assert "recommendations" in data

    @pytest.mark.asyncio
    async def test_export_compatibility_data(self, async_client: AsyncClient):
        """Test exporting compatibility data"""
        response = await async_client.get("/api/version-compatibility/export/", params={
            "format": "csv",
            "include_migration_guides": True,
            "version_range": "1.17.0-1.19.2"
        })
        assert response.status_code == 200
        
        # Verify it's a CSV export
        assert "text/csv" in response.headers["content-type"]

    @pytest.mark.asyncio
    async def test_get_complexity_analysis(self, async_client: AsyncClient):
        """Test getting complexity analysis for version migration"""
        response = await async_client.get("/api/version-compatibility/complexity/1.18.2/1.19.2")
        assert response.status_code == 200
        
        data = response.json()
        assert "overall_complexity" in data
        assert "complexity_breakdown" in data
        assert "time_estimates" in data
        assert "skill_requirements" in data
        assert "risk_assessment" in data

    @pytest.mark.asyncio
    async def test_invalid_version_format(self, async_client: AsyncClient):
        """Test validation of invalid version formats"""
        invalid_data = {
            "source_version": "invalid.version",
            "target_version": "1.19.2",
            "compatibility_score": 1.5  # Invalid score > 1.0
        }
        
        response = await async_client.post("/api/version-compatibility/entries/", json=invalid_data)
        assert response.status_code == 422  # Validation error
