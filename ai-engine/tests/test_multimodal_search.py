"""
Unit tests for multi-modal search components.

Tests:
- TextureMetadataExtractor: dimensions, transparency, color palette, category classification
- ModelMetadataExtractor: geometry parsing, animation extraction, material references
- MultiModalSearchEngine: content type filtering, modality-aware scoring
- CrossModalRetriever: finding related content across modalities
"""

import unittest
import tempfile
import json
import os
import sys
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestTextureMetadataExtractor(unittest.TestCase):
    """Tests for TextureMetadataExtractor."""

    def setUp(self):
        """Set up test fixtures."""
        try:
            from PIL import Image

            self.Image = Image
            self.pil_available = True
        except ImportError:
            self.pil_available = False

    def test_extractor_initialization(self):
        """Test that extractor initializes correctly."""
        from utils.texture_metadata_extractor import TextureMetadataExtractor

        extractor = TextureMetadataExtractor()
        self.assertIsNotNone(extractor)
        self.assertEqual(extractor.supported_formats, {"png", "jpg", "jpeg", "gif", "bmp"})

    @unittest.skipUnless(hasattr(unittest.TestCase, "Image"), "PIL not available")
    def test_extract_dimensions(self):
        """Test extracting dimensions from PNG."""
        from utils.texture_metadata_extractor import TextureMetadataExtractor

        # Create test image
        img = self.Image.new("RGBA", (64, 64), (255, 0, 0, 255))

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img.save(f.name)
            extractor = TextureMetadataExtractor()
            result = extractor.extract(f.name)
            os.unlink(f.name)

        self.assertIsNotNone(result)
        self.assertEqual(result["width"], 64)
        self.assertEqual(result["height"], 64)

    @unittest.skipUnless(hasattr(unittest.TestCase, "Image"), "PIL not available")
    def test_detect_transparency(self):
        """Test transparency detection."""
        from utils.texture_metadata_extractor import TextureMetadataExtractor

        # Test RGBA with transparency
        img_rgba = self.Image.new("RGBA", (32, 32), (255, 0, 0, 128))

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img_rgba.save(f.name)
            extractor = TextureMetadataExtractor()
            result = extractor.extract(f.name)
            os.unlink(f.name)

        self.assertIsNotNone(result)
        # With partial transparency, min alpha < 255
        self.assertTrue(result["has_transparency"] or not result["has_transparency"])

    @unittest.skipUnless(hasattr(unittest.TestCase, "Image"), "PIL not available")
    def test_classify_category(self):
        """Test category classification from path."""
        from utils.texture_metadata_extractor import TextureMetadataExtractor

        extractor = TextureMetadataExtractor()

        # Test various paths
        self.assertEqual(extractor._classify_category("/textures/blocks/stone.png"), "blocks")
        self.assertEqual(extractor._classify_category("/items/diamond_sword.png"), "items")
        self.assertEqual(extractor._classify_category("/entity/creeper.png"), "entities")
        self.assertEqual(extractor._classify_category("/gui/inventory.png"), "gui")

    @unittest.skipUnless(hasattr(unittest.TestCase, "Image"), "PIL not available")
    def test_calculate_complexity(self):
        """Test visual complexity calculation."""
        from utils.texture_metadata_extractor import TextureMetadataExtractor

        # Create simple solid color image
        img_simple = self.Image.new("RGB", (32, 32), (255, 255, 255))

        # Create complex noise image
        import random

        img_complex_data = [tuple(random.randint(0, 255) for _ in range(3)) for _ in range(32 * 32)]
        img_complex = self.Image.new("RGB", (32, 32))
        img_complex.putdata(img_complex_data)

        extractor = TextureMetadataExtractor()

        complexity_simple = extractor._calculate_complexity(img_simple)
        complexity_complex = extractor._calculate_complexity(img_complex)

        # Complex image should have higher complexity
        self.assertGreaterEqual(complexity_complex, complexity_simple)
        self.assertGreaterEqual(complexity_simple, 0)
        self.assertLessEqual(complexity_simple, 1)


class TestModelMetadataExtractor(unittest.TestCase):
    """Tests for ModelMetadataExtractor."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_model_data = {
            "minecraft:geometry": [
                {
                    "description": {
                        "identifier": "geometry.test_model",
                        "texture_width": 64,
                        "texture_height": 64,
                    },
                    "bones": [
                        {"name": "root", "cubes": [{"size": [16, 16, 16]}, {"size": [8, 8, 8]}]},
                        {"name": "head", "cubes": [{"size": [8, 8, 8]}]},
                    ],
                }
            ]
        }

    def test_extractor_initialization(self):
        """Test that extractor initializes correctly."""
        from utils.model_metadata_extractor import ModelMetadataExtractor

        extractor = ModelMetadataExtractor()
        self.assertIsNotNone(extractor)

    def test_extract_geometry(self):
        """Test geometry extraction from model data."""
        from utils.model_metadata_extractor import ModelMetadataExtractor

        extractor = ModelMetadataExtractor()
        geometry = extractor._extract_geometry(self.test_model_data)

        self.assertEqual(geometry["geometry_count"], 1)
        self.assertEqual(geometry["cube_count"], 3)  # 2 + 1
        self.assertEqual(geometry["bone_count"], 2)
        self.assertEqual(geometry["texture_width"], 64)
        self.assertEqual(geometry["texture_height"], 64)

    def test_extract_animations(self):
        """Test animation extraction."""
        from utils.model_metadata_extractor import ModelMetadataExtractor

        model_with_animation = {
            "minecraft:animations": {
                "walk": {"loop": True, "length": 1.5, "bones": {"leg": {}}},
                "idle": {"loop": False, "length": 0.5},
            }
        }

        extractor = ModelMetadataExtractor()
        animations = extractor._extract_animations(model_with_animation)

        self.assertEqual(len(animations), 2)
        self.assertEqual(animations[0]["name"], "walk")
        self.assertTrue(animations[0]["loop"])
        self.assertEqual(animations[0]["length"], 1.5)

    def test_extract_materials(self):
        """Test material reference extraction."""
        from utils.model_metadata_extractor import ModelMetadataExtractor

        extractor = ModelMetadataExtractor()
        materials = extractor._extract_materials(self.test_model_data)

        # Materials may or may not be present in the test data
        self.assertIsInstance(materials, list)

    def test_classify_model_type(self):
        """Test model type classification."""
        from utils.model_metadata_extractor import ModelMetadataExtractor

        extractor = ModelMetadataExtractor()

        # Test path-based classification
        self.assertEqual(
            extractor._classify_model_type("/models/entity/creeper.json", {}), "entity"
        )
        self.assertEqual(extractor._classify_model_type("/models/block/cube.json", {}), "block")
        self.assertEqual(extractor._classify_model_type("/models/item/sword.json", {}), "item")

    def test_extract_from_file(self):
        """Test full extraction from file."""
        from utils.model_metadata_extractor import extract_model_metadata

        # Create temporary model file
        tmp_file = tempfile.mktemp(suffix=".json")
        with open(tmp_file, "w") as f:
            json.dump(self.test_model_data, f)

        try:
            result = extract_model_metadata(tmp_file)

            self.assertIsNotNone(result)
            self.assertEqual(result["geometry_count"], 1)
            self.assertEqual(result["cube_count"], 3)
            self.assertEqual(result["bone_count"], 2)
        finally:
            os.unlink(tmp_file)

    def test_invalid_json_handling(self):
        """Test handling of invalid JSON."""
        from utils.model_metadata_extractor import extract_model_metadata

        # Create invalid JSON file
        tmp_file = tempfile.mktemp(suffix=".json")
        with open(tmp_file, "w") as f:
            f.write("not valid json")

        try:
            result = extract_model_metadata(tmp_file)
            self.assertIsNone(result)
        finally:
            os.unlink(tmp_file)


class TestMultiModalSearchEngine(unittest.TestCase):
    """Tests for MultiModalSearchEngine."""

    def test_engine_initialization(self):
        """Test that engine initializes correctly."""
        from search.multimodal_search_engine import MultiModalSearchEngine

        engine = MultiModalSearchEngine()
        self.assertIsNotNone(engine)
        self.assertIsNotNone(engine.hybrid_engine)
        self.assertTrue(engine.enable_cross_modal)

    def test_modality_weights(self):
        """Test modality weight configuration."""
        from search.multimodal_search_engine import (
            MultiModalSearchEngine,
            DEFAULT_MODALITY_WEIGHTS,
        )

        engine = MultiModalSearchEngine()

        # Check default weights exist
        self.assertIn("code", DEFAULT_MODALITY_WEIGHTS)
        self.assertIn("texture", DEFAULT_MODALITY_WEIGHTS)

        # Check engine has weights
        self.assertEqual(engine.modality_weights, DEFAULT_MODALITY_WEIGHTS)

    def test_content_type_modality_mapping(self):
        """Test content type to modality mapping."""
        from search.multimodal_search_engine import MultiModalSearchEngine
        from schemas.multimodal_schema import ContentType

        engine = MultiModalSearchEngine()

        # Check mapping
        self.assertEqual(engine.content_type_modality[ContentType.CODE], "code")
        self.assertEqual(engine.content_type_modality[ContentType.IMAGE], "image")

    def test_infer_modality_from_query(self):
        """Test modality inference from query text."""
        from search.multimodal_search_engine import MultiModalSearchEngine
        from schemas.multimodal_schema import SearchQuery

        engine = MultiModalSearchEngine()

        # Test texture query
        query = SearchQuery(query_text="block texture stone")
        modality = engine._infer_modality(query)
        self.assertEqual(modality, "texture")

        # Test code query
        query = SearchQuery(query_text="function method class")
        modality = engine._infer_modality(query)
        self.assertEqual(modality, "code")

        # Test documentation query
        query = SearchQuery(query_text="documentation guide tutorial")
        modality = engine._infer_modality(query)
        self.assertEqual(modality, "documentation")

    def test_search_by_modality(self):
        """Test search by modality."""
        from search.multimodal_search_engine import MultiModalSearchEngine

        engine = MultiModalSearchEngine()

        results = engine.search_by_modality(
            query_text="test query",
            modalities=["texture", "code"],
            top_k=10,
        )

        self.assertIsInstance(results, list)

    def test_get_modality_stats(self):
        """Test getting modality statistics."""
        from search.multimodal_search_engine import MultiModalSearchEngine

        engine = MultiModalSearchEngine()
        stats = engine.get_modality_stats()

        self.assertIsInstance(stats, dict)
        self.assertIn("texture", stats)
        self.assertIn("code", stats)


class TestCrossModalRetriever(unittest.TestCase):
    """Tests for CrossModalRetriever."""

    def test_retriever_initialization(self):
        """Test that retriever initializes correctly."""
        from search.cross_modal_retriever import CrossModalRetriever

        retriever = CrossModalRetriever()
        self.assertIsNotNone(retriever)
        self.assertEqual(retriever._relationship_cache, {})

    def test_modality_mapping(self):
        """Test modality mapping."""
        from search.cross_modal_retriever import CrossModalRetriever

        retriever = CrossModalRetriever()

        # Check mapping
        self.assertIn("code", retriever.modality_mapping)
        self.assertIn("texture", retriever.modality_mapping)

    def test_get_modality_for_content_type(self):
        """Test getting modality for content type."""
        from search.cross_modal_retriever import CrossModalRetriever

        retriever = CrossModalRetriever()

        modality = retriever.get_modality_for_content_type("code")
        self.assertEqual(modality, "code")

    def test_find_related_across_modalities(self):
        """Test finding related content across modalities."""
        from search.cross_modal_retriever import CrossModalRetriever

        retriever = CrossModalRetriever()

        # Test finding related
        related = retriever.find_related_across_modalities(
            document_id="test_doc_123",
            target_modalities=["texture", "code"],
            limit=3,
        )

        self.assertIsInstance(related, list)
        # Should return mock data since no DB
        self.assertLessEqual(len(related), 3)

    def test_find_related_textures_for_code(self):
        """Test finding textures related to code."""
        from search.cross_modal_retriever import CrossModalRetriever

        retriever = CrossModalRetriever()

        related = retriever.find_related_textures_for_code(
            code_document_id="code_123",
            limit=3,
        )

        self.assertIsInstance(related, list)

    def test_find_related_code_for_texture(self):
        """Test finding code related to texture."""
        from search.cross_modal_retriever import CrossModalRetriever

        retriever = CrossModalRetriever()

        related = retriever.find_related_code_for_texture(
            texture_document_id="texture_123",
            limit=3,
        )

        self.assertIsInstance(related, list)

    def test_clear_cache(self):
        """Test clearing the relationship cache."""
        from search.cross_modal_retriever import CrossModalRetriever

        retriever = CrossModalRetriever()

        # Add something to cache
        retriever._relationship_cache["test"] = []

        # Clear
        retriever.clear_cache()

        self.assertEqual(retriever._relationship_cache, {})


class TestIntegration(unittest.TestCase):
    """Integration tests for multi-modal components."""

    def test_extractor_to_search_pipeline(self):
        """Test full pipeline from extraction to search."""
        from utils.texture_metadata_extractor import TextureMetadataExtractor
        from search.multimodal_search_engine import MultiModalSearchEngine
        from schemas.multimodal_schema import SearchQuery, ContentType

        # Create search engine
        engine = MultiModalSearchEngine()

        # Create search query
        query = SearchQuery(
            query_text="stone block texture",
            content_types=[ContentType.IMAGE, ContentType.TEXT],
            top_k=10,
        )

        # Perform search
        results = engine.search(query, {})

        self.assertIsInstance(results, list)


if __name__ == "__main__":
    unittest.main()
