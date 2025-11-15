# Phase 2 API Documentation

## 🚀 Overview

This document provides comprehensive API documentation for all Phase 2 features of ModPorter-AI, including Knowledge Graph System, Community Curation System, Expert Knowledge Capture, Version Compatibility Matrix, and Automated Inference Engine.

## 📡 Base URLs

### Environments
- **Development**: `http://localhost:8000/api/v1`
- **Staging**: `https://staging-api.modporter.ai/v1`
- **Production**: `https://api.modporter.ai/v1`

## 🔐 Authentication

Phase 2 APIs require authentication:
```http
Authorization: Bearer <jwt_token>
X-User-ID: <user_id>
X-User-Role: <role>  # admin, contributor, reviewer, user
```

---

# 🔗 Knowledge Graph System API

## Base Path: `/api/v1/knowledge-graph`

## Nodes Management

### Create Node
```http
POST /api/v1/knowledge-graph/nodes/
Authorization: Bearer <token>
Content-Type: application/json

{
  "node_type": "java_class",
  "properties": {
    "name": "CustomBlock",
    "package": "com.example.mod",
    "modifiers": ["public", "final"]
  },
  "metadata": {
    "source_file": "CustomBlock.java",
    "lines": [1, 100],
    "minecraft_version": "1.19.2"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "node_12345",
    "node_type": "java_class",
    "properties": {
      "name": "CustomBlock",
      "package": "com.example.mod",
      "modifiers": ["public", "final"]
    },
    "metadata": {
      "source_file": "CustomBlock.java",
      "lines": [1, 100],
      "minecraft_version": "1.19.2"
    },
    "created_at": "2025-01-01T12:00:00Z",
    "updated_at": "2025-01-01T12:00:00Z"
  }
}
```

### Get Node
```http
GET /api/v1/knowledge-graph/nodes/{node_id}
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "node_12345",
    "node_type": "java_class",
    "properties": { /* ... */ },
    "relationships": [
      {
        "id": "rel_67890",
        "type": "extends",
        "target_id": "node_54321",
        "properties": { /* ... */ }
      }
    ]
  }
}
```

### Search Nodes
```http
GET /api/v1/knowledge-graph/search?query=BlockRegistry&node_type=java_class&limit=50&offset=0
Authorization: Bearer <token>
```

**Query Parameters:**
- `query` (string, optional): Search term
- `node_type` (string, optional): Filter by node type
- `limit` (integer, default: 50): Maximum results
- `offset` (integer, default: 0): Pagination offset

**Response:**
```json
{
  "success": true,
  "data": {
    "nodes": [
      {
        "id": "node_12345",
        "node_type": "java_class",
        "properties": {
          "name": "BlockRegistry",
          "package": "net.minecraft.block"
        },
        "relevance_score": 0.95
      }
    ],
    "total": 1,
    "offset": 0,
    "limit": 50
  }
}
```

### Get Node Neighbors
```http
GET /api/v1/knowledge-graph/nodes/{node_id}/neighbors?depth=2&relationship_types=extends,implements
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "center_node": { /* Node data */ },
    "neighbors": {
      "depth_1": [
        {
          "id": "node_67890",
          "relationship": {
            "type": "extends",
            "properties": { /* ... */ }
          },
          "node": { /* Node data */ }
        }
      ],
      "depth_2": [ /* ... */ ]
    }
  }
}
```

## Edges Management

### Create Edge
```http
POST /api/v1/knowledge-graph/edges/
Authorization: Bearer <token>
Content-Type: application/json

{
  "source_id": "node_12345",
  "target_id": "node_67890",
  "relationship_type": "depends_on",
  "properties": {
    "strength": 0.8,
    "dependency_type": "compile_time",
    "minecraft_version": "1.19.2"
  }
}
```

### Get Path
```http
GET /api/v1/knowledge-graph/path/{source_id}/{target_id}?max_depth=5&include_metadata=true
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "path": [
      {
        "node": { /* Node data */ },
        "edge": {
          "type": "extends",
          "properties": { /* ... */ }
        }
      }
    ],
    "path_length": 3,
    "total_cost": 0.75
  }
}
```

### Get Subgraph
```http
GET /api/v1/knowledge-graph/subgraph/{center_id}?radius=2&min_connections=3
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "center": { /* Center node data */ },
    "nodes": [ /* Array of nodes */ ],
    "edges": [ /* Array of edges */ ],
    "statistics": {
      "total_nodes": 15,
      "total_edges": 23,
      "density": 0.21
    }
  }
}
```

## Advanced Queries

### Execute Cypher Query
```http
POST /api/v1/knowledge-graph/query/
Authorization: Bearer <token>
Content-Type: application/json

{
  "query": "MATCH (n:java_class)-[r:extends]->(m:java_class) RETURN n, r, m LIMIT 10",
  "parameters": {},
  "include_metadata": true
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "results": [
      {
        "n": { /* Source node */ },
        "r": { /* Relationship */ },
        "m": { /* Target node */ }
      }
    ],
    "execution_time": "0.045s",
    "total_results": 10
  }
}
```

### Get Graph Statistics
```http
GET /api/v1/knowledge-graph/statistics/
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "total_nodes": 15420,
    "total_edges": 28930,
    "node_type_distribution": {
      "java_class": 5230,
      "java_method": 8920,
      "minecraft_block": 1200,
      "minecraft_item": 950,
      "minecraft_entity": 120
    },
    "relationship_type_distribution": {
      "extends": 3450,
      "implements": 1230,
      "depends_on": 8920,
      "creates": 2340,
      "modifies": 1890
    },
    "graph_density": 0.024,
    "average_degree": 3.75
  }
}
```

---

# 👥 Community Curation System API

## Base Path: `/api/v1/community`

## Peer Review System

### Create Review
```http
POST /api/v1/community/peer-review/reviews/
Authorization: Bearer <token>
Content-Type: application/json

{
  "contribution_id": "contrib_12345",
  "review_type": "technical",
  "reviewer_id": "user_67890",
  "technical_review": {
    "score": 8.5,
    "issues_found": [
      {
        "severity": "minor",
        "description": "Variable naming could be more descriptive",
        "line_numbers": [45, 67]
      }
    ],
    "suggestions": [
      "Use more descriptive variable names for clarity"
    ]
  },
  "functional_review": {
    "score": 9.0,
    "correctness": "verified",
    "edge_cases_tested": ["null_input", "empty_string", "negative_values"]
  },
  "recommendation": "approve",
  "comments": "Excellent contribution with minor improvements suggested"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "review_54321",
    "contribution_id": "contrib_12345",
    "reviewer_id": "user_67890",
    "status": "completed",
    "overall_score": 8.75,
    "recommendation": "approve",
    "created_at": "2025-01-01T12:00:00Z",
    "completed_at": "2025-01-01T12:30:00Z"
  }
}
```

### Get Review Queue
```http
GET /api/v1/community/peer-review/reviews/queue?expertise=java_modding&priority=high&limit=20&offset=0
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "reviews": [
      {
        "id": "review_12345",
        "contribution": {
          "id": "contrib_67890",
          "title": "Optimized Block Registration",
          "type": "code_pattern",
          "author": "expert_developer",
          "submitted_at": "2025-01-01T10:00:00Z"
        },
        "priority": "high",
        "expertise_required": ["java_modding", "performance"],
        "estimated_time": "30 minutes"
      }
    ],
    "total": 1,
    "offset": 0,
    "limit": 20
  }
}
```

### Submit Review
```http
POST /api/v1/community/peer-review/reviews/{review_id}/submit
Authorization: Bearer <token>
Content-Type: application/json

{
  "technical_review": {
    "score": 8.5,
    "issues_found": ["minor_naming_issue"],
    "suggestions": ["use_more_descriptive_names"]
  },
  "functional_review": {
    "score": 9.0,
    "correctness": "verified",
    "edge_cases": ["handles_null_input"]
  },
  "recommendation": "approve",
  "comments": "Excellent contribution with minor improvements suggested"
}
```

### Get Review Analytics
```http
GET /api/v1/community/peer-review/analytics?period=30d&reviewer_id=user_12345
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "period": "30d",
    "total_reviews": 45,
    "average_score": 8.2,
    "review_time_stats": {
      "average": "25 minutes",
      "median": "20 minutes",
      "p95": "45 minutes"
    },
    "approval_rate": 0.87,
    "top_reviewers": [
      {
        "user_id": "user_12345",
        "reviews_completed": 12,
        "average_score": 8.7
      }
    ]
  }
}
```

## Expert Knowledge Capture

### Submit Contribution
```http
POST /api/v1/community/expert-knowledge/contributions/
Authorization: Bearer <token>
Content-Type: application/json

{
  "contributor_id": "user_12345",
  "contribution_type": "code_pattern",
  "title": "Efficient Entity Spawning",
  "description": "Optimized approach to spawning multiple entities with minimal performance impact",
  "content": {
    "pattern_code": "public class EfficientEntitySpawner { /* ... */ }",
    "explanation": "This pattern uses object pooling and batch spawning...",
    "performance_notes": "Reduces entity spawning overhead by 60%"
  },
  "tags": ["entities", "performance", "spawning", "optimization"],
  "minecraft_version": "1.19.2",
  "references": [
    {
      "type": "documentation",
      "url": "https://minecraft.wiki/w/Entity",
      "title": "Minecraft Entity Documentation"
    },
    {
      "type": "example",
      "mod_id": "example_mod",
      "description": "Working implementation"
    }
  ],
  "test_cases": [
    {
      "description": "Spawns 1000 entities",
      "expected_result": "Completes within 100ms",
      "actual_result": "Completed in 85ms"
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "contrib_67890",
    "status": "pending_review",
    "submission_date": "2025-01-01T12:00:00Z",
    "extracted_knowledge": {
      "entities": ["EntitySpawner", "ObjectPool"],
      "patterns": ["object_pooling", "batch_processing"],
      "relationships": [
        {
          "source": "EntitySpawner",
          "target": "ObjectPool",
          "type": "uses"
        }
      ]
    }
  }
}
```

### Search Contributions
```http
GET /api/v1/community/expert-knowledge/contributions/search?query=block_registration&type=code_pattern&rating_min=4.0&verified=true&limit=20
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "contributions": [
      {
        "id": "contrib_12345",
        "title": "Efficient Block Registration",
        "type": "code_pattern",
        "author": "expert_developer",
        "rating": 4.8,
        "verified": true,
        "tags": ["blocks", "registration", "performance"],
        "summary": "Optimized pattern for registering large numbers of blocks...",
        "usage_count": 234,
        "created_at": "2025-01-01T10:00:00Z"
      }
    ],
    "total": 1,
    "facets": {
      "types": {
        "code_pattern": 45,
        "migration_guide": 23,
        "performance_tip": 18
      },
      "ratings": {
        "5.0": 12,
        "4.0+": 33,
        "3.0+": 54
      }
    }
  }
}
```

### Get Knowledge Recommendations
```http
POST /api/v1/community/expert-knowledge/recommendations
Authorization: Bearer <token>
Content-Type: application/json

{
  "current_task": "creating_custom_block",
  "mod_type": "forge",
  "user_expertise": "intermediate",
  "previous_work": ["item_creation", "basic_blocks"],
  "minecraft_version": "1.19.2",
  "preferences": {
    "performance_focused": true,
    "beginner_friendly": false,
    "modern_patterns": true
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "recommendations": [
      {
        "contribution_id": "contrib_12345",
        "title": "Advanced Block Properties",
        "relevance_score": 0.92,
        "reason": "Matches your current task and expertise level",
        "difficulty": "intermediate",
        "estimated_time": "2 hours",
        "prerequisites": ["basic_block_creation"]
      }
    ],
    "learning_path": [
      {
        "step": 1,
        "title": "Block Properties Basics",
        "contribution_id": "contrib_67890",
        "estimated_time": "30 minutes"
      },
      {
        "step": 2,
        "title": "Advanced Block Properties",
        "contribution_id": "contrib_12345",
        "estimated_time": "2 hours"
      }
    ]
  }
}
```

---

# 🔄 Version Compatibility Matrix API

## Base Path: `/api/v1/version-compatibility`

## Compatibility Data

### Get Compatibility Matrix
```http
GET /api/v1/version-compatibility/matrix/?start_version=1.17.0&end_version=1.19.2&include_detailed=true&format=json
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "matrix": [
      {
        "java_version": "1.17.0",
        "bedrock_version": "1.17.0",
        "compatibility_score": 0.95,
        "features_supported": [
          {
            "feature": "custom_blocks",
            "support_level": "full",
            "notes": "All block types supported"
          },
          {
            "feature": "entity_behaviors",
            "support_level": "partial",
            "notes": "Advanced AI behaviors may require manual adjustment"
          }
        ],
        "deprecated_patterns": [
          "old_block_registry_method",
          "legacy_event_handling"
        ],
        "known_issues": [
          "Some rendering differences between platforms",
          "Performance variation on mobile devices"
        ]
      }
    ],
    "summary": {
      "highest_compatibility": {
        "java_version": "1.18.2",
        "bedrock_version": "1.18.2",
        "score": 0.98
      },
      "lowest_compatibility": {
        "java_version": "1.17.0",
        "bedrock_version": "1.19.2",
        "score": 0.72
      }
    }
  }
}
```

### Get Migration Path
```http
GET /api/v1/version-compatibility/paths/1.17.0/1.19.2?min_score=0.8&max_steps=3&prefer_automated=true
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "path": [
      {
        "step": 1,
        "from_version": "1.17.0",
        "to_version": "1.18.0",
        "compatibility_score": 0.91,
        "automated_conversion": true,
        "estimated_time": "15 minutes",
        "migration_guide": {
          "summary": "Update registry methods and event handling",
          "code_changes": 12,
          "test_required": true
        }
      },
      {
        "step": 2,
        "from_version": "1.18.0",
        "to_version": "1.19.2",
        "compatibility_score": 0.87,
        "automated_conversion": true,
        "estimated_time": "20 minutes",
        "migration_guide": {
          "summary": "Update rendering pipeline and block properties",
          "code_changes": 8,
          "test_required": true
        }
      }
    ],
    "total_score": 0.89,
    "total_estimated_time": "35 minutes",
    "automation_coverage": "100%"
  }
}
```

### Submit Compatibility Report
```http
POST /api/v1/version-compatibility/reports/
Authorization: Bearer <token>
Content-Type: application/json

{
  "source_version": "1.18.2",
  "target_version": "1.19.2",
  "mod_id": "example_mod",
  "mod_type": "forge",
  "conversion_success": true,
  "issues_encountered": [
    {
      "type": "warning",
      "description": "Texture mapping required manual adjustment",
      "severity": "low",
      "resolution": "Updated texture paths manually"
    }
  ],
  "manual_fixes_required": 2,
  "total_conversion_time": "45 minutes",
  "user_experience": "moderately_difficult",
  "performance_impact": {
    "before": {
      "fps": 60,
      "memory_usage": "256MB"
    },
    "after": {
      "fps": 58,
      "memory_usage": "262MB"
    }
  },
  "feature_breakdown": {
    "blocks": {
      "total": 150,
      "converted": 148,
      "manual_adjustment": 2
    },
    "items": {
      "total": 75,
      "converted": 75,
      "manual_adjustment": 0
    },
    "entities": {
      "total": 25,
      "converted": 23,
      "manual_adjustment": 2
    }
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "report_id": "report_12345",
    "status": "submitted",
    "contributed_to_matrix": true,
    "impact_score": 0.85,
    "similar_reports_found": 3,
    "updated_compatibility_score": 0.88
  }
}
```

### Predict Compatibility
```http
POST /api/v1/version-compatibility/predict/
Authorization: Bearer <token>
Content-Type: application/json

{
  "mod_characteristics": {
    "lines_of_code": 10000,
    "custom_blocks": 150,
    "custom_items": 75,
    "custom_entities": 25,
    "complexity_score": 0.7,
    "uses_advanced_features": true,
    "dependencies": ["jei", "jeep", "tconstruct"]
  },
  "source_version": "1.18.2",
  "target_version": "1.19.2",
  "conversion_approach": "gradual_migration"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "predicted_score": 0.86,
    "confidence": 0.92,
    "breakdown": {
      "api_compatibility": 0.90,
      "feature_support": 0.82,
      "performance_impact": 0.88,
      "complexity_factor": 0.85
    },
    "risk_factors": [
      {
        "factor": "advanced_rendering_features",
        "impact": "high",
        "mitigation": "manual_review_of_rendering_code"
      },
      {
        "factor": "custom_entity_ai",
        "impact": "medium",
        "mitigation": "update_ai_behavior_system"
      }
    ],
    "recommendations": [
      "Test custom blocks thoroughly",
      "Update entity AI behaviors",
      "Validate rendering pipeline"
    ]
  }
}
```

---

# 🧠 Automated Inference Engine API

## Base Path: `/api/v1/conversion-inference`

## Path Inference

### Infer Conversion Path
```http
POST /api/v1/conversion-inference/infer-path/
Authorization: Bearer <token>
Content-Type: application/json

{
  "java_concept": "CustomBlock extends Block implements ITileEntityProvider",
  "target_platform": "bedrock",
  "minecraft_version": "1.19.2",
  "path_options": {
    "prefer_automated": true,
    "min_confidence": 0.8,
    "include_alternatives": true,
    "max_paths": 3
  },
  "context": {
    "mod_type": "forge",
    "complexity_indicators": {
      "has_custom_rendering": true,
      "has_tile_entity": true,
      "has_custom_behavior": false
    }
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "primary_path": {
      "steps": [
        {
          "step": 1,
          "action": "extract_block_properties",
          "confidence": 0.95,
          "automated": true,
          "estimated_time": "5 minutes"
        },
        {
          "step": 2,
          "action": "convert_tile_entity_to_block_components",
          "confidence": 0.87,
          "automated": true,
          "estimated_time": "15 minutes",
          "notes": "Requires manual review of complex tile entity logic"
        },
        {
          "step": 3,
          "action": "implement_bedrock_block_events",
          "confidence": 0.92,
          "automated": true,
          "estimated_time": "10 minutes"
        }
      ],
      "total_confidence": 0.91,
      "total_estimated_time": "30 minutes",
      "automation_coverage": "85%"
    },
    "alternative_paths": [
      {
        "path_id": "alt_1",
        "confidence": 0.84,
        "approach": "use_custom_block_behavior_packs",
        "differences": ["Simpler implementation", "Less customization", "Faster conversion"]
      }
    ],
    "success_probability": 0.89,
    "complexity_score": 0.72
  }
}
```

### Batch Path Inference
```http
POST /api/v1/conversion-inference/batch-infer/
Authorization: Bearer <token>
Content-Type: application/json

{
  "java_concepts": [
    "CustomItem extends Item",
    "CustomEntity extends EntityLiving",
    "CustomRecipe extends IRecipe"
  ],
  "target_platform": "bedrock",
  "minecraft_version": "1.19.2",
  "path_options": {
    "parallel_processing": true,
    "min_confidence": 0.8
  },
  "correlation_analysis": true
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "results": [
      {
        "java_concept": "CustomItem extends Item",
        "path": { /* Conversion path data */ },
        "confidence": 0.94,
        "estimated_time": "20 minutes"
      }
    ],
    "correlations": [
      {
        "concept1": "CustomItem",
        "concept2": "CustomRecipe",
        "correlation": 0.76,
        "type": "dependency",
        "notes": "Items often referenced in recipes"
      }
    ],
    "optimization_suggestions": [
      "Convert CustomItem and CustomRecipe together for better integration"
    ],
    "total_estimated_time": "65 minutes",
    "batch_confidence": 0.91
  }
}
```

### Optimize Conversion Sequence
```http
POST /api/v1/conversion-inference/optimize-sequence/
Authorization: Bearer <token>
Content-Type: application/json

{
  "java_concepts": [
    "CustomBlock",
    "CustomItem", 
    "CustomEntity",
    "CustomRecipe"
  ],
  "conversion_dependencies": {
    "CustomItem": ["CustomRecipe"],
    "CustomBlock": ["CustomItem", "CustomEntity"]
  },
  "target_platform": "bedrock",
  "minecraft_version": "1.19.2",
  "optimization_goals": [
    "minimize_total_time",
    "maximize_automation",
    "reduce_manual_intervention"
  ],
  "constraints": {
    "max_parallel_tasks": 2,
    "max_time_per_task": "2 hours"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "optimized_sequence": [
      {
        "phase": 1,
        "parallel_tasks": [
          {
            "concept": "CustomEntity",
            "estimated_time": "45 minutes",
            "confidence": 0.89
          },
          {
            "concept": "CustomBlock",
            "estimated_time": "60 minutes",
            "confidence": 0.87
          }
        ]
      },
      {
        "phase": 2,
        "sequential_tasks": [
          {
            "concept": "CustomItem",
            "estimated_time": "30 minutes",
            "confidence": 0.94,
            "dependencies": []
          },
          {
            "concept": "CustomRecipe",
            "estimated_time": "20 minutes",
            "confidence": 0.91,
            "dependencies": ["CustomItem"]
          }
        ]
      }
    ],
    "total_time": "155 minutes",
    "automation_coverage": "88%",
    "optimization_score": 0.92,
    "gained_efficiency": "23%"
  }
}
```

## Learning and Adaptation

### Submit Learning Data
```http
POST /api/v1/conversion-inference/learn/
Authorization: Bearer <token>
Content-Type: application/json

{
  "java_concept": "AdvancedCustomBlock with complex tile entity",
  "bedrock_concept": "CustomBlock with component-based behavior",
  "conversion_result": {
    "success": true,
    "manual_interventions": [
      {
        "type": "code_adjustment",
        "location": "tile_entity_logic",
        "description": "Updated tile entity update logic to work with Bedrock's component system",
        "time_spent": "15 minutes"
      }
    ],
    "performance_metrics": {
      "before_conversion": {
        "code_lines": 250,
        "complexity_score": 0.78
      },
      "after_conversion": {
        "code_lines": 180,
        "complexity_score": 0.65,
        "performance_improvement": "12%"
      }
    }
  },
  "success_metrics": {
    "functionality_preserved": 0.95,
    "performance_maintained": 0.88,
    "code_quality_improved": 0.82,
    "automation_success": 0.85
  },
  "feedback": {
    "user_satisfaction": 4.2,
    "conversion_difficulty": "moderate",
    "would_use_again": true
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "learning_id": "learn_12345",
    "status": "processed",
    "impact": {
      "model_accuracy_improvement": 0.02,
      "pattern_recognition_enhancement": true,
      "new_insights_discovered": 2
    },
    "updated_confidence_scores": {
      "similar_concepts": {
        "average_improvement": 0.08,
        "affected_patterns": 15
      }
    }
  }
}
```

### Get Model Performance
```http
GET /api/v1/conversion-inference/performance?period=30d&concept_type=block
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "period": "30d",
    "concept_type": "block",
    "overall_accuracy": 0.91,
    "confidence_distribution": {
      "0.9-1.0": 65,
      "0.8-0.9": 25,
      "0.7-0.8": 8,
      "below_0.7": 2
    },
    "performance_trends": [
      {
        "date": "2025-01-01",
        "accuracy": 0.89,
        "confidence": 0.87,
        "conversions_processed": 23
      }
    ],
    "top_performing_patterns": [
      {
        "pattern": "simple_block_conversion",
        "success_rate": 0.97,
        "average_confidence": 0.94
      }
    ],
    "areas_for_improvement": [
      {
        "concept_type": "complex_tile_entities",
        "current_accuracy": 0.73,
        "target_accuracy": 0.85,
        "recommended_action": "gather_more_training_data"
      }
    ]
  }
}
```

---

# 📊 Analytics and Monitoring

## Base Path: `/api/v1/analytics`

### System Health
```http
GET /api/v1/analytics/health
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "services": {
      "knowledge_graph": {
        "status": "healthy",
        "response_time": "45ms",
        "database_connections": 8,
        "cache_hit_rate": 0.92
      },
      "community_system": {
        "status": "healthy",
        "response_time": "120ms",
        "pending_reviews": 12,
        "active_users": 234
      },
      "inference_engine": {
        "status": "healthy",
        "response_time": "280ms",
        "model_version": "2.1.0",
        "accuracy": 0.91
      }
    },
    "performance": {
      "average_response_time": "148ms",
      "p95_response_time": "450ms",
      "request_rate": "45 req/s",
      "error_rate": 0.002
    }
  }
}
```

### Usage Statistics
```http
GET /api/v1/analytics/usage?period=7d&group_by=endpoint
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "period": "7d",
    "total_requests": 15420,
    "endpoint_breakdown": [
      {
        "endpoint": "/knowledge-graph/search",
        "requests": 5230,
        "average_response_time": "85ms",
        "success_rate": 0.998
      },
      {
        "endpoint": "/community/expert-knowledge/contributions/",
        "requests": 3420,
        "average_response_time": "320ms",
        "success_rate": 0.992
      }
    ],
    "user_activity": {
      "active_users": 1234,
      "new_users": 89,
      "retention_rate": 0.87
    },
    "feature_adoption": {
      "knowledge_graph": 0.73,
      "community_curation": 0.45,
      "inference_engine": 0.38
    }
  }
}
```

---

# 🔧 Error Handling

## Standard Error Response Format
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": [
      {
        "field": "minecraft_version",
        "issue": "Version 1.99.0 is not supported"
      }
    ]
  },
  "timestamp": "2025-01-01T12:00:00Z",
  "request_id": "req_12345"
}
```

## Common Error Codes

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Request validation failed |
| `AUTHENTICATION_ERROR` | 401 | Invalid or missing authentication |
| `AUTHORIZATION_ERROR` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `CONFLICT` | 409 | Resource conflict |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |
| `KNOWLEDGE_GRAPH_ERROR` | 422 | Graph query error |
| `INFERENCE_ENGINE_ERROR` | 422 | Inference failure |

---

# 📝 Rate Limiting

## Rate Limits by Endpoint

| Endpoint Category | Limit | Window |
|------------------|-------|--------|
| Knowledge Graph Search | 100/minute | per user |
| Community Contributions | 20/hour | per user |
| Peer Reviews | 50/hour | per reviewer |
| Inference Engine | 30/minute | per user |
| Analytics | 1000/hour | per organization |

---

# 🚀 Best Practices

## 1. Pagination
Always use pagination for list endpoints:
```http
GET /api/v1/knowledge-graph/search?limit=50&offset=100
```

## 2. Filtering
Use specific filters to reduce data transfer:
```http
GET /api/v1/community/contributions?type=code_pattern&rating_min=4.0
```

## 3. Caching
Implement client-side caching for stable data:
```http
GET /api/v1/knowledge-graph/statistics/
Cache-Control: max-age=3600
```

## 4. Batch Operations
Use batch endpoints for multiple operations:
```http
POST /api/v1/conversion-inference/batch-infer/
```

## 5. Error Handling
Always check the `success` field and handle errors appropriately:
```javascript
const response = await api.get('/knowledge-graph/nodes/123');
if (response.success) {
  // Handle success
} else {
  // Handle error based on response.error.code
}
```

## 6. Authentication
Store JWT tokens securely and refresh them before expiration:
```javascript
if (isTokenExpiring(token)) {
  token = await refreshToken();
}
```

---

# 📞 Support

For API support and questions:

- **Documentation**: [Full API Documentation](./API_COMPREHENSIVE.md)
- **Feature Documentation**: [Knowledge Graph](./features/KNOWLEDGE_GRAPH_SYSTEM.md), [Community Curation](./features/COMMUNITY_CURATION_SYSTEM.md)
- **Issues**: [GitHub Issues](https://github.com/modporter-ai/modporter-ai/issues)
- **Email**: api-support@modporter-ai.com
- **Status Page**: [https://status.modporter-ai.com](https://status.modporter-ai.com)

---

## Version History

### v2.0.0 (Current)
- Added Knowledge Graph System APIs
- Added Community Curation System APIs
- Added Version Compatibility Matrix APIs
- Added Automated Inference Engine APIs
- Enhanced authentication and authorization
- Improved error handling and monitoring

### v1.0.0
- Basic conversion APIs
- File upload and processing
- Simple authentication
- Basic analytics

---

*This documentation covers all Phase 2 APIs. For Phase 1 APIs, see the [Comprehensive API Documentation](./API_COMPREHENSIVE.md).*
