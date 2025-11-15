"""
Pytest plugin to apply mocks before any tests are imported.

This plugin helps avoid dependency issues by mocking heavy libraries
like chromadb and sentence-transformers before they're imported.
"""

import sys
from unittest.mock import MagicMock, Mock

def pytest_configure(config):
    """Apply mocks at the earliest possible moment in pytest session."""
    # Comprehensive chromadb mock
    chromadb_mock = MagicMock()

    # Mock config module
    config_mock = MagicMock()
    config_mock.Settings = Mock()
    chromadb_mock.config = config_mock
    sys.modules['chromadb.config'] = config_mock

    # Mock api module
    api_mock = MagicMock()
    chromadb_mock.api = api_mock

    # Mock models
    models_mock = MagicMock()
    api_mock.models = models_mock
    sys.modules['chromadb.api.models'] = models_mock

    # Mock main chromadb module
    sys.modules['chromadb'] = chromadb_mock

    # Mock sentence-transformers
    sentence_transformers_mock = MagicMock()

    # Mock SentenceTransformer class
    transformer_mock = MagicMock()
    transformer_mock.encode = MagicMock(return_value=[[0.1, 0.2, 0.3]])
    sentence_transformers_mock.SentenceTransformer = Mock(return_value=transformer_mock)

    # Mock util module
    util_mock = MagicMock()
    util_mock.cos_sim = MagicMock(return_value=0.8)
    sentence_transformers_mock.util = util_mock

    sys.modules['sentence_transformers'] = sentence_transformers_mock
    sys.modules['sentence_transformers.util'] = util_mock

    # Mock pgvector
    pgvector_mock = MagicMock()
    sqlalchemy_mock = MagicMock()
    sqlalchemy_mock.VECTOR = MagicMock()
    pgvector_mock.sqlalchemy = sqlalchemy_mock
    sys.modules['pgvector'] = pgvector_mock
    sys.modules['pgvector.sqlalchemy'] = sqlalchemy_mock

    # Mock other heavy dependencies
    sys.modules['torch'] = MagicMock()
    sys.modules['transformers'] = MagicMock()
    sys.modules['datasets'] = MagicMock()
    sys.modules['accelerate'] = MagicMock()

    # Apply RAG component mocks
    # Mock schemas.multimodal_schema
    multimodal_schema_mock = MagicMock()
    ContentType = Mock()
    ContentType.DOCUMENTATION = "documentation"
    ContentType.CODE = "code"
    ContentType.CONFIGURATION = "configuration"
    ContentType.IMAGE = "image"
    multimodal_schema_mock.ContentType = ContentType
    sys.modules['schemas.multimodal_schema'] = multimodal_schema_mock

    # Mock search modules
    search_mock = MagicMock()
    sys.modules['search'] = search_mock
    sys.modules['search.hybrid_search_engine'] = MagicMock()
    sys.modules['search.reranking_engine'] = MagicMock()
    sys.modules['search.query_expansion'] = MagicMock()

    # Mock utils modules
    utils_mock = MagicMock()
    sys.modules['utils'] = utils_mock
    sys.modules['utils.multimodal_embedding_generator'] = MagicMock()
    sys.modules['utils.advanced_chunker'] = MagicMock()
    sys.modules['utils.vector_db_client'] = MagicMock()

    # Mock evaluation modules
    evaluation_mock = MagicMock()
    sys.modules['evaluation'] = evaluation_mock
    sys.modules['evaluation.rag_evaluator'] = MagicMock()
