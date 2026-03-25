# Phase 15-01: Improved Document Indexing

## Phase Information
- **Phase**: 15-01
- **Name**: Improved Document Indexing
- **Goal**: Smart chunking, metadata extraction, hierarchical indexing

## Context

### From Milestone v4.6
Build advanced RAG system with improved document indexing, semantic search, knowledge expansion, context optimization, user correction learning, and multi-modal support.

### From STATE.md
- **Previous Phase**: 14-07 (Sealed Classes) - 170+ tests passing
- **Current Milestone**: v4.6 - RAG & Knowledge Enhancement (8 phases)
- **Target**: Improved Document Indexing

### Technical Context

#### Current RAG Architecture
- **Backend**: `backend/src/api/embeddings.py` - CRUD operations for embeddings
- **AI Engine Search**: `ai-engine/search/` - hybrid_search_engine.py, query_expansion.py, reranking_engine.py
- **Database**: PostgreSQL with pgvector for vector storage
- **Embedding Model**: sentence-transformers/all-MiniLM-L6-v2 (configurable to OpenAI)

#### Key Files
- `backend/src/api/embeddings.py` - Embeddings API endpoints
- `ai-engine/search/hybrid_search_engine.py` - Hybrid search implementation
- `ai-engine/search/reranking_engine.py` - Re-ranking capabilities
- `ai-engine/search/query_expansion.py` - Query expansion logic
- `backend/src/db/models.py` - Database models with pgvector VECTOR(1536)

### Technical Decisions (Locked)
- PostgreSQL + pgvector for vector storage (production)
- sentence-transformers/all-MiniLM-L6-v2 for embeddings (default)
- Async SQLAlchemy for database operations
- FastAPI for backend API

### Technical Constraints
- Must maintain backward compatibility with existing embeddings API
- Must work with existing vector database schema
- Must support both local and OpenAI embeddings

### Dependencies
- Phase 14-xx (completed): Java pattern conversion features
- No dependencies on upcoming phases

### Discretion Areas
- Chunking strategy selection (fixed-size, semantic, recursive)
- Metadata extraction approach
- Hierarchical indexing structure design
- Performance optimization vs. accuracy tradeoffs
