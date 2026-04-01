
import pytest
import uuid
import sys
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import status
from httpx import AsyncClient, ASGITransport
from main import app
from db.models import DocumentEmbedding
from models.embedding_models import DocumentEmbeddingResponse

@pytest.mark.asyncio
class TestEmbeddingsAPILogic:
    """Test the logic of embeddings API endpoints."""

    async def test_create_embedding_new(self):
        """Test creating a new embedding successfully."""
        now = datetime.now(timezone.utc)
        mock_embedding = MagicMock(spec=DocumentEmbedding)
        mock_embedding.id = uuid.uuid4()
        mock_embedding.content_hash = "new-hash"
        mock_embedding.document_source = "source"
        mock_embedding.embedding = [0.1, 0.2]
        mock_embedding.created_at = now
        mock_embedding.updated_at = now

        with patch("db.crud.get_document_embedding_by_hash", new_callable=AsyncMock) as mock_get, \
             patch("db.crud.create_document_embedding", new_callable=AsyncMock) as mock_create:
            
            mock_get.return_value = None
            mock_create.return_value = mock_embedding

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                response = await ac.post(
                    "/api/v1/embeddings/embeddings/",
                    json={
                        "embedding": [0.1, 0.2],
                        "document_source": "source",
                        "content_hash": "new-hash"
                    }
                )

            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["content_hash"] == "new-hash"
            mock_get.assert_called_once()
            mock_create.assert_called_once()

    async def test_create_embedding_existing(self):
        """Test getting an existing embedding when content hash matches."""
        now = datetime.now(timezone.utc)
        mock_embedding = MagicMock(spec=DocumentEmbedding)
        mock_embedding.id = uuid.uuid4()
        mock_embedding.content_hash = "existing-hash"
        mock_embedding.document_source = "source"
        mock_embedding.embedding = [0.1, 0.2]
        mock_embedding.created_at = now
        mock_embedding.updated_at = now

        with patch("db.crud.get_document_embedding_by_hash", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_embedding

            # Mock model_dump to return serializable data
            with patch("models.embedding_models.DocumentEmbeddingResponse.model_dump") as mock_dump:
                mock_dump.return_value = {
                    "id": str(mock_embedding.id),
                    "content_hash": "existing-hash",
                    "document_source": "source",
                    "embedding": [0.1, 0.2],
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                }

                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    response = await ac.post(
                        "/api/v1/embeddings/embeddings/",
                        json={
                            "embedding": [0.1, 0.2],
                            "document_source": "source",
                            "content_hash": "existing-hash"
                        }
                    )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["content_hash"] == "existing-hash"
            mock_get.assert_called_once()

    async def test_search_similar_embeddings_success(self):
        """Test searching for similar embeddings."""
        now = datetime.now(timezone.utc)
        mock_result = MagicMock()
        mock_result.id = uuid.uuid4()
        mock_result.content_hash = "hash"
        mock_result.document_source = "source"
        mock_result.embedding = [0.1, 0.2]
        mock_result.created_at = now
        mock_result.updated_at = now

        with patch("db.crud.find_similar_embeddings", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = [mock_result]

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                response = await ac.post(
                    "/api/v1/embeddings/embeddings/search/",
                    json={
                        "query_embedding": [0.1, 0.2],
                        "limit": 5
                    }
                )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 1
            assert data[0]["content_hash"] == "hash"
            mock_find.assert_called_once()

    async def test_search_similar_embeddings_empty_query(self):
        """Test searching with empty query embedding."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/embeddings/embeddings/search/",
                json={
                    "query_embedding": [],
                    "limit": 5
                }
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_generate_embeddings_success(self):
        """Test generating embeddings via the API."""
        # Mock the embedding generator
        mock_result = MagicMock()
        mock_result.embedding = MagicMock()
        mock_result.embedding.tolist.return_value = [0.1, 0.2]
        
        # We need to mock the components imported inside the endpoint
        # First, ensure utils.embedding_generator can be imported by mocking it in sys.modules
        mock_gen_module = MagicMock()
        sys.modules["utils.embedding_generator"] = mock_gen_module
        
        with patch("utils.embedding_generator.OpenAIEmbeddingGenerator") as mock_openai_gen, \
             patch("utils.embedding_generator.LocalEmbeddingGenerator") as mock_local_gen:
                
                mock_instance = mock_local_gen.return_value
                mock_instance.generate_embeddings.return_value = [mock_result]
                
                # Force use of local generator
                mock_openai_gen_instance = mock_openai_gen.return_value
                mock_openai_gen_instance._client = None

                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    response = await ac.post(
                        "/api/v1/embeddings/embeddings/generate",
                        json={
                            "texts": ["hello world"],
                            "provider": "local"
                        }
                    )

                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data == [[0.1, 0.2]]

    async def test_get_document_success(self):
        """Test getting a document by ID."""
        doc_id = uuid.uuid4()
        mock_doc = MagicMock()
        mock_doc.id = doc_id
        mock_doc.title = "Test Doc"
        mock_doc.document_source = "source"
        mock_doc.metadata_json = {"key": "value"}
        
        mock_chunk = MagicMock()
        mock_chunk.id = uuid.uuid4()
        mock_chunk.content_hash = "chunk-hash"
        mock_chunk.chunk_index = 0
        mock_chunk.metadata_json = {
            "char_start": 0, 
            "char_end": 10,
            "heading_context": ["H1"],
            "original_heading": "Heading"
        }

        with patch("db.crud.get_document_with_chunks", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = (mock_doc, [mock_chunk])

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                response = await ac.get(f"/api/v1/embeddings/embeddings/documents/{doc_id}")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == str(doc_id)
            assert data["title"] == "Test Doc"
            assert len(data["chunks"]) == 1
            assert data["chunks"][0]["content"] == "chunk-hash"

    async def test_get_document_not_found(self):
        """Test getting a non-existent document."""
        doc_id = uuid.uuid4()
        with patch("db.crud.get_document_with_chunks", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = (None, [])

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                response = await ac.get(f"/api/v1/embeddings/embeddings/documents/{doc_id}")

            assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_get_document_chunks_success(self):
        """Test getting chunks for a document."""
        doc_id = uuid.uuid4()
        mock_chunk = MagicMock()
        mock_chunk.id = uuid.uuid4()
        mock_chunk.chunk_index = 0
        mock_chunk.metadata_json = {
            "content": "chunk content", 
            "char_start": 0, 
            "char_end": 10,
            "heading_context": [],
            "original_heading": ""
        }

        with patch("db.crud.get_chunks_by_parent", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [mock_chunk]

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                response = await ac.get(f"/api/v1/embeddings/embeddings/documents/{doc_id}/chunks")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 1
            assert data[0]["content"] == "chunk content"

    async def test_hybrid_search_vector_only(self):
        """Test hybrid search in vector_only mode."""
        mock_result = MagicMock()
        mock_result.id = uuid.uuid4()
        mock_result.document_source = "source"
        mock_result.title = "Title"
        mock_result.chunk_index = 0
        mock_result.distance = 0.5
        mock_result.metadata_json = {"content": "text"}

        # Mock dependencies in sys.modules to avoid import errors
        sys.modules["utils.embedding_generator"] = MagicMock()
        
        with patch("db.crud.find_similar_embeddings", new_callable=AsyncMock) as mock_find, \
             patch("utils.embedding_generator.LocalEmbeddingGenerator") as mock_gen_class, \
             patch("utils.embedding_generator.OpenAIEmbeddingGenerator") as mock_openai_gen_class:
            
            mock_gen_instance = mock_gen_class.return_value
            mock_gen_instance.generate_embeddings.return_value = [MagicMock(embedding=MagicMock(tolist=lambda: [0.1, 0.2]))]
            
            mock_openai_gen_instance = mock_openai_gen_class.return_value
            mock_openai_gen_instance._client = None # Force fallback to local
            
            mock_find.return_value = [mock_result]

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                response = await ac.post(
                    "/api/v1/embeddings/embeddings/hybrid-search",
                    json={
                        "query": "test query",
                        "search_mode": "vector_only",
                        "expand_query": False,
                        "use_reranker": False
                    }
                )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data["results"]) == 1
            assert data["results"][0]["document_source"] == "source"
            assert data["results"][0]["vector_score"] > 0

    async def test_index_document_success(self):
        """Test indexing a document successfully."""
        # Mocking the complex internal logic of indexing
        with patch("api.embeddings._get_ai_engine_indexing") as mock_get_indexing:
            mock_factory = MagicMock()
            mock_extractor_class = MagicMock()
            mock_get_indexing.return_value = (mock_factory, mock_extractor_class)
            
            mock_strategy = MagicMock()
            mock_factory.create.return_value = mock_strategy
            
            mock_chunk = MagicMock()
            mock_chunk.content = "chunk content"
            mock_strategy.chunk.return_value = [mock_chunk]
            
            mock_extractor = mock_extractor_class.return_value
            # Return an object with document_type and metadata attribute
            mock_metadata_obj = MagicMock()
            mock_metadata_obj.document_type = "text"
            mock_metadata_obj.metadata = {"meta": "data"}
            mock_extractor.extract.return_value = mock_metadata_obj

            # Also need to mock LocalEmbeddingGenerator which is imported inside the function
            sys.modules["utils.embedding_generator"] = MagicMock()
            with patch("utils.embedding_generator.LocalEmbeddingGenerator") as mock_gen_class, \
                 patch("db.crud.create_document_with_chunks", new_callable=AsyncMock) as mock_create_db:
                
                mock_gen_instance = mock_gen_class.return_value
                mock_gen_instance.generate_embeddings.return_value = [MagicMock(embedding=MagicMock(tolist=lambda: [0.1, 0.2]))]
                
                mock_parent_doc = MagicMock()
                mock_parent_doc.id = uuid.uuid4()
                # Return a list of chunks as second element
                mock_create_db.return_value = (mock_parent_doc, [MagicMock()])

                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    response = await ac.post(
                        "/api/v1/embeddings/embeddings/index-document",
                        json={
                            "content": "some document content",
                            "source": "test-source",
                            "metadata": {"author": "test"},
                            "chunking_strategy": "fixed"
                        }
                    )

                assert response.status_code == status.HTTP_201_CREATED
                data = response.json()
                assert data["chunks_created"] == 1
                # Just check if metadata exists
                assert "metadata" in data

    async def test_hybrid_search_full(self):
        """Test hybrid search with more options."""
        mock_result_id = uuid.uuid4()
        
        # We need a result object that has all these attributes
        mock_result = MagicMock()
        mock_result.document = MagicMock()
        mock_result.document.id = str(mock_result_id)
        mock_result.document.content = "text"
        mock_result.document.metadata = {"source": "source", "title": "Title"}
        
        mock_result.final_score = 0.7
        mock_result.similarity_score = 0.8
        mock_result.keyword_score = 0.5
        mock_result.rank = 1
        mock_result.match_explanation = "test"
        mock_result.matched_content = "text"

        # Mock dependencies in sys.modules to avoid import errors
        sys.modules["utils.embedding_generator"] = MagicMock()
        
        with patch("api.embeddings.get_hybrid_engine") as mock_get_engine, \
             patch("utils.embedding_generator.LocalEmbeddingGenerator") as mock_gen_class, \
             patch("utils.embedding_generator.OpenAIEmbeddingGenerator") as mock_openai_gen_class:
            
            mock_engine = AsyncMock()
            mock_engine.search.return_value = [mock_result]
            mock_get_engine.return_value = mock_engine
            
            mock_gen_instance = mock_gen_class.return_value
            mock_gen_instance.generate_embeddings.return_value = [MagicMock(embedding=MagicMock(tolist=lambda: [0.1, 0.2]))]
            
            mock_openai_gen_instance = mock_openai_gen_class.return_value
            mock_openai_gen_instance._client = None
            
            # Mock DB result for documents
            mock_db_result = MagicMock()
            mock_db_doc = MagicMock()
            mock_db_doc.id = mock_result_id
            mock_db_doc.document_source = "source"
            mock_db_doc.title = "Title"
            mock_db_doc.embedding = [0.1, 0.2]
            mock_db_doc.metadata_json = {}
            mock_db_result.scalars.return_value.all.return_value = [mock_db_doc]

            with patch("sqlalchemy.ext.asyncio.AsyncSession.execute", new_callable=AsyncMock) as mock_execute:
                mock_execute.return_value = mock_db_result

                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    response = await ac.post(
                        "/api/v1/embeddings/embeddings/hybrid-search",
                        json={
                            "query": "test query",
                            "search_mode": "hybrid",
                            "expand_query": False,
                            "use_reranker": False
                        }
                    )

                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert len(data["results"]) == 1
                assert data["results"][0]["score"] > 0

    async def test_search_enhanced_success(self):
        """Test enhanced search endpoint successfully."""
        mock_result_id = uuid.uuid4()
        
        # Mock dependencies in sys.modules to avoid import errors
        sys.modules["utils.embedding_generator"] = MagicMock()
        sys.modules["schemas.multimodal_schema"] = MagicMock()
        sys.modules["search.hybrid_search_engine"] = MagicMock()
        
        # Mock the internal imports and helpers
        with patch("api.embeddings.get_query_expander") as mock_get_expander, \
             patch("api.embeddings.get_hybrid_engine") as mock_get_engine, \
             patch("utils.embedding_generator.LocalEmbeddingGenerator") as mock_gen_class, \
             patch("schemas.multimodal_schema.MultiModalDocument") as mock_doc_class, \
             patch("schemas.multimodal_schema.ContentType") as mock_content_type, \
             patch("schemas.multimodal_schema.SearchQuery") as mock_query_class, \
             patch("search.hybrid_search_engine.SearchMode") as mock_search_mode:
            
            # Mock expander
            mock_expander = MagicMock()
            mock_expander.expand_query.return_value = MagicMock(expanded_query="expanded query")
            mock_get_expander.return_value = mock_expander
            
            # Mock generator
            mock_gen_instance = mock_gen_class.return_value
            mock_gen_instance.generate_embeddings.return_value = [MagicMock(embedding=MagicMock(tolist=lambda: [0.1, 0.2]))]
            
            # Mock engine
            mock_engine = AsyncMock()
            mock_search_result = MagicMock()
            mock_search_result.document = MagicMock(id=str(mock_result_id), content="text", metadata={})
            mock_search_result.matched_content = "text"
            mock_search_result.similarity_score = 0.8
            mock_search_result.keyword_score = 0.5
            mock_search_result.final_score = 0.7
            mock_search_result.rank = 1
            mock_search_result.match_explanation = "test"
            mock_engine.search.return_value = [mock_search_result]
            mock_get_engine.return_value = mock_engine
            
            # Mock DB
            mock_db_result = MagicMock()
            mock_db_doc = MagicMock()
            mock_db_doc.id = mock_result_id
            mock_db_doc.document_source = "source"
            mock_db_doc.embedding = [0.1, 0.2]
            mock_db_doc.metadata_json = {}
            mock_db_result.scalars.return_value.all.return_value = [mock_db_doc]

            with patch("sqlalchemy.ext.asyncio.AsyncSession.execute", new_callable=AsyncMock) as mock_execute:
                mock_execute.return_value = mock_db_result

                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    response = await ac.post(
                        "/api/v1/embeddings/embeddings/search-enhanced/",
                        json={
                            "query_text": "test query",
                            "use_hybrid": True,
                            "use_reranker": False,
                            "expand_query": True
                        }
                    )

                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["total_results"] == 1
                assert data["results"][0]["document_id"] == str(mock_result_id)

