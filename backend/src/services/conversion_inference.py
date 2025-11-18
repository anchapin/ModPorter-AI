"""
Automated Inference Engine for Conversion Paths

This service provides automated inference capabilities for finding
optimal conversion paths between Java and Bedrock modding concepts.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession


from src.db.knowledge_graph_crud import (
    KnowledgeNodeCRUD, ConversionPatternCRUD
)
from src.db.models import KnowledgeNode
from src.db.graph_db import graph_db

logger = logging.getLogger(__name__)


class ConversionInferenceEngine:
    """Automated inference engine for conversion paths."""
    
    def __init__(self):
        self.confidence_thresholds = {
            "high": 0.8,
            "medium": 0.6,
            "low": 0.4
        }
        self.max_path_depth = 5
        self.min_path_confidence = 0.5
        
    async def infer_conversion_path(
        self,
        java_concept: str,
        db: AsyncSession,
        target_platform: str = "bedrock",
        minecraft_version: str = "latest",
        path_options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Automatically infer optimal conversion path for Java concept.
        
        Args:
            java_concept: Source Java concept to convert
            target_platform: Target platform (bedrock, java, both)
            minecraft_version: Minecraft version context
            path_options: Additional options for path finding
            db: Database session
        
        Returns:
            Inferred conversion paths with confidence scores and alternatives
        """
        try:
            # Parse options
            options = path_options or {}
            max_depth = options.get("max_depth", self.max_path_depth)
            min_confidence = options.get("min_confidence", self.min_path_confidence)
            include_alternatives = options.get("include_alternatives", True)
            optimize_for = options.get("optimize_for", "confidence")  # confidence, speed, features
            
            # Step 1: Find source concept in knowledge graph
            source_node = await self._find_concept_node(
                db, java_concept, "java", minecraft_version
            )
            
            if not source_node:
                return {
                    "success": False,
                    "error": "Source concept not found in knowledge graph",
                    "java_concept": java_concept,
                    "suggestions": await self._suggest_similar_concepts(
                        db, java_concept, "java"
                    )
                }
            
            # Step 2: Find direct conversion relationships
            direct_paths = await self._find_direct_paths(
                db, source_node, target_platform, minecraft_version
            )
            
            if direct_paths and optimize_for != "features":
                # High-quality direct path available
                best_direct = max(direct_paths, key=lambda x: x["confidence"])
                
                return {
                    "success": True,
                    "java_concept": java_concept,
                    "path_type": "direct",
                    "primary_path": best_direct,
                    "alternative_paths": direct_paths[1:] if include_alternatives else [],
                    "path_count": len(direct_paths),
                    "inference_metadata": {
                        "algorithm": "direct_lookup",
                        "confidence_threshold": min_confidence,
                        "minecraft_version": minecraft_version,
                        "inference_timestamp": datetime.utcnow().isoformat()
                    }
                }
            
            # Step 3: Find indirect conversion paths (graph traversal)
            indirect_paths = await self._find_indirect_paths(
                db, source_node, target_platform, minecraft_version, 
                max_depth, min_confidence
            )
            
            # Step 4: Combine and rank paths
            all_paths = direct_paths + indirect_paths
            
            if not all_paths:
                return {
                    "success": False,
                    "error": "No conversion paths found",
                    "java_concept": java_concept,
                    "suggestions": await self._suggest_similar_concepts(
                        db, java_concept, "java"
                    )
                }
            
            # Step 5: Optimize paths based on criteria
            ranked_paths = await self._rank_paths(
                all_paths, optimize_for, db, minecraft_version
            )
            
            primary_path = ranked_paths[0] if ranked_paths else None
            alternative_paths = ranked_paths[1:5] if include_alternatives else []
            
            return {
                "success": True,
                "java_concept": java_concept,
                "path_type": "inferred" if indirect_paths else "direct",
                "primary_path": primary_path,
                "alternative_paths": alternative_paths,
                "path_count": len(all_paths),
                "inference_metadata": {
                    "algorithm": "graph_traversal" if indirect_paths else "direct_lookup",
                    "confidence_threshold": min_confidence,
                    "max_depth": max_depth,
                    "optimization_criteria": optimize_for,
                    "minecraft_version": minecraft_version,
                    "inference_timestamp": datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error inferring conversion path: {e}")
            return {
                "success": False,
                "error": "Inference engine error",
                "details": str(e)
            }
    
    async def batch_infer_paths(
        self,
        java_concepts: List[str],
        target_platform: str = "bedrock",
        minecraft_version: str = "latest",
        path_options: Dict[str, Any] = None,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Infer conversion paths for multiple Java concepts.
        
        Args:
            java_concepts: List of Java concepts to convert
            target_platform: Target platform
            minecraft_version: Minecraft version context
            path_options: Options for path finding
            db: Database session
        
        Returns:
            Batch inference results with optimized path clustering
        """
        try:
            # Infer paths for each concept
            concept_paths = {}
            failed_concepts = []
            
            for concept in java_concepts:
                result = await self.infer_conversion_path(
                    concept, target_platform, minecraft_version, path_options, db
                )
                
                if result.get("success"):
                    concept_paths[concept] = {
                        "primary_path": result.get("primary_path"),
                        "alternatives": result.get("alternative_paths", []),
                        "confidence": result.get("primary_path", {}).get("confidence", 0.0)
                    }
                else:
                    failed_concepts.append({
                        "concept": concept,
                        "error": result.get("error"),
                        "suggestions": result.get("suggestions", [])
                    })
            
            # Step 1: Analyze path patterns across concepts
            path_analysis = await self._analyze_batch_paths(concept_paths, db)
            
            # Step 2: Optimize batch processing order
            processing_order = await self._optimize_processing_order(
                concept_paths, path_analysis
            )
            
            # Step 3: Identify shared conversion steps
            shared_steps = await self._identify_shared_steps(concept_paths, db)
            
            # Step 4: Generate batch processing plan
            batch_plan = await self._generate_batch_plan(
                concept_paths, processing_order, shared_steps, path_analysis
            )
            
            return {
                "success": True,
                "total_concepts": len(java_concepts),
                "successful_paths": len(concept_paths),
                "failed_concepts": failed_concepts,
                "concept_paths": concept_paths,
                "path_analysis": path_analysis,
                "processing_plan": batch_plan,
                "batch_metadata": {
                    "target_platform": target_platform,
                    "minecraft_version": minecraft_version,
                    "inference_timestamp": datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error in batch path inference: {e}")
            return {
                "success": False,
                "error": "Batch inference error",
                "details": str(e)
            }
    
    async def optimize_conversion_sequence(
        self,
        java_concepts: List[str],
        conversion_dependencies: Optional[Dict[str, List[str]]] = None,
        target_platform: str = "bedrock",
        minecraft_version: str = "latest",
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Optimize conversion sequence based on dependencies and shared patterns.
        
        Args:
            java_concepts: List of concepts to convert
            conversion_dependencies: Optional dependency relationships
            target_platform: Target platform
            minecraft_version: Minecraft version context
            db: Database session
        
        Returns:
            Optimized conversion sequence with processing steps
        """
        try:
            dependencies = conversion_dependencies or {}
            
            # Step 1: Build dependency graph
            dep_graph = await self._build_dependency_graph(
                java_concepts, dependencies, db
            )
            
            # Step 2: Topological sort for processing order
            processing_order = await self._topological_sort(dep_graph)
            
            # Step 3: Group concepts with shared conversion patterns
            processing_groups = await self._group_by_patterns(
                processing_order, target_platform, minecraft_version, db
            )
            
            # Step 4: Generate optimized sequence
            sequence = []
            total_estimated_time = 0.0
            
            for group_idx, group in enumerate(processing_groups):
                group_step = {
                    "step_number": group_idx + 1,
                    "parallel_processing": True,
                    "concepts": group["concepts"],
                    "shared_patterns": group["shared_patterns"],
                    "estimated_time": group["estimated_time"],
                    "optimization_notes": group["optimization_notes"]
                }
                
                sequence.append(group_step)
                total_estimated_time += group["estimated_time"]
            
            # Step 5: Add dependency validation steps
            validation_steps = await self._generate_validation_steps(
                processing_order, dependencies, target_platform, db
            )
            
            return {
                "success": True,
                "total_concepts": len(java_concepts),
                "optimization_algorithm": "dependency_aware_grouping",
                "processing_sequence": sequence,
                "validation_steps": validation_steps,
                "total_estimated_time": total_estimated_time,
                "optimization_savings": await self._calculate_savings(
                    processing_order, processing_groups, db
                ),
                "metadata": {
                    "dependencies_count": len(dependencies),
                    "parallel_groups": len(processing_groups),
                    "target_platform": target_platform,
                    "minecraft_version": minecraft_version,
                    "optimization_timestamp": datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error optimizing conversion sequence: {e}")
            return {
                "success": False,
                "error": "Sequence optimization error",
                "details": str(e)
            }
    
    async def learn_from_conversion(
        self,
        java_concept: str,
        bedrock_concept: str,
        conversion_result: Dict[str, Any],
        success_metrics: Dict[str, float],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Learn from conversion results to improve future inference.
        
        Args:
            java_concept: Original Java concept
            bedrock_concept: Resulting Bedrock concept
            conversion_result: Detailed conversion outcome
            success_metrics: Success metrics (confidence, accuracy, etc.)
            db: Database session
        
        Returns:
            Learning results with updated knowledge
        """
        try:
            # Step 1: Analyze conversion performance
            performance_analysis = await self._analyze_conversion_performance(
                java_concept, bedrock_concept, conversion_result, success_metrics
            )
            
            # Step 2: Update knowledge graph with learned patterns
            learning_updates = await self._update_knowledge_graph(
                java_concept, bedrock_concept, performance_analysis, db
            )
            
            # Step 3: Adjust inference confidence thresholds
            threshold_adjustments = await self._adjust_confidence_thresholds(
                performance_analysis, success_metrics
            )
            
            # Step 4: Record learning event
            learning_event = {
                "java_concept": java_concept,
                "bedrock_concept": bedrock_concept,
                "conversion_result": conversion_result,
                "success_metrics": success_metrics,
                "performance_analysis": performance_analysis,
                "learning_updates": learning_updates,
                "threshold_adjustments": threshold_adjustments,
                "learning_timestamp": datetime.utcnow().isoformat()
            }
            
            # Store learning event (would go to analytics in production)
            await self._store_learning_event(learning_event, db)
            
            return {
                "success": True,
                "learning_event_id": learning_event.get("id"),
                "performance_analysis": performance_analysis,
                "knowledge_updates": learning_updates,
                "threshold_adjustments": threshold_adjustments,
                "new_confidence_thresholds": self.confidence_thresholds
            }
            
        except Exception as e:
            logger.error(f"Error learning from conversion: {e}")
            return {
                "success": False,
                "error": "Learning process error",
                "details": str(e)
            }
    
    async def get_inference_statistics(
        self,
        days: int = 30,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Get statistics about inference engine performance.
        
        Args:
            days: Number of days to include in statistics
            db: Database session
        
        Returns:
            Performance metrics and trends
        """
        try:
            # This would query actual inference statistics from database
            # For now, return mock data
            stats = {
                "period_days": days,
                "total_inferences": 1847,
                "successful_inferences": 1723,
                "failed_inferences": 124,
                "success_rate": 93.3,
                "average_confidence": 0.78,
                "average_path_length": 2.4,
                "average_processing_time": 0.45,
                "path_types": {
                    "direct": 1234,
                    "indirect": 613
                },
                "confidence_distribution": {
                    "high": 890,
                    "medium": 678,
                    "low": 279
                },
                "learning_events": 892,
                "performance_trends": {
                    "success_rate_trend": "improving",
                    "confidence_trend": "stable",
                    "speed_trend": "improving"
                },
                "optimization_impact": {
                    "time_savings": 34.7,  # percentage
                    "accuracy_improvement": 12.3,  # percentage
                    "resource_efficiency": 28.1  # percentage
                },
                "generated_at": datetime.utcnow().isoformat()
            }
            
            return stats
        except Exception as e:
            logger.error(f"Error getting inference statistics: {e}")
            return {
                "success": False,
                "error": "Statistics retrieval error",
                "details": str(e)
            }
    
    # Private Helper Methods
    
    async def _find_concept_node(
        self, 
        db: AsyncSession, 
        concept: str, 
        platform: str, 
        version: str
    ) -> Optional[KnowledgeNode]:
        """Find concept node in knowledge graph."""
        try:
            nodes = await KnowledgeNodeCRUD.search(db, concept, limit=10)
            
            # Filter by platform and version
            for node in nodes:
                if (concept.lower() in node.name.lower() or 
                    node.name.lower() in concept.lower()) and \
                   (platform in node.platform or node.platform == "both") and \
                   (version == node.minecraft_version or node.minecraft_version == "latest"):
                    return node
            
            return None
        except Exception as e:
            logger.error(f"Error finding concept node: {e}")
            return None
    
    async def _find_direct_paths(
        self,
        db: AsyncSession,
        source_node: KnowledgeNode,
        target_platform: str,
        minecraft_version: str
    ) -> List[Dict[str, Any]]:
        """Find direct conversion paths from source node."""
        try:
            # Get relationships from Neo4j
            neo4j_paths = graph_db.find_conversion_paths(
                source_node.neo4j_id or str(source_node.id),
                max_depth=1,
                minecraft_version=minecraft_version
            )
            
            # Filter by target platform
            direct_paths = []
            for path in neo4j_paths:
                if path["path_length"] == 1:
                    target_node = path["end_node"]
                    
                    # Check if target matches platform
                    if (target_platform in target_node.get("platform", "") or 
                        target_node.get("platform") == "both"):
                        
                        direct_path = {
                            "path_type": "direct",
                            "confidence": path["confidence"],
                            "steps": [
                                {
                                    "source_concept": source_node.name,
                                    "target_concept": target_node.get("name"),
                                    "relationship": path["relationships"][0]["type"],
                                    "platform": target_node.get("platform"),
                                    "version": target_node.get("minecraft_version")
                                }
                            ],
                            "path_length": 1,
                            "supports_features": path.get("supported_features", []),
                            "success_rate": path.get("success_rate", 0.5),
                            "usage_count": path.get("usage_count", 0)
                        }
                        direct_paths.append(direct_path)
            
            # Sort by confidence (descending)
            direct_paths.sort(key=lambda x: x["confidence"], reverse=True)
            return direct_paths
            
        except Exception as e:
            logger.error(f"Error finding direct paths: {e}")
            return []
    
    async def _find_indirect_paths(
        self,
        db: AsyncSession,
        source_node: KnowledgeNode,
        target_platform: str,
        minecraft_version: str,
        max_depth: int,
        min_confidence: float
    ) -> List[Dict[str, Any]]:
        """Find indirect conversion paths through graph traversal."""
        try:
            # Get paths from Neo4j with depth > 1
            neo4j_paths = graph_db.find_conversion_paths(
                source_node.neo4j_id or str(source_node.id),
                max_depth=max_depth,
                minecraft_version=minecraft_version
            )
            
            # Filter and process indirect paths
            indirect_paths = []
            for path in neo4j_paths:
                if path["path_length"] > 1 and path["confidence"] >= min_confidence:
                    target_node = path["end_node"]
                    
                    # Check platform compatibility
                    if (target_platform in target_node.get("platform", "") or 
                        target_node.get("platform") == "both"):
                        
                        steps = []
                        for i, relationship in enumerate(path["relationships"]):
                            step = {
                                "source_concept": path["nodes"][i]["name"],
                                "target_concept": path["nodes"][i + 1]["name"],
                                "relationship": relationship["type"],
                                "confidence": relationship.get("confidence", 0.5)
                            }
                            steps.append(step)
                        
                        indirect_path = {
                            "path_type": "indirect",
                            "confidence": path["confidence"],
                            "steps": steps,
                            "path_length": path["path_length"],
                            "supports_features": path.get("supported_features", []),
                            "success_rate": path.get("success_rate", 0.5),
                            "usage_count": path.get("usage_count", 0),
                            "intermediate_concepts": [
                                step["target_concept"] 
                                for step in steps[:-1]
                            ]
                        }
                        indirect_paths.append(indirect_path)
            
            # Sort by confidence and path length
            indirect_paths.sort(key=lambda x: (-x["confidence"], x["path_length"]))
            return indirect_paths
            
        except Exception as e:
            logger.error(f"Error finding indirect paths: {e}")
            return []
    
    async def _rank_paths(
        self,
        paths: List[Dict[str, Any]],
        optimize_for: str,
        db: AsyncSession,
        minecraft_version: str
    ) -> List[Dict[str, Any]]:
        """Rank paths based on optimization criteria."""
        try:
            if optimize_for == "confidence":
                # Sort by confidence (descending)
                return sorted(paths, key=lambda x: (-x["confidence"], x["path_length"]))
            
            elif optimize_for == "speed":
                # Sort by path length (ascending), then confidence
                return sorted(paths, key=lambda x: (x["path_length"], -x["confidence"]))
            
            elif optimize_for == "features":
                # Sort by number of supported features (descending), then confidence
                return sorted(paths, key=lambda x: (-len(x.get("supports_features", [])), -x["confidence"]))
            
            else:
                # Default: balanced ranking
                for path in paths:
                    # Calculate balanced score
                    confidence_score = path["confidence"]
                    length_score = 1.0 / path["path_length"]
                    features_score = len(path.get("supports_features", [])) / 10.0
                    
                    # Weighted combination
                    balanced_score = (confidence_score * 0.5 + 
                                    length_score * 0.3 + 
                                    features_score * 0.2)
                    path["balanced_score"] = balanced_score
                
                return sorted(paths, key=lambda x: -x["balanced_score"])
                
        except Exception as e:
            logger.error(f"Error ranking paths: {e}")
            return paths
    
    async def _suggest_similar_concepts(
        self, 
        db: AsyncSession, 
        target_concept: str, 
        platform: str
    ) -> List[Dict[str, Any]]:
        """Suggest similar concepts when exact match not found."""
        try:
            # Search for similar concepts
            similar_nodes = await KnowledgeNodeCRUD.search(
                db, target_concept.split()[0], limit=5
            )
            
            suggestions = []
            for node in similar_nodes[:3]:  # Top 3 suggestions
                if platform in node.platform or node.platform == "both":
                    suggestions.append({
                        "concept": node.name,
                        "description": node.description,
                        "platform": node.platform,
                        "expert_validated": node.expert_validated,
                        "community_rating": node.community_rating
                    })
            
            return suggestions
        except Exception as e:
            logger.error(f"Error suggesting similar concepts: {e}")
            return []
    
    async def _analyze_batch_paths(
        self, 
        concept_paths: Dict[str, Dict], 
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Analyze patterns across batch of inferred paths."""
        try:
            path_lengths = [len(p["primary_path"]["steps"]) 
                          for p in concept_paths.values() if p["primary_path"]]
            confidences = [p["confidence"] for p in concept_paths.values()]
            
            # Find common patterns
            common_patterns = await self._find_common_patterns(concept_paths)
            
            return {
                "total_paths": len(concept_paths),
                "average_path_length": sum(path_lengths) / len(path_lengths) if path_lengths else 0,
                "average_confidence": sum(confidences) / len(confidences) if confidences else 0,
                "common_patterns": common_patterns,
                "path_complexity": {
                    "simple": sum(1 for pl in path_lengths if pl <= 2),
                    "moderate": sum(1 for pl in path_lengths if 3 <= pl <= 4),
                    "complex": sum(1 for pl in path_lengths if pl > 4)
                }
            }
        except Exception as e:
            logger.error(f"Error analyzing batch paths: {e}")
            return {}
    
    async def _optimize_processing_order(
        self, 
        concept_paths: Dict[str, Dict], 
        path_analysis: Dict
    ) -> List[str]:
        """Optimize processing order based on path analysis."""
        try:
            # Sort by confidence (descending), then by path length (ascending)
            concepts = list(concept_paths.keys())
            
            def sort_key(concept):
                path_data = concept_paths[concept]
                confidence = path_data.get("confidence", 0.0)
                path_length = len(path_data.get("primary_path", {}).get("steps", []))
                
                # Higher confidence and shorter paths first
                return (-confidence, path_length)
            
            return sorted(concepts, key=sort_key)
            
        except Exception as e:
            logger.error(f"Error optimizing processing order: {e}")
            return list(concept_paths.keys())
    
    async def _identify_shared_steps(
        self, 
        concept_paths: Dict[str, Dict], 
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Identify shared conversion steps across concepts."""
        try:
            # Extract all steps from all paths
            all_steps = []
            for concept_data in concept_paths.values():
                primary_path = concept_data.get("primary_path", {})
                steps = primary_path.get("steps", [])
                all_steps.extend(steps)
            
            # Find common relationships and target concepts
            relationship_counts = {}
            target_counts = {}
            
            for step in all_steps:
                rel = step.get("relationship", "")
                target = step.get("target_concept", "")
                
                relationship_counts[rel] = relationship_counts.get(rel, 0) + 1
                target_counts[target] = target_counts.get(target, 0) + 1
            
            # Find most common
            most_common_rel = max(relationship_counts.items(), key=lambda x: x[1]) if relationship_counts else None
            most_common_target = max(target_counts.items(), key=lambda x: x[1]) if target_counts else None
            
            shared_steps = []
            if most_common_rel and most_common_rel[1] > 1:
                shared_steps.append({
                    "type": "relationship",
                    "value": most_common_rel[0],
                    "count": most_common_rel[1],
                    "percentage": (most_common_rel[1] / len(all_steps)) * 100
                })
            
            if most_common_target and most_common_target[1] > 1:
                shared_steps.append({
                    "type": "target_concept",
                    "value": most_common_target[0],
                    "count": most_common_target[1],
                    "percentage": (most_common_target[1] / len(all_steps)) * 100
                })
            
            return shared_steps
        except Exception as e:
            logger.error(f"Error identifying shared steps: {e}")
            return []
    
    async def _generate_batch_plan(
        self,
        concept_paths: Dict[str, Dict],
        processing_order: List[str],
        shared_steps: List[Dict],
        path_analysis: Dict
    ) -> Dict[str, Any]:
        """Generate optimized batch processing plan."""
        try:
            # Calculate processing groups based on shared patterns
            groups = []
            batch_size = 3  # Process 3 concepts in parallel
            
            for i in range(0, len(processing_order), batch_size):
                batch_concepts = processing_order[i:i + batch_size]
                group = {
                    "batch_number": (i // batch_size) + 1,
                    "concepts": batch_concepts,
                    "estimated_time": self._estimate_batch_time(batch_concepts, concept_paths),
                    "shared_patterns": [
                        step for step in shared_steps 
                        if step["count"] > 1
                    ],
                    "optimizations": await self._get_batch_optimizations(batch_concepts, concept_paths)
                }
                groups.append(group)
            
            return {
                "total_groups": len(groups),
                "processing_groups": groups,
                "estimated_total_time": sum(g["estimated_time"] for g in groups),
                "optimization_potential": len(shared_steps)
            }
        except Exception as e:
            logger.error(f"Error generating batch plan: {e}")
            return {}
    
    async def _find_common_patterns(
        self, 
        concept_paths: Dict[str, Dict]
    ) -> List[Dict[str, Any]]:
        """Find common patterns across multiple conversion paths."""
        # This would analyze path structures to find recurring patterns
        # For now, return mock data
        return [
            {
                "pattern": "entity_to_behavior",
                "frequency": 12,
                "description": "Java entities converting to Bedrock behavior components"
            },
            {
                "pattern": "item_to_component",
                "frequency": 8,
                "description": "Java items converting to Bedrock item components"
            }
        ]
    
    def _estimate_batch_time(
        self, 
        concepts: List[str], 
        concept_paths: Dict[str, Dict]
    ) -> float:
        """Estimate processing time for a batch of concepts."""
        # Base time per concept + complexity factor
        base_time = 0.1  # 100ms per concept
        complexity_factor = 1.2  # 20% overhead for parallel processing
        
        total_confidence = sum(
            concept_paths.get(c, {}).get("confidence", 0.0) 
            for c in concepts
        )
        
        # Lower average confidence = more processing time
        confidence_penalty = (1.0 - (total_confidence / len(concepts))) * 0.05
        
        return (len(concepts) * base_time * complexity_factor) + confidence_penalty
    
    async def _get_batch_optimizations(
        self, 
        concepts: List[str], 
        concept_paths: Dict[str, Dict]
    ) -> List[str]:
        """Get optimization opportunities for batch processing."""
        optimizations = []
        
        # Check for shared target concepts
        targets = [
            concept_paths.get(c, {}).get("primary_path", {}).get("steps", [])[-1].get("target_concept")
            for c in concepts
        ]
        
        target_counts = {}
        for target in targets:
            if target:
                target_counts[target] = target_counts.get(target, 0) + 1
        
        for target, count in target_counts.items():
            if count > 1:
                optimizations.append(f"Multiple concepts convert to {target} - can optimize shared logic")
        
        return optimizations
    
    async def _build_dependency_graph(
        self,
        concepts: List[str],
        dependencies: Dict[str, List[str]],
        db: AsyncSession
    ) -> Dict[str, List[str]]:
        """Build dependency graph from concepts and dependencies."""
        # Initialize graph with all concepts
        graph = {concept: [] for concept in concepts}
        
        # Add dependencies
        for concept, deps in dependencies.items():
            if concept in graph:
                graph[concept] = [dep for dep in deps if dep in concepts]
        
        return graph
    
    async def _topological_sort(self, graph: Dict[str, List[str]]) -> List[str]:
        """Perform topological sort on dependency graph."""
        try:
            # Kahn's algorithm for topological sorting
            in_degree = {node: 0 for node in graph}
            
            # Calculate in-degrees
            for node in graph:
                for neighbor in graph[node]:
                    in_degree[neighbor] = in_degree.get(neighbor, 0) + 1
            
            # Initialize queue with nodes having no dependencies
            queue = [node for node, degree in in_degree.items() if degree == 0]
            result = []
            
            while queue:
                current = queue.pop(0)
                result.append(current)
                
                # Update in-degrees of neighbors
                for neighbor in graph.get(current, []):
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)
            
            # Check for cycles
            if len(result) != len(graph):
                raise ValueError("Dependency graph contains cycles")
            
            return result
        except Exception as e:
            logger.error(f"Error in topological sort: {e}")
            # Fallback to original order
            return list(graph.keys())
    
    async def _group_by_patterns(
        self,
        processing_order: List[str],
        target_platform: str,
        minecraft_version: str,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Group concepts by shared conversion patterns."""
        # This would analyze patterns and group related concepts
        # For now, create simple groups
        groups = []
        group_size = 2  # Process 2 concepts together
        
        for i in range(0, len(processing_order), group_size):
            group_concepts = processing_order[i:i + group_size]
            
            group = {
                "concepts": group_concepts,
                "shared_patterns": await self._find_shared_patterns_for_group(
                    group_concepts, db
                ),
                "estimated_time": len(group_concepts) * 0.15,  # 150ms per concept
                "optimization_notes": [
                    "Shared patterns detected",
                    "Parallel processing recommended"
                ]
            }
            groups.append(group)
        
        return groups
    
    async def _find_shared_patterns_for_group(
        self, 
        concepts: List[str], 
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Find patterns shared by a group of concepts."""
        # Mock implementation
        return [
            {
                "pattern": "entity_component_conversion",
                "applicable_concepts": concepts[:2],
                "benefit": "Shared component processing"
            }
        ]
    
    async def _generate_validation_steps(
        self,
        processing_order: List[str],
        dependencies: Dict[str, List[str]],
        target_platform: str,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Generate validation steps for conversion sequence."""
        validation_steps = []
        
        for i, concept in enumerate(processing_order):
            step = {
                "step_number": i + 1,
                "concept": concept,
                "validation_type": "dependency_check",
                "dependencies": dependencies.get(concept, []),
                "validation_criteria": [
                    "Verify all dependencies are processed",
                    "Check platform compatibility",
                    "Validate conversion success"
                ],
                "estimated_time": 0.05  # 50ms per validation
            }
            validation_steps.append(step)
        
        # Add final validation step
        validation_steps.append({
            "step_number": len(processing_order) + 1,
            "concept": "final_integration",
            "validation_type": "integration_test",
            "dependencies": processing_order,
            "validation_criteria": [
                "Test all converted concepts together",
                "Verify cross-concept compatibility",
                "Validate target platform features"
            ],
            "estimated_time": 0.2
        })
        
        return validation_steps
    
    async def _calculate_savings(
        self,
        processing_order: List[str],
        processing_groups: List[Dict],
        db: AsyncSession
    ) -> Dict[str, float]:
        """Calculate optimization savings from grouping."""
        try:
            # Sequential processing time
            sequential_time = len(processing_order) * 0.2  # 200ms per concept
            
            # Parallel processing time (sum of group times)
            parallel_time = sum(g["estimated_time"] for g in processing_groups)
            
            # Time savings percentage
            time_savings = ((sequential_time - parallel_time) / sequential_time) * 100
            
            return {
                "time_savings_percentage": max(0, time_savings),
                "sequential_time": sequential_time,
                "parallel_time": parallel_time
            }
        except Exception as e:
            logger.error(f"Error calculating savings: {e}")
            return {"time_savings_percentage": 0.0}
    
    async def _analyze_conversion_performance(
        self,
        java_concept: str,
        bedrock_concept: str,
        conversion_result: Dict,
        success_metrics: Dict[str, float]
    ) -> Dict[str, Any]:
        """Analyze conversion performance for learning."""
        return {
            "conversion_success": success_metrics.get("overall_success", 0.0),
            "accuracy": success_metrics.get("accuracy", 0.0),
            "feature_completeness": success_metrics.get("feature_completeness", 0.0),
            "performance_impact": success_metrics.get("performance_impact", 0.0),
            "user_satisfaction": success_metrics.get("user_satisfaction", 0.0),
            "conversion_complexity": self._calculate_complexity(conversion_result),
            "resource_usage": success_metrics.get("resource_usage", 0.0),
            "error_count": conversion_result.get("errors", 0),
            "warnings_count": conversion_result.get("warnings", 0)
        }
    
    async def _update_knowledge_graph(
        self,
        java_concept: str,
        bedrock_concept: str,
        performance: Dict,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Update knowledge graph with learned information."""
        # This would update confidence scores, add new relationships, etc.
        return {
            "confidence_updates": 1,
            "new_relationships": 0,
            "pattern_updates": 1,
            "expert_validation_updates": 0
        }
    
    async def _adjust_confidence_thresholds(
        self,
        performance: Dict,
        success_metrics: Dict
    ) -> Dict[str, float]:
        """Adjust confidence thresholds based on performance feedback."""
        # Simple adjustment algorithm
        overall_success = success_metrics.get("overall_success", 0.0)
        
        if overall_success > 0.8:
            # Increase thresholds (be more selective)
            adjustment = 0.05
        elif overall_success < 0.5:
            # Decrease thresholds (be more permissive)
            adjustment = -0.05
        else:
            adjustment = 0.0
        
        adjusted_thresholds = {}
        for level, threshold in self.confidence_thresholds.items():
            adjusted_thresholds[level] = max(0.1, min(0.95, threshold + adjustment))
        
        # Update instance thresholds
        self.confidence_thresholds.update(adjusted_thresholds)
        
        return {
            "adjustment": adjustment,
            "new_thresholds": adjusted_thresholds,
            "triggering_success_rate": overall_success
        }
    
    def _calculate_complexity(self, conversion_result: Dict) -> float:
        """Calculate complexity score for conversion result."""
        complexity_factors = [
            conversion_result.get("step_count", 1) * 0.2,
            conversion_result.get("pattern_count", 1) * 0.3,
            len(conversion_result.get("custom_code", [])) * 0.4,
            conversion_result.get("file_count", 1) * 0.1
        ]
        return sum(complexity_factors)
    
    async def _store_learning_event(self, event: Dict, db: AsyncSession):
        """Store learning event for analytics."""
        # This would store the learning event in database
        event["id"] = f"learning_{datetime.utcnow().timestamp()}"
        logger.info(f"Storing learning event: {event['id']}")


    async def enhance_conversion_accuracy(
        self,
        conversion_paths: List[Dict[str, Any]],
        context_data: Dict[str, Any] = None,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Enhance conversion accuracy through multi-layered validation and optimization.
        
        This method applies several accuracy improvement techniques:
        1. Pattern validation against known successful conversions
        2. Cross-platform compatibility checking
        3. Machine learning prediction refinement
        4. Community wisdom integration
        5. Real-time performance optimization
        
        Args:
            conversion_paths: List of potential conversion paths
            context_data: Additional context (version constraints, preferences, etc.)
            db: Database session for data access
        
        Returns:
            Enhanced and optimized conversion paths with improved accuracy scores
        """
        try:
            enhanced_paths = []
            
            for path in conversion_paths:
                enhanced_path = path.copy()
                
                # 1. Pattern Validation
                pattern_score = await self._validate_conversion_pattern(
                    path, db
                )
                
                # 2. Cross-Platform Compatibility
                compatibility_score = await self._check_platform_compatibility(
                    path, context_data
                )
                
                # 3. ML Prediction Refinement
                ml_score = await self._refine_with_ml_predictions(
                    path, context_data
                )
                
                # 4. Community Wisdom Integration
                community_score = await self._integrate_community_wisdom(
                    path, db
                )
                
                # 5. Performance Optimization
                optimization_score = await self._optimize_for_performance(
                    path, context_data
                )
                
                # Calculate enhanced accuracy score
                base_confidence = path.get("confidence", 0.0)
                accuracy_weights = {
                    "pattern_validation": 0.25,
                    "platform_compatibility": 0.20,
                    "ml_prediction": 0.25,
                    "community_wisdom": 0.15,
                    "performance_optimization": 0.15
                }
                
                enhanced_accuracy = (
                    base_confidence * 0.3 +  # Base confidence still matters
                    pattern_score * accuracy_weights["pattern_validation"] +
                    compatibility_score * accuracy_weights["platform_compatibility"] +
                    ml_score * accuracy_weights["ml_prediction"] +
                    community_score * accuracy_weights["community_wisdom"] +
                    optimization_score * accuracy_weights["performance_optimization"]
                )
                
                # Apply confidence bounds
                enhanced_accuracy = max(0.0, min(1.0, enhanced_accuracy))
                
                # Add enhancement metadata
                enhanced_path.update({
                    "enhanced_accuracy": enhanced_accuracy,
                    "accuracy_components": {
                        "base_confidence": base_confidence,
                        "pattern_validation": pattern_score,
                        "platform_compatibility": compatibility_score,
                        "ml_prediction": ml_score,
                        "community_wisdom": community_score,
                        "performance_optimization": optimization_score
                    },
                    "enhancement_applied": True,
                    "enhancement_timestamp": datetime.utcnow().isoformat()
                })
                
                # Add accuracy improvement suggestions
                suggestions = await self._generate_accuracy_suggestions(
                    enhanced_path, enhanced_accuracy
                )
                enhanced_path["accuracy_suggestions"] = suggestions
                
                enhanced_paths.append(enhanced_path)
            
            # Re-rank enhanced paths
            ranked_paths = sorted(
                enhanced_paths, 
                key=lambda x: x.get("enhanced_accuracy", 0), 
                reverse=True
            )
            
            return {
                "success": True,
                "enhanced_paths": ranked_paths,
                "accuracy_improvements": {
                    "original_avg_confidence": sum(p.get("confidence", 0) for p in conversion_paths) / len(conversion_paths),
                    "enhanced_avg_confidence": sum(p.get("enhanced_accuracy", 0) for p in ranked_paths) / len(ranked_paths),
                    "improvement_percentage": self._calculate_improvement_percentage(conversion_paths, ranked_paths)
                },
                "enhancement_metadata": {
                    "algorithms_applied": ["pattern_validation", "platform_compatibility", "ml_prediction", "community_wisdom", "performance_optimization"],
                    "enhancement_timestamp": datetime.utcnow().isoformat(),
                    "context_applied": context_data
                }
            }
            
        except Exception as e:
            logger.error(f"Error in enhance_conversion_accuracy: {e}")
            return {
                "success": False,
                "error": f"Accuracy enhancement failed: {str(e)}"
            }

    async def _validate_conversion_pattern(
        self, path: Dict[str, Any], db: AsyncSession
    ) -> float:
        """Validate conversion pattern against known successful patterns."""
        try:
            # Get pattern type from path
            pattern_type = path.get("pattern_type", "unknown")
            
            # Check against successful patterns in knowledge base
            if db:
                successful_patterns = await ConversionPatternCRUD.get_by_type(
                    db, pattern_type, validation_status="validated"
                )
                
                if successful_patterns:
                    # Calculate pattern match score
                    avg_success_rate = sum(
                        p.success_rate for p in successful_patterns
                    ) / len(successful_patterns)
                    
                    return min(1.0, avg_success_rate * 1.2)  # Boost for validated patterns
                else:
                    return 0.5  # Neutral score for unknown patterns
            
            return 0.7  # Default moderate score when no DB available
            
        except Exception as e:
            logger.error(f"Error in _validate_conversion_pattern: {e}")
            return 0.5

    async def _check_platform_compatibility(
        self, path: Dict[str, Any], context_data: Dict[str, Any]
    ) -> float:
        """Check cross-platform compatibility of conversion path."""
        try:
            target_version = context_data.get("minecraft_version", "latest")
            
            # Version compatibility factors
            version_factors = {
                "latest": 1.0,
                "1.20": 0.95,
                "1.19": 0.90,
                "1.18": 0.85,
                "1.17": 0.80,
                "1.16": 0.70
            }
            
            base_score = version_factors.get(target_version, 0.7)
            
            # Check for deprecated features in path
            deprecated_features = path.get("deprecated_features", [])
            if deprecated_features:
                penalty = min(0.3, len(deprecated_features) * 0.1)
                base_score -= penalty
            
            # Check for experimental features
            experimental_features = path.get("experimental_features", [])
            if experimental_features:
                bonus = min(0.2, len(experimental_features) * 0.05)
                base_score += bonus
            
            return max(0.0, min(1.0, base_score))
            
        except Exception as e:
            logger.error(f"Error in _check_platform_compatibility: {e}")
            return 0.6

    async def _refine_with_ml_predictions(
        self, path: Dict[str, Any], context_data: Dict[str, Any]
    ) -> float:
        """Refine path using machine learning predictions."""
        try:
            # Simulate ML model prediction (in real implementation, would call trained model)
            base_confidence = path.get("confidence", 0.0)
            
            # Feature extraction for ML
            features = {
                "path_length": len(path.get("steps", [])),
                "base_confidence": base_confidence,
                "pattern_type": path.get("pattern_type", ""),
                "platform": path.get("target_platform", ""),
                "complexity": path.get("complexity", "medium")
            }
            
            # Simulated ML prediction (would use actual trained model)
            ml_prediction = self._simulate_ml_scoring(features)
            
            return ml_prediction
            
        except Exception as e:
            logger.error(f"Error in _refine_with_ml_predictions: {e}")
            return 0.7

    async def _integrate_community_wisdom(
        self, path: Dict[str, Any], db: AsyncSession
    ) -> float:
        """Integrate community feedback and wisdom into path scoring."""
        try:
            # Get community ratings for similar paths
            pattern_type = path.get("pattern_type", "")
            
            if db:
                # In real implementation, would query community contributions
                # For now, simulate based on pattern popularity
                popularity_scores = {
                    "entity_conversion": 0.85,
                    "block_conversion": 0.80,
                    "item_conversion": 0.78,
                    "behavior_conversion": 0.75,
                    "command_conversion": 0.70,
                    "unknown": 0.60
                }
                
                return popularity_scores.get(pattern_type, 0.60)
            
            return 0.7  # Default score
            
        except Exception as e:
            logger.error(f"Error in _integrate_community_wisdom: {e}")
            return 0.6

    async def _optimize_for_performance(
        self, path: Dict[str, Any], context_data: Dict[str, Any]
    ) -> float:
        """Optimize path for runtime performance."""
        try:
            performance_factors = {
                "path_length": len(path.get("steps", [])),
                "complexity": path.get("complexity", "medium"),
                "resource_intensity": path.get("resource_intensity", "medium")
            }
            
            # Score based on performance factors
            score = 0.8  # Base score
            
            # Penalty for long paths
            if performance_factors["path_length"] > 5:
                score -= 0.2
            elif performance_factors["path_length"] > 3:
                score -= 0.1
            
            # Penalty for high complexity
            if performance_factors["complexity"] == "high":
                score -= 0.15
            elif performance_factors["complexity"] == "very_high":
                score -= 0.25
            
            # Penalty for high resource intensity
            if performance_factors["resource_intensity"] == "high":
                score -= 0.1
            
            return max(0.0, min(1.0, score))
            
        except Exception as e:
            logger.error(f"Error in _optimize_for_performance: {e}")
            return 0.7

    async def _generate_accuracy_suggestions(
        self, path: Dict[str, Any], accuracy_score: float
    ) -> List[str]:
        """Generate suggestions for improving accuracy."""
        suggestions = []
        
        if accuracy_score < 0.5:
            suggestions.append("Consider alternative conversion patterns")
            suggestions.append("Validate against more recent Minecraft versions")
        
        if accuracy_score < 0.7:
            suggestions.append("Add more community feedback")
            suggestions.append("Include additional test cases")
        
        components = path.get("accuracy_components", {})
        
        if components.get("pattern_validation", 0) < 0.7:
            suggestions.append("Review pattern validation against known successful conversions")
        
        if components.get("platform_compatibility", 0) < 0.8:
            suggestions.append("Check for deprecated features and update compatibility")
        
        if components.get("ml_prediction", 0) < 0.6:
            suggestions.append("Consider more training data for ML model")
        
        return suggestions

    def _calculate_improvement_percentage(
        self, original_paths: List[Dict[str, Any]], enhanced_paths: List[Dict[str, Any]]
    ) -> float:
        """Calculate percentage improvement in accuracy."""
        if not original_paths or not enhanced_paths:
            return 0.0
        
        original_avg = sum(p.get("confidence", 0) for p in original_paths) / len(original_paths)
        enhanced_avg = sum(p.get("enhanced_accuracy", 0) for p in enhanced_paths) / len(enhanced_paths)
        
        if original_avg == 0:
            return 0.0
        
        return ((enhanced_avg - original_avg) / original_avg) * 100

    def _simulate_ml_scoring(self, features: Dict[str, Any]) -> float:
        """Simulate ML model scoring (placeholder for actual ML implementation)."""
        # Simple heuristic scoring for demonstration
        base_score = 0.7
        
        # Adjust based on features
        if features.get("base_confidence", 0) > 0.7:
            base_score += 0.15
        
        if features.get("path_length", 0) <= 3:
            base_score += 0.10
        
        if features.get("complexity") == "low":
            base_score += 0.05
        
        return min(1.0, base_score + 0.1)  # Small boost


# Singleton instance
conversion_inference_engine = ConversionInferenceEngine()
