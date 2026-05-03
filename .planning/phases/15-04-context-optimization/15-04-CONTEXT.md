# Phase 15-04: Context Window Optimization

## Phase Information
- **Phase**: 15-04
- **Name**: Context Window Optimization
- **Goal**: Dynamic context sizing, relevant chunk prioritization

## Context

### From Milestone v4.6
Build advanced RAG system with improved document indexing, semantic search, knowledge expansion, context optimization, user correction learning, and multi-modal support.

### From STATE.md
- **Previous Phase**: 15-03 (Knowledge Base Expansion) - Complete
- **Current Milestone**: v4.6 - RAG & Knowledge Enhancement (8 phases)
- **Target**: Context Window Optimization

### Technical Context

#### Current RAG Architecture
- **Backend**: `backend/src/api/embeddings.py` - CRUD operations for embeddings
- **AI Engine Search**: `ai-engine/search/` - hybrid_search_engine.py, query_expansion.py, reranking_engine.py
- **Database**: PostgreSQL with pgvector for vector storage
- **Embedding Model**: sentence-transformers/all-MiniLM-L6-v2 (configurable to OpenAI)
- **Indexing**: `ai-engine/indexing/` - chunking_strategies.py, metadata_extractor.py

#### Phase 15-01-03 Accomplishments
- Phase 15-01: Smart chunking strategies (FixedSize, Recursive, Semantic), metadata extraction, hierarchical indexing
- Phase 15-02: Hybrid search (semantic + keyword), cross-encoder re-ranking, query expansion, BM25 fallback
- Phase 15-03: Minecraft/Bedrock documentation ingestion, 40+ conversion patterns, community workflow

#### Key Files
- `backend/src/api/embeddings.py` - Embeddings API endpoints
- `ai-engine/search/hybrid_search_engine.py` - Hybrid search implementation
- `ai-engine/indexing/chunking_strategies.py` - Chunking strategies
- `backend/src/db/models.py` - Database models with pgvector VECTOR(1536)

### Requirements (RAG-4.1, RAG-4.2)
- RAG-4.1: Dynamic context window sizing based on query complexity
- RAG-4.2: Relevancy-based chunk prioritization

### Deliverables
1. Dynamic context window sizing based on query complexity
2. Relevancy-based chunk prioritization
3. Context compression for long documents
4. Multi-turn conversation context management

### Technical Decisions (Locked)
- PostgreSQL + pgvector for vector storage (production)
- sentence-transformers/all-MiniLM-L6-v2 for embeddings (default)
- Async SQLAlchemy for database operations
- FastAPI for backend API
- Must maintain backward compatibility with existing search API

### Technical Constraints
- Must maintain backward compatibility with existing embeddings/search API
- Must work with existing vector database schema
- Must support both local and OpenAI embeddings
- Must handle long documents efficiently

### Discretion Areas
- Query complexity classification algorithm
- Context compression technique selection
- Multi-turn memory management strategy
- Performance optimization vs. accuracy tradeoffs
