# Phase 15-05: User Correction Learning

## Phase Information
- **Phase**: 15-05
- **Name**: User Correction Learning
- **Goal**: Store and apply user feedback/corrections to knowledge base

## Context

### From Milestone v4.6
Build advanced RAG system with improved document indexing, semantic search, knowledge expansion, context optimization, user correction learning, and multi-modal support.

### From STATE.md
- **Previous Phases**: 
  - 15-01 (Improved Document Indexing) - Complete
  - 15-02 (Semantic Search Enhancement) - Complete
  - 15-03 (Knowledge Base Expansion) - Complete
  - 15-04 (Context Window Optimization) - Complete
- **Current Milestone**: v4.6 - RAG & Knowledge Enhancement (8 phases)
- **Target**: User Correction Learning

### Technical Context

#### Current RAG Architecture
- **Backend**: `backend/src/api/embeddings.py` - CRUD operations for embeddings
- **AI Engine Search**: `ai-engine/search/` - hybrid_search_engine.py, query_expansion.py, reranking_engine.py
- **Database**: PostgreSQL with pgvector for vector storage
- **Embedding Model**: sentence-transformers/all-MiniLM-L6-v2 (configurable to OpenAI)
- **Indexing**: `ai-engine/indexing/` - chunking_strategies.py, metadata_extractor.py
- **Context Optimization**: `ai-engine/search/query_complexity_analyzer.py`, `context_manager.py`, `chunk_prioritizer.py`

#### Phase 15-01-04 Accomplishments
- Phase 15-01: Smart chunking strategies (FixedSize, Recursive, Semantic), metadata extraction, hierarchical indexing
- Phase 15-02: Hybrid search (semantic + keyword), cross-encoder re-ranking, query expansion, BM25 fallback
- Phase 15-03: Minecraft/Bedrock documentation ingestion, 40+ conversion patterns, community workflow
- Phase 15-04: Query complexity-based dynamic context sizing, chunk prioritization, multi-turn conversation management

#### Key Files
- `backend/src/api/embeddings.py` - Embeddings API endpoints
- `backend/src/db/models.py` - Database models including ConversionFeedback, PatternSubmission, DocumentEmbedding
- `ai-engine/search/hybrid_search_engine.py` - Hybrid search implementation
- `ai-engine/indexing/chunking_strategies.py` - Chunking strategies
- `ai-engine/search/query_complexity_analyzer.py` - Query classification
- `ai-engine/search/context_manager.py` - Multi-turn context

#### Existing Feedback Infrastructure
- `ConversionFeedback` model (backend/src/db/models.py:340-355): Stores user feedback on conversions
- `PatternSubmission` model: Community pattern submissions with approval workflow
- `feedback` relationship on ConversionJob: Links feedback to conversion jobs

### Requirements (RAG-5.1, RAG-5.2)
- RAG-5.1: User feedback collection system for conversion corrections
- RAG-5.2: Correction validation, approval workflow, and knowledge base update pipeline

### Deliverables
1. User feedback collection system for code corrections
2. Correction validation and approval workflow
3. Knowledge base update pipeline (applying corrections to embeddings)
4. Feedback-driven re-ranking

### Technical Decisions (Locked)
- PostgreSQL + pgvector for vector storage (production)
- sentence-transformers/all-MiniLM-L6-v2 for embeddings (default)
- Async SQLAlchemy for database operations
- FastAPI for backend API
- Must maintain backward compatibility with existing search API
- Reuse existing ConversionFeedback model for correction storage
- Reuse PatternSubmission approval workflow pattern

### Technical Constraints
- Must maintain backward compatibility with existing embeddings/search API
- Must work with existing vector database schema
- Must support both local and OpenAI embeddings
- Must integrate with existing user authentication
- Corrections must go through validation before being applied to knowledge base

### Discretion Areas
- Feedback collection interface design
- Correction validation algorithm
- Knowledge base update frequency and batching strategy
- Re-ranking algorithm based on correction patterns
- Performance optimization vs. accuracy tradeoffs
