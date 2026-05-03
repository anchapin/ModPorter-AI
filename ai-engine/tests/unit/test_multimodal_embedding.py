"""
Unit tests for MultiModalEmbeddingGenerator and related specialized generators.
"""

import pytest
import numpy as np
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from utils.multimodal_embedding_generator import (
    MultiModalEmbeddingGenerator, 
    CodeAwareEmbeddingGenerator, 
    ImageEmbeddingGenerator,
    EmbeddingStrategy,
    EmbeddingResult as MultiModalEmbeddingResult
)
from utils.embedding_generator import EmbeddingResult as BaseEmbeddingResult
from utils.advanced_chunker import Chunk, ChunkType

class TestCodeAwareEmbeddingGenerator:
    @pytest.fixture
    def generator(self):
        with patch('utils.multimodal_embedding_generator.LocalEmbeddingGenerator'):
            return CodeAwareEmbeddingGenerator()

    @pytest.mark.asyncio
    async def test_generate_code_embedding_success(self, generator):
        chunk = Chunk(
            content="public class MyBlock { public void test() { } }",
            chunk_type=ChunkType.CODE_CLASS,
            chunk_id="c1",
            metadata={"class_name": "MyBlock", "package_name": "com.test"}
        )
        
        # Proper setup of base result object
        mock_embedding = np.array([1.0, 2.0])
        mock_res = BaseEmbeddingResult(
            embedding=mock_embedding,
            model="test-model",
            dimensions=2
        )
        
        generator.base_generator.generate_embeddings = MagicMock(return_value=[mock_res])
        generator.base_generator.model_name = "test-model"
        
        with patch('inspect.iscoroutinefunction', return_value=False):
            result = await generator.generate_code_embedding(chunk)
        
        assert isinstance(result, MultiModalEmbeddingResult)
        assert np.array_equal(result.embedding, mock_embedding)

    @pytest.mark.asyncio
    async def test_generate_code_embedding_async_base(self, generator):
        chunk = Chunk("class A {}", ChunkType.CODE_CLASS, "id")
        
        mock_embedding = np.array([3.0, 4.0])
        mock_res = BaseEmbeddingResult(
            embedding=mock_embedding,
            model="m",
            dimensions=2
        )
        
        generator.base_generator.generate_embeddings = AsyncMock(return_value=[mock_res])
        generator.base_generator.model_name = "m"
        
        with patch('inspect.iscoroutinefunction', return_value=True):
            res = await generator.generate_code_embedding(chunk)
            assert np.array_equal(res.embedding, mock_embedding)

    @pytest.mark.asyncio
    async def test_generate_code_embedding_none_result(self, generator):
        chunk = Chunk("code", ChunkType.CODE_BLOCK, "id")
        generator.base_generator.generate_embeddings = AsyncMock(return_value=None)
        with patch('inspect.iscoroutinefunction', return_value=True):
            res = await generator.generate_code_embedding(chunk)
            assert res is None

    @pytest.mark.asyncio
    async def test_generate_code_embedding_failure(self, generator):
        chunk = Chunk("code", ChunkType.CODE_BLOCK, "id")
        generator.base_generator.generate_embeddings = MagicMock(side_effect=Exception("Embed fail"))
        
        result = await generator.generate_code_embedding(chunk)
        assert result is None

    def test_detect_minecraft_features(self, generator):
        code = "new Block(); GameRegistry.registerBlock(); @EventHandler"
        features = generator._detect_minecraft_features(code)
        assert "block" in features
        assert "registry" in features
        assert "uses_eventhandler" in features

    def test_enhance_code_context(self, generator):
        chunk = Chunk("void main() {}", ChunkType.CODE_METHOD, "id", metadata={"method_name": "main"})
        enhanced = generator._enhance_code_context(chunk)
        assert "Java method implementation" in enhanced
        assert "Method: main" in enhanced


class TestImageEmbeddingGenerator:
    @pytest.fixture
    def generator(self):
        return ImageEmbeddingGenerator()

    @pytest.mark.asyncio
    async def test_generate_image_embedding(self, generator):
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.stat') as mock_stat:
            mock_stat.return_value.st_size = 1024
            
            result = await generator.generate_image_embedding("assets/blocks/stone.png")
            
            assert result is not None
            assert result.strategy == EmbeddingStrategy.MULTIMODAL
            assert result.metadata["texture_category"] == "blocks"

    def test_classify_texture(self, generator):
        assert generator._classify_texture("items/apple.png") == "items"
        assert generator._classify_texture("gui/inventory.png") == "gui"
        assert generator._classify_texture("unknown/path.png") == "unknown"

    def test_extract_image_features_animated(self, generator):
        with patch('pathlib.Path.exists', return_value=False):
            features = generator._extract_image_features("test_anim.png")
            assert features["possibly_animated"] is True


class TestMultiModalEmbeddingGenerator:
    @pytest.fixture
    def generator(self):
        with patch('utils.multimodal_embedding_generator.LocalEmbeddingGenerator'), \
             patch('utils.multimodal_embedding_generator.CodeAwareEmbeddingGenerator'), \
             patch('utils.multimodal_embedding_generator.ImageEmbeddingGenerator'):
            return MultiModalEmbeddingGenerator()

    @pytest.mark.asyncio
    async def test_generate_embedding_text(self, generator):
        mock_res = MultiModalEmbeddingResult(np.array([1,2,3]), "m", EmbeddingStrategy.TEXT_ONLY)
        with patch.object(generator, '_generate_text_embedding', return_value=mock_res):
            res = await generator.generate_embedding("hello")
            assert res == mock_res

    @pytest.mark.asyncio
    async def test_generate_text_embedding_sync(self, generator):
        mock_embedding = np.array([1.0, 1.0])
        mock_res = BaseEmbeddingResult(
            embedding=mock_embedding,
            model="sync",
            dimensions=2
        )
        generator.text_generator.generate_embeddings = MagicMock(return_value=[mock_res])
        
        with patch('inspect.iscoroutinefunction', return_value=False):
            res = await generator._generate_text_embedding("test", EmbeddingStrategy.TEXT_ONLY)
            assert np.array_equal(res.embedding, mock_embedding)

    @pytest.mark.asyncio
    async def test_generate_embedding_chunk_text(self, generator):
        chunk = Chunk("text content", ChunkType.TEXT, "id")
        mock_res = MultiModalEmbeddingResult(np.array([1]), "m", EmbeddingStrategy.TEXT_ONLY)
        with patch.object(generator, '_generate_text_embedding', return_value=mock_res):
            res = await generator.generate_embedding(chunk)
            assert res == mock_res

    @pytest.mark.asyncio
    async def test_generate_multimodal_embedding_combined(self, generator):
        t_res = MultiModalEmbeddingResult(np.array([1.0, 0.0]), "m1", EmbeddingStrategy.TEXT_ONLY, confidence=1.0)
        i_res = MultiModalEmbeddingResult(np.array([0.0, 1.0]), "m2", EmbeddingStrategy.MULTIMODAL, confidence=1.0)
        
        generator._generate_text_embedding = AsyncMock(return_value=t_res)
        generator.image_generator.generate_image_embedding = AsyncMock(return_value=i_res)
        
        content = {"text": "some text", "image_path": "some/path.png"}
        result = await generator.generate_embedding(content)
        assert np.allclose(result.embedding, [0.5, 0.5])

    @pytest.mark.asyncio
    async def test_generate_multimodal_embedding_full_house(self, generator):
        t_res = MultiModalEmbeddingResult(np.array([1.0]), "m1", EmbeddingStrategy.TEXT_ONLY, confidence=1.0)
        i_res = MultiModalEmbeddingResult(np.array([1.0]), "m2", EmbeddingStrategy.MULTIMODAL, confidence=1.0)
        c_res = MultiModalEmbeddingResult(np.array([1.0]), "m3", EmbeddingStrategy.CODE_SPECIALIZED, confidence=1.0)
        
        generator._generate_text_embedding = AsyncMock(return_value=t_res)
        generator.image_generator.generate_image_embedding = AsyncMock(return_value=i_res)
        generator.code_generator.generate_code_embedding = AsyncMock(return_value=c_res)
        
        content = {"text": "t", "image_path": "i.png", "code": "c"}
        result = await generator.generate_embedding(content)
        assert len(result.metadata["modalities"]) == 3

    @pytest.mark.asyncio
    async def test_generate_multimodal_embedding_empty_dict(self, generator):
        result = await generator.generate_embedding({})
        assert result is None

    def test_combine_embeddings(self, generator):
        e1 = ("t", np.array([1.0, 1.0]), 1.0)
        e2 = ("i", np.array([2.0, 2.0]), 1.0)
        combined = generator._combine_embeddings([e1, e2])
        assert np.allclose(combined, [1.5, 1.5])

    @pytest.mark.asyncio
    async def test_batch_generate_embeddings(self, generator):
        generator.generate_embedding = AsyncMock(return_value=MagicMock())
        results = await generator.batch_generate_embeddings(["a", "b"])
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_batch_generate_embeddings_empty(self, generator):
        results = await generator.batch_generate_embeddings([])
        assert results == []

    @pytest.mark.asyncio
    async def test_unsupported_type(self, generator):
        res = await generator.generate_embedding(123)
        assert res is None
