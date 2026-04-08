import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from api.embeddings import router

app = FastAPI()
app.include_router(router)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


class TestEmbeddingsAPIReal:
    @patch("api.embeddings.get_db")
    @patch("api.embeddings.crud")
    async def test_create_embedding_new(self, mock_crud, mock_get_db, client):
        mock_get_db.return_value = AsyncMock()
        mock_crud.get_document_embedding_by_hash = AsyncMock(return_value=None)

        import uuid

        mock_embedding = MagicMock()
        mock_embedding.id = uuid.uuid4()
        mock_embedding.embedding = [0.1] * 384
        mock_embedding.document_source = "test.txt"
        mock_embedding.content_hash = "hash123"
        mock_crud.create_document_embedding = AsyncMock(return_value=mock_embedding)

        payload = {
            "embedding": [0.1] * 384,
            "document_source": "test.txt",
            "content_hash": "hash123",
        }

        response = client.post("/embeddings/", json=payload)

        assert response.status_code == 201
        assert response.json()["content_hash"] == "hash123"

    @patch("api.embeddings.get_db")
    @patch("api.embeddings.crud")
    async def test_create_embedding_existing(self, mock_crud, mock_get_db, client):
        mock_get_db.return_value = AsyncMock()

        import uuid

        mock_embedding = MagicMock()
        mock_embedding.id = uuid.uuid4()
        mock_embedding.embedding = [0.1] * 384
        mock_embedding.document_source = "test.txt"
        mock_embedding.content_hash = "hash123"
        mock_crud.get_document_embedding_by_hash = AsyncMock(return_value=mock_embedding)

        payload = {
            "embedding": [0.1] * 384,
            "document_source": "test.txt",
            "content_hash": "hash123",
        }

        response = client.post("/embeddings/", json=payload)

        assert response.status_code == 200
        assert response.json()["content_hash"] == "hash123"

    @patch("api.embeddings.get_db")
    @patch("api.embeddings.crud")
    async def test_search_embeddings_success(self, mock_crud, mock_get_db, client):
        mock_get_db.return_value = AsyncMock()

        import uuid

        mock_embedding = MagicMock()
        mock_embedding.id = uuid.uuid4()
        mock_embedding.embedding = [0.1] * 384
        mock_embedding.document_source = "test.txt"
        mock_embedding.content_hash = "hash123"
        mock_crud.find_similar_embeddings = AsyncMock(return_value=[mock_embedding])

        payload = {"query_embedding": [0.1] * 384, "limit": 5}

        response = client.post("/embeddings/search/", json=payload)

        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["content_hash"] == "hash123"

    def test_search_embeddings_empty_query(self, client):
        payload = {"query_embedding": [], "limit": 5}
        response = client.post("/embeddings/search/", json=payload)
        assert response.status_code == 400
        assert "query_embedding must not be empty" in response.json()["detail"]

    @patch("api.embeddings.get_db")
    @patch("api.embeddings.crud")
    async def test_index_document_success(self, mock_crud, mock_get_db, client):
        mock_get_db.return_value = AsyncMock()

        # Mock the embedding generator module to avoid loading torch/sentence-transformers
        mock_gen_class = MagicMock()
        mock_gen = MagicMock()
        mock_gen_class.return_value = mock_gen

        mock_emb_result = MagicMock()
        mock_emb_result.embedding.tolist.return_value = [0.1] * 384
        mock_gen.generate_embeddings.return_value = [mock_emb_result]

        with patch.dict(
            "sys.modules",
            {"utils.embedding_generator": MagicMock(LocalEmbeddingGenerator=mock_gen_class)},
        ):
            # Mock other dependencies
            with patch("api.embeddings._get_ai_engine_indexing") as mock_get_indexing:
                mock_factory = MagicMock()
                mock_extractor_class = MagicMock()
                mock_get_indexing.return_value = (mock_factory, mock_extractor_class)

                # Mock the chunking strategy and metadata extractor
                mock_strategy = MagicMock()
                mock_factory.create.return_value = mock_strategy

                mock_chunk = MagicMock()
                mock_chunk.content = "chunk1"
                mock_chunk.heading_context = []
                mock_chunk.original_heading = None
                mock_chunk.char_start = 0
                mock_chunk.char_end = 10
                mock_chunk.content_hash = "hash1"
                mock_strategy.chunk.return_value = [mock_chunk]

                mock_extractor = MagicMock()
                mock_extractor_class.return_value = mock_extractor

                mock_metadata = MagicMock()
                mock_metadata.document_type = "text"
                mock_metadata.tags = []
                mock_metadata.title = "Test Doc"
                mock_metadata.to_dict.return_value = {"title": "Test Doc"}
                mock_extractor.extract.return_value = mock_metadata

                mock_chunk_meta = MagicMock()
                mock_chunk_meta.to_dict.return_value = {"chunk": 0}
                mock_extractor.create_chunk_metadata.return_value = mock_chunk_meta

                # Mock DB operations
                from types import SimpleNamespace
                import uuid

                mock_doc = SimpleNamespace(id=uuid.uuid4())
                mock_crud.create_document_with_chunks = AsyncMock(
                    return_value=(mock_doc, [MagicMock()])
                )

                payload = {
                    "content": "This is a test document content.",
                    "source": "test.md",
                    "metadata": {"type": "guide"},
                }

                response = client.post("/embeddings/index-document", json=payload)

                assert response.status_code == 201
                assert "document_id" in response.json()
                assert response.json()["chunks_created"] == 1
