"""
Version Compatibility Matrix Service

This service manages the compatibility matrix between different Minecraft
Java and Bedrock versions for conversion patterns and features.
"""

import logging
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db.knowledge_graph_crud import (
    VersionCompatibilityCRUD,
    ConversionPatternCRUD
)
from ..models import VersionCompatibility

logger = logging.getLogger(__name__)


class VersionCompatibilityService:
    """Service for managing version compatibility matrix."""
    
    def __init__(self):
        # Initialize with default compatibility data
        self.default_compatibility = self._load_default_compatibility()
        
    async def get_compatibility(
        self,
        java_version: str,
        bedrock_version: str,
        db: AsyncSession
    ) -> Optional[VersionCompatibility]:
        """
        Get compatibility information between Java and Bedrock versions.
        
        Args:
            java_version: Minecraft Java edition version
            bedrock_version: Minecraft Bedrock edition version
            db: Database session
        
        Returns:
            Version compatibility data or None if not found
        """
        try:
            # Try to find exact match in database
            compatibility = await VersionCompatibilityCRUD.get_compatibility(
                db, java_version, bedrock_version
            )
            
            if compatibility:
                return compatibility
            
            # If no exact match, try to find closest versions
            return await self._find_closest_compatibility(
                db, java_version, bedrock_version
            )
            
        except Exception as e:
            logger.error(f"Error getting version compatibility: {e}")
            return None
    
    async def get_by_java_version(
        self,
        java_version: str,
        db: AsyncSession
    ) -> List[VersionCompatibility]:
        """
        Get all compatibility entries for a specific Java version.
        
        Args:
            java_version: Minecraft Java edition version
            db: Database session
        
        Returns:
            List of compatibility entries
        """
        try:
            return await VersionCompatibilityCRUD.get_by_java_version(db, java_version)
        except Exception as e:
            logger.error(f"Error getting compatibility by Java version: {e}")
            return []
    
    async def get_supported_features(
        self,
        java_version: str,
        db: AsyncSession,
        bedrock_version: str,
        feature_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get features supported between specific Java and Bedrock versions.
        
        Args:
            java_version: Minecraft Java edition version
            bedrock_version: Minecraft Bedrock edition version
            feature_type: Optional filter for specific feature type
            db: Database session
        
        Returns:
            Supported features with conversion details
        """
        try:
            # Get compatibility data
            compatibility = await self.get_compatibility(
                java_version, bedrock_version, db
            )
            
            if not compatibility:
                return {
                    "supported": False,
                    "features": [],
                    "message": f"No compatibility data found for Java {java_version} to Bedrock {bedrock_version}"
                }
            
            # Filter features by type if specified
            features = compatibility.features_supported
            if feature_type:
                features = [f for f in features if f.get("type") == feature_type]
            
            # Get conversion patterns for these versions
            patterns = await ConversionPatternCRUD.get_by_version(
                db, minecraft_version=java_version, 
                validation_status="validated"
            )
            
            # Extract relevant patterns for the feature type
            relevant_patterns = []
            if feature_type:
                relevant_patterns = [p for p in patterns if feature_type in p.get("tags", [])]
            else:
                relevant_patterns = patterns
            
            return {
                "supported": True,
                "compatibility_score": compatibility.compatibility_score,
                "features": features,
                "patterns": [
                    {
                        "id": p.id,
                        "name": p.name,
                        "description": p.description,
                        "success_rate": p.success_rate,
                        "tags": p.tags,
                        "java_version": p.minecraft_versions
                    }
                    for p in relevant_patterns
                ],
                "migration_guides": compatibility.migration_guides,
                "deprecated_patterns": compatibility.deprecated_patterns,
                "auto_update_rules": compatibility.auto_update_rules
            }
            
        except Exception as e:
            logger.error(f"Error getting supported features: {e}")
            return {
                "supported": False,
                "features": [],
                "error": str(e)
            }
    
    async def update_compatibility(
        self,
        java_version: str,
        bedrock_version: str,
        compatibility_data: Dict[str, Any],
        db: AsyncSession
    ) -> bool:
        """
        Update compatibility information between versions.
        
        Args:
            java_version: Minecraft Java edition version
            bedrock_version: Minecraft Bedrock edition version
            compatibility_data: New compatibility information
            db: Database session
        
        Returns:
            True if update successful, False otherwise
        """
        try:
            # Check if compatibility entry already exists
            existing = await VersionCompatibilityCRUD.get_compatibility(
                db, java_version, bedrock_version
            )
            
            if existing:
                # Update existing entry
                update_data = {
                    "compatibility_score": compatibility_data.get("compatibility_score", 0.0),
                    "features_supported": compatibility_data.get("features_supported", []),
                    "deprecated_patterns": compatibility_data.get("deprecated_patterns", []),
                    "migration_guides": compatibility_data.get("migration_guides", {}),
                    "auto_update_rules": compatibility_data.get("auto_update_rules", {}),
                    "known_issues": compatibility_data.get("known_issues", [])
                }
                
                from ..db.knowledge_graph_crud import VersionCompatibilityCRUD
                success = await VersionCompatibilityCRUD.update(
                    db, existing.id, update_data
                )
            else:
                # Create new entry
                create_data = {
                    "java_version": java_version,
                    "bedrock_version": bedrock_version,
                    "compatibility_score": compatibility_data.get("compatibility_score", 0.0),
                    "features_supported": compatibility_data.get("features_supported", []),
                    "deprecated_patterns": compatibility_data.get("deprecated_patterns", []),
                    "migration_guides": compatibility_data.get("migration_guides", {}),
                    "auto_update_rules": compatibility_data.get("auto_update_rules", {}),
                    "known_issues": compatibility_data.get("known_issues", [])
                }
                
                new_compatibility = await VersionCompatibilityCRUD.create(db, create_data)
                success = new_compatibility is not None
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating compatibility: {e}")
            return False
    
    async def get_conversion_path(
        self,
        java_version: str,
        bedrock_version: str,
        feature_type: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Get optimal conversion path between versions for specific feature type.
        
        Args:
            java_version: Minecraft Java edition version
            bedrock_version: Minecraft Bedrock edition version
            feature_type: Type of feature to convert
            db: Database session
        
        Returns:
            Conversion path with intermediate versions if needed
        """
        try:
            # First check direct compatibility
            direct_compatibility = await self.get_compatibility(
                java_version, bedrock_version, db
            )
            
            if direct_compatibility and direct_compatibility.compatibility_score >= 0.8:
                # Direct conversion is possible with high compatibility
                return {
                    "path_type": "direct",
                    "steps": [
                        {
                            "from_version": java_version,
                            "to_version": bedrock_version,
                            "compatibility_score": direct_compatibility.compatibility_score,
                            "features": direct_compatibility.features_supported,
                            "patterns": await self._get_relevant_patterns(
                                db, java_version, feature_type
                            )
                        }
                    ]
                }
            
            # Need intermediate steps - find optimal path
            return await self._find_optimal_conversion_path(
                db, java_version, bedrock_version, feature_type
            )
            
        except Exception as e:
            logger.error(f"Error finding conversion path: {e}")
            return {
                "path_type": "failed",
                "error": str(e),
                "message": "Failed to find conversion path"
            }
    
    async def get_matrix_overview(
        self,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Get overview of version compatibility matrix.
        
        Args:
            db: Database session
        
        Returns:
            Matrix overview with statistics and summary data
        """
        try:
            # Get all compatibility entries
            query = select(VersionCompatibility)
            result = await db.execute(query)
            compatibilities = result.scalars().all()
            
            if not compatibilities:
                return {
                    "total_combinations": 0,
                    "java_versions": [],
                    "bedrock_versions": [],
                    "average_compatibility": 0.0,
                    "matrix": {}
                }
            
            # Extract unique versions
            java_versions = list(set(c.java_version for c in compatibilities))
            bedrock_versions = list(set(c.bedrock_version for c in compatibilities))
            
            # Build compatibility matrix
            matrix = {}
            for jv in java_versions:
                matrix[jv] = {}
                for bv in bedrock_versions:
                    # Find compatibility entry
                    compat = next((c for c in compatibilities 
                                 if c.java_version == jv and c.bedrock_version == bv), None)
                    
                    if compat:
                        matrix[jv][bv] = {
                            "score": compat.compatibility_score,
                            "features_count": len(compat.features_supported),
                            "issues_count": len(compat.known_issues)
                        }
                    else:
                        matrix[jv][bv] = None
            
            # Calculate statistics
            scores = [c.compatibility_score for c in compatibilities]
            average_score = sum(scores) / len(scores) if scores else 0.0
            
            high_compatibility = sum(1 for s in scores if s >= 0.8)
            medium_compatibility = sum(1 for s in scores if 0.5 <= s < 0.8)
            low_compatibility = sum(1 for s in scores if s < 0.5)
            
            return {
                "total_combinations": len(compatibilities),
                "java_versions": sorted(java_versions),
                "bedrock_versions": sorted(bedrock_versions),
                "average_compatibility": average_score,
                "compatibility_distribution": {
                    "high": high_compatibility,
                    "medium": medium_compatibility,
                    "low": low_compatibility
                },
                "matrix": matrix,
                "last_updated": max((c.updated_at for c in compatibilities)).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting matrix overview: {e}")
            return {
                "error": str(e),
                "message": "Failed to get matrix overview"
            }
    
    async def generate_migration_guide(
        self,
        from_java_version: str,
        to_bedrock_version: str,
        features: List[str],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Generate migration guide for specific versions and features.
        
        Args:
            from_java_version: Source Java edition version
            to_bedrock_version: Target Bedrock edition version
            features: List of features to migrate
            db: Database session
        
        Returns:
            Detailed migration guide with step-by-step instructions
        """
        try:
            # Get compatibility data
            compatibility = await self.get_compatibility(
                from_java_version, to_bedrock_version, db
            )
            
            if not compatibility:
                return {
                    "error": "No compatibility data found",
                    "message": f"No migration data available for Java {from_java_version} to Bedrock {to_bedrock_version}"
                }
            
            # Get relevant patterns for features
            relevant_patterns = []
            for feature in features:
                patterns = await self._get_relevant_patterns(
                    db, from_java_version, feature
                )
                relevant_patterns.extend(patterns)
            
            # Generate step-by-step guide
            guide = {
                "from_version": from_java_version,
                "to_version": to_bedrock_version,
                "compatibility_score": compatibility.compatibility_score,
                "features": features,
                "steps": [],
                "patterns": [
                    {
                        "id": p.id,
                        "name": p.name,
                        "description": p.description,
                        "success_rate": p.success_rate
                    }
                    for p in relevant_patterns
                ],
                "known_issues": compatibility.known_issues,
                "additional_resources": compatibility.migration_guides.get(
                    "resources", []
                )
            }
            
            # Generate migration steps
            if compatibility.compatibility_score >= 0.8:
                # High compatibility - direct migration
                guide["steps"] = await self._generate_direct_migration_steps(
                    from_java_version, to_bedrock_version, features, db
                )
            else:
                # Lower compatibility - need intermediate steps
                guide["steps"] = await self._generate_gradual_migration_steps(
                    from_java_version, to_bedrock_version, features, db
                )
            
            return guide
            
        except Exception as e:
            logger.error(f"Error generating migration guide: {e}")
            return {
                "error": str(e),
                "message": "Failed to generate migration guide"
            }
    
    async def _find_closest_compatibility(
        self,
        db: AsyncSession,
        java_version: str,
        bedrock_version: str
    ) -> Optional[VersionCompatibility]:
        """Find closest version compatibility when exact match not found."""
        try:
            # Get all Java and Bedrock versions
            query = select(VersionCompatibility)
            result = await db.execute(query)
            all_compatibilities = result.scalars().all()
            
            if not all_compatibilities:
                return None
            
            # Find closest Java version
            java_versions = list(set(c.java_version for c in all_compatibilities))
            closest_java = self._find_closest_version(java_version, java_versions)
            
            # Find closest Bedrock version
            bedrock_versions = list(set(c.bedrock_version for c in all_compatibilities))
            closest_bedrock = self._find_closest_version(bedrock_version, bedrock_versions)
            
            # Find compatibility between closest versions
            closest_compat = next((c for c in all_compatibilities 
                               if c.java_version == closest_java and 
                               c.bedrock_version == closest_bedrock), None)
            
            return closest_compat
            
        except Exception as e:
            logger.error(f"Error finding closest compatibility: {e}")
            return None
    
    def _find_closest_version(self, target_version: str, available_versions: List[str]) -> str:
        """Find closest version from available versions."""
        try:
            # Parse version numbers and find closest
            target_parts = [int(p) for p in target_version.split('.') if p.isdigit()]
            
            if not target_parts:
                return available_versions[0] if available_versions else target_version
            
            best_version = available_versions[0] if available_versions else target_version
            best_score = float('inf')
            
            for version in available_versions:
                version_parts = [int(p) for p in version.split('.') if p.isdigit()]
                if not version_parts:
                    continue
                
                # Calculate distance between versions
                max_len = max(len(target_parts), len(version_parts))
                score = 0
                
                for i in range(max_len):
                    t_val = target_parts[i] if i < len(target_parts) else 0
                    v_val = version_parts[i] if i < len(version_parts) else 0
                    score += abs(t_val - v_val)
                
                if score < best_score:
                    best_score = score
                    best_version = version
            
            return best_version
            
        except Exception as e:
            logger.error(f"Error finding closest version: {e}")
            return target_version
    
    async def _find_optimal_conversion_path(
        self,
        db: AsyncSession,
        java_version: str,
        bedrock_version: str,
        feature_type: str
    ) -> Dict[str, Any]:
        """Find optimal conversion path with intermediate versions."""
        try:
            # Get all versions sorted by release date
            java_versions = await self._get_sorted_java_versions(db)
            bedrock_versions = await self._get_sorted_bedrock_versions(db)
            
            # Find positions of source and target versions
            try:
                java_start_idx = java_versions.index(java_version)
            except ValueError:
                return {"path_type": "failed", "message": f"Source Java version {java_version} not found"}
            
            try:
                bedrock_target_idx = bedrock_versions.index(bedrock_version)
            except ValueError:
                return {"path_type": "failed", "message": f"Target Bedrock version {bedrock_version} not found"}
            
            # Find intermediate Java and Bedrock versions
            # Simple strategy: use one intermediate step
            intermediate_java_idx = min(java_start_idx + 1, len(java_versions) - 1)
            intermediate_java = java_versions[intermediate_java_idx]
            
            # Find compatible Bedrock version for intermediate Java
            intermediate_bedrock = await self._find_best_bedrock_match(
                db, intermediate_java, feature_type
            )
            
            if not intermediate_bedrock:
                # Try to find any compatible Bedrock version
                for bv in bedrock_versions:
                    compat = await self.get_compatibility(
                        intermediate_java, bv, db
                    )
                    if compat and compat.compatibility_score >= 0.5:
                        intermediate_bedrock = bv
                        break
            
            if not intermediate_bedrock:
                return {"path_type": "failed", "message": "No suitable intermediate versions found"}
            
            # Check final compatibility
            final_compatibility = await self.get_compatibility(
                intermediate_bedrock, bedrock_version, db
            )
            
            if not final_compatibility or final_compatibility.compatibility_score < 0.5:
                return {"path_type": "failed", "message": "Final compatibility too low"}
            
            # Build path steps
            first_compat = await self.get_compatibility(
                java_version, intermediate_bedrock, db
            )
            
            return {
                "path_type": "intermediate",
                "steps": [
                    {
                        "from_version": java_version,
                        "to_version": intermediate_bedrock,
                        "compatibility_score": first_compat.compatibility_score if first_compat else 0.0,
                        "patterns": await self._get_relevant_patterns(
                            db, java_version, feature_type
                        )
                    },
                    {
                        "from_version": intermediate_bedrock,
                        "to_version": bedrock_version,
                        "compatibility_score": final_compatibility.compatibility_score,
                        "patterns": await self._get_relevant_patterns(
                            db, intermediate_bedrock, feature_type
                        )
                    }
                ],
                "recommended_intermediate_java": intermediate_java,
                "total_compatibility_score": (
                    (first_compat.compatibility_score if first_compat else 0.0) * 
                    final_compatibility.compatibility_score
                ) / 2.0
            }
            
        except Exception as e:
            logger.error(f"Error finding optimal conversion path: {e}")
            return {
                "path_type": "failed",
                "error": str(e),
                "message": "Failed to find optimal conversion path"
            }
    
    async def _get_relevant_patterns(
        self,
        db: AsyncSession,
        version: str,
        feature_type: str
    ) -> List[Dict[str, Any]]:
        """Get relevant conversion patterns for version and feature type."""
        try:
            patterns = await ConversionPatternCRUD.get_by_version(
                db, minecraft_version=version, 
                validation_status="validated"
            )
            
            # Filter by feature type
            relevant = []
            for pattern in patterns:
                if feature_type in pattern.tags or pattern.name.lower().contains(feature_type.lower()):
                    relevant.append({
                        "id": pattern.id,
                        "name": pattern.name,
                        "description": pattern.description,
                        "success_rate": pattern.success_rate,
                        "tags": pattern.tags
                    })
            
            return relevant
            
        except Exception as e:
            logger.error(f"Error getting relevant patterns: {e}")
            return []
    
    async def _get_sorted_java_versions(self, db: AsyncSession) -> List[str]:
        """Get all Java versions sorted by release date."""
        # In a real implementation, this would sort by actual release dates
        # For now, return a predefined list
        return [
            "1.14.4", "1.15.2", "1.16.5", "1.17.1", "1.18.2", 
            "1.19.4", "1.20.1", "1.20.6", "1.21.0"
        ]
    
    async def _get_sorted_bedrock_versions(self, db: AsyncSession) -> List[str]:
        """Get all Bedrock versions sorted by release date."""
        # In a real implementation, this would sort by actual release dates
        # For now, return a predefined list
        return [
            "1.14.0", "1.16.0", "1.17.0", "1.18.0", "1.19.0", 
            "1.20.0", "1.20.60", "1.21.0"
        ]
    
    async def _find_best_bedrock_match(
        self,
        db: AsyncSession,
        java_version: str,
        feature_type: str
    ) -> Optional[str]:
        """Find best matching Bedrock version for Java version and feature."""
        try:
            # Get all Bedrock versions
            bedrock_versions = await self._get_sorted_bedrock_versions(db)
            
            # Check compatibility for each
            best_version = None
            best_score = 0.0
            
            for bv in bedrock_versions:
                compat = await self.get_compatibility(java_version, bv, db)
                
                if compat:
                    # Check if feature is supported
                    features = compat.features_supported
                    feature_supported = any(
                        f.get("type") == feature_type for f in features
                    )
                    
                    if feature_supported and compat.compatibility_score > best_score:
                        best_score = compat.compatibility_score
                        best_version = bv
            
            return best_version
            
        except Exception as e:
            logger.error(f"Error finding best Bedrock match: {e}")
            return None
    
    async def _generate_direct_migration_steps(
        self,
        from_java_version: str,
        to_bedrock_version: str,
        features: List[str],
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Generate steps for direct migration."""
        return [
            {
                "step": 1,
                "title": "Backup and Prepare",
                "description": f"Create backup of your Java {from_java_version} mod and prepare development environment.",
                "actions": [
                    "Backup original mod files",
                    "Set up Bedrock development environment",
                    "Install required Bedrock development tools"
                ],
                "estimated_time": "30-60 minutes"
            },
            {
                "step": 2,
                "title": "Feature Analysis",
                "description": f"Analyze the features you want to convert: {', '.join(features)}",
                "actions": [
                    "Document current feature implementations",
                    "Identify conversion requirements",
                    "Check for Bedrock equivalents"
                ],
                "estimated_time": "60-120 minutes"
            },
            {
                "step": 3,
                "title": "Conversion Implementation",
                "description": f"Convert Java features to Bedrock {to_bedrock_version} implementation",
                "actions": [
                    "Implement Bedrock behavior files",
                    "Create Bedrock resource definitions",
                    "Convert Java code logic to Bedrock components"
                ],
                "estimated_time": "2-8 hours depending on complexity"
            },
            {
                "step": 4,
                "title": "Testing and Validation",
                "description": f"Test converted mod in Bedrock {to_bedrock_version} environment",
                "actions": [
                    "Functional testing of all features",
                    "Cross-platform compatibility testing",
                    "Performance optimization"
                ],
                "estimated_time": "1-3 hours"
            }
        ]
    
    async def _generate_gradual_migration_steps(
        self,
        from_java_version: str,
        to_bedrock_version: str,
        features: List[str],
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Generate steps for gradual migration through intermediate versions."""
        return [
            {
                "step": 1,
                "title": "Phase 1: Compatibility Analysis",
                "description": f"Analyze compatibility between Java {from_java_version} and target Bedrock {to_bedrock_version}",
                "actions": [
                    "Review compatibility matrix for version mapping",
                    "Identify features requiring gradual conversion",
                    "Plan intermediate version targets"
                ],
                "estimated_time": "60-90 minutes"
            },
            {
                "step": 2,
                "title": "Phase 2: Intermediate Conversion",
                "description": "Convert features to intermediate compatible versions",
                "actions": [
                    "Convert to intermediate Java version if needed",
                    "Implement compatibility layer functions",
                    "Create feature flags for gradual rollout"
                ],
                "estimated_time": "3-6 hours"
            },
            {
                "step": 3,
                "title": "Phase 3: Target Version Conversion",
                "description": f"Complete conversion to target Bedrock {to_bedrock_version}",
                "actions": [
                    "Remove intermediate compatibility layers",
                    "Finalize Bedrock-specific implementations",
                    "Optimize for target version features"
                ],
                "estimated_time": "2-4 hours"
            },
            {
                "step": 4,
                "title": "Phase 4: Validation and Cleanup",
                "description": "Final testing and cleanup of gradual migration process",
                "actions": [
                    "Comprehensive testing across all phases",
                    "Remove temporary compatibility code",
                    "Documentation updates for final version"
                ],
                "estimated_time": "1-2 hours"
            }
        ]
    
    def _load_default_compatibility(self) -> Dict[str, Any]:
        """Load default compatibility data for initialization."""
        return {
            "1.19.4": {
                "1.19.50": {
                    "score": 0.85,
                    "features": ["entities", "blocks", "items", "recipes"],
                    "patterns": ["entity_behavior", "block_states", "item_components"],
                    "issues": ["animation_differences", "particle_effects"]
                },
                "1.20.0": {
                    "score": 0.75,
                    "features": ["entities", "blocks", "items"],
                    "patterns": ["entity_behavior", "block_states", "item_components"],
                    "issues": ["new_features_missing"]
                }
            },
            "1.20.1": {
                "1.20.0": {
                    "score": 0.90,
                    "features": ["entities", "blocks", "items", "recipes", "biomes"],
                    "patterns": ["entity_behavior", "block_states", "item_components"],
                    "issues": []
                },
                "1.20.60": {
                    "score": 0.80,
                    "features": ["entities", "blocks", "items", "recipes"],
                    "patterns": ["entity_behavior", "block_states", "item_components"],
                    "issues": ["cherry_features_missing"]
                }
            }
        }


# Singleton instance
version_compatibility_service = VersionCompatibilityService()
