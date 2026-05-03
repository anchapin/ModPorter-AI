# Phase 15-07 Context: Advanced RAG Pipeline

## Phase Overview
**Phase Goal**: Re-ranking pipeline, query expansion, hybrid fusion  
**Deliverables**:
- Multi-stage re-ranking pipeline
- Query rewrite and expansion
- Hybrid fusion algorithms
- Performance optimization

## Requirements Mapped
- RAG-7.1: Multi-stage re-ranking pipeline
- RAG-7.2: Query rewrite and expansion
- RAG-7.3: Hybrid fusion algorithms

## Current State Analysis

### Existing Components (from prior phases)
1. **reranking_engine.py** - Multiple strategies: cross-encoder, feature-based, neural, ensemble, contextual
2. **query_expansion.py** - Multiple strategies: synonym, contextual, domain (Minecraft-specific), semantic, historical
3. **hybrid_search_engine.py** - BM25, vector, semantic, context scoring with multiple ranking strategies
4. **feedback_reranker.py** - User feedback-based reranking (Phase 15-05)
5. **query_complexity_analyzer.py** - Query complexity analysis

### What's Missing
1. **Unified Pipeline** - No orchestrator that combines all these components
2. **Multi-Stage Re-ranking** - Sequential application of multiple rerankers
3. **LLM Query Rewrite** - Using LLM to rewrite/clarify ambiguous queries
4. **Adaptive Fusion** - Intelligent combination based on query type
5. **Performance Optimization** - Caching, batching, async processing

## Design Decisions

### Architecture
- Create `rag_pipeline.py` as the main orchestrator
- Pipeline stages: Query Analysis → Rewrite → Expansion → Search → Multi-Stage Re-rank → Fusion
- Configurable pipeline with pluggable stages

### Key Components to Build
1. **RAGPipeline** - Main orchestrator class
2. **MultiStageReranker** - Sequential reranking with stage config
3. **QueryRewriter** - LLM-based query rewriting
4. **AdaptiveFusion** - Query-type-aware score fusion
5. **PipelineCache** - Result caching for performance

### Performance Targets
- <100ms for simple queries (no LLM rewrite)
- <500ms for complex queries (with LLM rewrite)
- Support async batch processing

## Dependencies
- Phase 15-02: HybridSearchEngine, RerankingEngine
- Phase 15-05: FeedbackReranker
- Phase 15-06: Cross-reference linking

## Constraints
- Must integrate with existing HybridSearchEngine
- Must work with existing embedding/reranking models
- Must maintain backward compatibility with existing API endpoints
