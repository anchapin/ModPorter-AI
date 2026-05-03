---
phase: 15-07-advanced-rag-pipeline
plan: "02"
subsystem: search
tags: [rag, query-rewriting, adaptive-fusion, api]
dependency_graph:
  requires: ["15-07-01"]
  provides:
    - query_rewriter
    - adaptive_fusion
    - rag_api_endpoint
  affects:
    - rag_pipeline
tech_stack:
  added:
    - QueryRewriter with rule-based and LLM-based rewriting
    - AdaptiveFusion with query-type-aware score fusion
    - FastAPI endpoint /api/v1/search/rag
  patterns:
    - Adaptive fusion strategies based on query type
    - Abbreviation expansion for common terms
key_files:
  created:
    - ai-engine/search/query_rewriter.py
    - ai-engine/search/adaptive_fusion.py
    - backend/src/api/rag.py
  modified:
    - backend/src/main.py
decisions:
  - "Query rewriting can be disabled for performance"
  - "Fusion strategy adapts based on query type (informational, navigational, transactional)"
  - "API endpoint follows RESTful design with request/response models"
metrics:
  duration: "completed"
  completed_date: "2026-03-27"
---

# Phase 15-07 Plan 02: Query Rewriting & Adaptive Fusion Summary

## Overview
Added query rewriting and adaptive fusion capabilities to the RAG pipeline.

## Deliverables

### 1. Query Rewriter (`ai-engine/search/query_rewriter.py`)
- **QueryRewriter class** - LLM-based and rule-based query rewriting
- **RewriteResult** - Result with original query, rewritten query, confidence
- **RewriteType enum** - CLARIFICATION, SPECIFICATION, DECOMPOSITION, NONE
- Abbreviation expansion (mc → Minecraft, api → application programming interface)
- Can be disabled for performance-sensitive use cases

### 2. Adaptive Fusion (`ai-engine/search/adaptive_fusion.py`)
- **AdaptiveFusion** - Query-type-aware score fusion
- **Fusion strategies**: RECIPROCAL_RANK_FUSION, WEIGHTED_SUM, SCORE_AVERAGING, CONFIDENCE_WEIGHTED
- Query-type-specific weights:
  - INFORMATIONAL: Semantic-first (vector scores weighted higher)
  - NAVIGATIONAL: Keyword-first (BM25 scores weighted higher)
  - TRANSACTIONAL: Hybrid balanced
  - COMPLEX: Ensemble with all signals
  - SIMPLE: Fast single-source

### 3. RAG Search API Endpoint (`backend/src/api/rag.py`)
- **POST /api/v1/search/rag** - Full RAG pipeline search endpoint
- **Request model**: query, top_k, enable_rewrite, enable_rerank, rerank_stages, fusion_strategy
- **Response model**: results, query_analysis, rewritten_query, timing, stages_applied
- **GET /api/v1/search/rag/health** - Health check endpoint

## Verification
- [x] QueryRewriter imports without errors
- [x] AdaptiveFusion imports without errors
- [x] API endpoint registered in main.py
- [x] Integration with RAGPipeline complete

## Success Criteria
Pipeline includes query rewriting and adaptive fusion with API exposure ✅
