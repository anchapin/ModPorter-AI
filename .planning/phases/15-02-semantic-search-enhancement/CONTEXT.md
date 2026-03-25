# Phase 15-02: Semantic Search Enhancement

## Phase Information
- **Phase**: 15-02
- **Name**: Semantic Search Enhancement
- **Goal**: Hybrid search improvement, re-ranking, query expansion

## Context

### From Milestone v4.6
Build advanced RAG system with improved document indexing, semantic search, knowledge expansion, context optimization, user correction learning, and multi-modal support.

### From STATE.md
- **Previous Phase**: 15-01 (Improved Document Indexing) - Just completed
- **Current Milestone**: v4.6 - RAG & Knowledge Enhancement (8 phases)
- **Target**: Semantic Search Enhancement

### Technical Context

#### Current RAG Architecture
- **Backend**: `backend/src/api/embeddings.py` - CRUD operations for embeddings
- **AI Engine Search**: `ai-engine/search/` - existing search components
- **Database**: PostgreSQL with pgvector for vector storage
- **Embedding Model**: sentence-transformers/all-MiniLM-L6-v2 (configurable to OpenAI)

#### What Was Built in 15-01
- Smart chunking strategies (FixedSize, Recursive, Semantic)
- Metadata extraction for Java/Bedrock code constructs
- Hierarchical index structure (document → section → chunk)
- Embedding API for document vector operations
- `ai-engine/indexing/` module with chunking and metadata extraction

#### Key Files
- `backend/src/api/embeddings.py` - Embeddings API endpoints
- `ai-engine/search/` - Search components (to be enhanced)
- `ai-engine/indexing/chunking_strategies.py` - Chunking from 15-01
- `backend/src/db/models.py` - Database models with pgvector VECTOR(1536)

### Technical Decisions (Locked)
- PostgreSQL + pgvector for vector storage (production)
- sentence-transformers/all-MiniLM-L6-v2 for embeddings (default)
- Async SQLAlchemy for database operations
- FastAPI for backend API
- Cross-encoder: cross-encoder/ms-marco-MiniLM-L-6-v2 for re-ranking

### Technical Constraints
- Must maintain backward compatibility with existing search API
- Search latency must remain < 500ms with re-ranking
- Hybrid search should work with existing document indices