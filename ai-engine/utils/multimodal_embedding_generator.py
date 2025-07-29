"""
Multi-modal embedding generator for the advanced RAG system.

This module provides enhanced embedding generation capabilities for different
content types including text, code, images, and multi-modal combinations.
"""

import os
import logging
import hashlib
from typing import List, Dict, Any, Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np
from pathlib import Path

# Import the existing embedding generator as base
from utils.embedding_generator import EmbeddingGenerator
from utils.advanced_chunker import Chunk, ChunkType

logger = logging.getLogger(__name__)


class EmbeddingStrategy(str, Enum):
    """Strategies for generating embeddings."""
    TEXT_ONLY = "text_only"
    CODE_SPECIALIZED = "code_specialized"
    MULTIMODAL = "multimodal"
    HYBRID = "hybrid"
    CONTEXT_AWARE = "context_aware"


@dataclass
class EmbeddingResult:
    """Result of embedding generation with metadata."""
    embedding: np.ndarray
    model_used: str
    strategy: EmbeddingStrategy
    confidence: Optional[float] = None
    processing_time_ms: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class CodeAwareEmbeddingGenerator:
    """
    Embedding generator specialized for code content.
    
    This generator understands programming language structures and can
    create more meaningful embeddings for code snippets.
    """
    
    def __init__(self):
        self.base_generator = EmbeddingGenerator()
        self.code_keywords = self._load_code_keywords()
        self.java_patterns = self._load_java_patterns()
    
    def _load_code_keywords(self) -> Dict[str, List[str]]:
        """Load programming language keywords and common patterns."""
        return {
            'java': [
                'class', 'interface', 'extends', 'implements', 'public', 'private', 'protected',
                'static', 'final', 'abstract', 'synchronized', 'volatile', 'transient',
                'import', 'package', 'new', 'instanceof', 'throw', 'throws', 'try', 'catch',
                'finally', 'if', 'else', 'switch', 'case', 'default', 'for', 'while', 'do',
                'break', 'continue', 'return', 'void', 'int', 'long', 'float', 'double',
                'boolean', 'char', 'byte', 'short', 'String', 'Object', 'ArrayList', 'HashMap'
            ],
            'minecraft': [
                'Block', 'Item', 'Entity', 'World', 'Player', 'Registry', 'Material',
                'BlockState', 'ItemStack', 'EntityType', 'Biome', 'Dimension', 'Chunk',
                'Recipe', 'CraftingRecipe', 'SmeltingRecipe', 'GameRegistry', 'ModBlocks',
                'ModItems', 'ModEntities', 'ClientProxy', 'ServerProxy', 'EventHandler',
                'SubscribeEvent', 'Mod', 'EventBusSubscriber', 'OnlyIn', 'Side', 'SideOnly'
            ]
        }
    
    def _load_java_patterns(self) -> Dict[str, str]:
        """Load common Java/Minecraft coding patterns."""
        return {
            'class_declaration': r'(?:public|private|protected)?\s*(?:static|final|abstract)?\s*class\s+(\w+)',
            'method_declaration': r'(?:public|private|protected)?\s*(?:static|final)?\s*\w+\s+(\w+)\s*\([^)]*\)',
            'field_declaration': r'(?:public|private|protected)?\s*(?:static|final)?\s*\w+\s+(\w+)\s*[=;]',
            'minecraft_registry': r'(?:GameRegistry|Registry)\.register\w*\(',
            'minecraft_block': r'new\s+Block\s*\(',
            'minecraft_item': r'new\s+Item\s*\(',
            'event_handler': r'@(?:EventHandler|SubscribeEvent)',
            'mod_annotation': r'@Mod\s*\('
        }
    
    async def generate_code_embedding(self, chunk: Chunk) -> EmbeddingResult:
        """
        Generate embedding for code content with enhanced context.
        
        Args:
            chunk: Code chunk to embed
            
        Returns:
            Enhanced embedding result with code-specific metadata
        """
        import time
        start_time = time.time()
        
        # Enhance the code content with context
        enhanced_content = self._enhance_code_context(chunk)
        
        # Generate base embedding
        embeddings = await self.base_generator.generate_embeddings([enhanced_content])
        
        if not embeddings or embeddings[0] is None:
            logger.error(f"Failed to generate embedding for code chunk: {chunk.chunk_id}")
            return None
        
        processing_time = (time.time() - start_time) * 1000
        
        # Calculate confidence based on code complexity and keywords
        confidence = self._calculate_code_confidence(chunk)
        
        return EmbeddingResult(
            embedding=embeddings[0],
            model_used=self.base_generator.model_name,
            strategy=EmbeddingStrategy.CODE_SPECIALIZED,
            confidence=confidence,
            processing_time_ms=processing_time,
            metadata={
                'chunk_type': chunk.chunk_type,
                'code_features': self._extract_code_features(chunk),
                'enhanced_content_length': len(enhanced_content),
                'original_content_length': len(chunk.content)
            }
        )
    
    def _enhance_code_context(self, chunk: Chunk) -> str:
        """Enhance code chunk with additional context."""
        content = chunk.content
        
        # Add type information
        if chunk.chunk_type == ChunkType.CODE_CLASS:
            content = f"Java class definition: {content}"
        elif chunk.chunk_type == ChunkType.CODE_METHOD:
            content = f"Java method implementation: {content}"
        
        # Add metadata context
        if chunk.metadata:
            if 'class_name' in chunk.metadata:
                content = f"Class: {chunk.metadata['class_name']}\n{content}"
            if 'method_name' in chunk.metadata:
                content = f"Method: {chunk.metadata['method_name']}\n{content}"
            if 'package_name' in chunk.metadata:
                content = f"Package: {chunk.metadata['package_name']}\n{content}"
        
        # Add Minecraft-specific context if detected
        minecraft_features = self._detect_minecraft_features(chunk.content)
        if minecraft_features:
            context_info = f"Minecraft mod code with features: {', '.join(minecraft_features)}\n"
            content = context_info + content
        
        return content
    
    def _detect_minecraft_features(self, code: str) -> List[str]:
        """Detect Minecraft-specific features in code."""
        features = []
        
        for pattern_name, pattern in self.java_patterns.items():
            if pattern_name.startswith('minecraft_'):
                import re
                if re.search(pattern, code):
                    features.append(pattern_name.replace('minecraft_', ''))
        
        # Check for Minecraft keywords
        minecraft_keywords = self.code_keywords.get('minecraft', [])
        for keyword in minecraft_keywords:
            if keyword in code:
                features.append(f"uses_{keyword.lower()}")
        
        return list(set(features))  # Remove duplicates
    
    def _extract_code_features(self, chunk: Chunk) -> Dict[str, Any]:
        """Extract features from code chunk."""
        content = chunk.content
        
        features = {
            'line_count': len(content.split('\n')),
            'character_count': len(content),
            'has_comments': '//' in content or '/*' in content,
            'has_annotations': '@' in content,
            'brace_count': content.count('{'),
            'semicolon_count': content.count(';'),
            'import_count': content.count('import '),
            'method_calls': len([line for line in content.split('\n') if '(' in line and ')' in line]),
        }
        
        # Language-specific features
        java_keywords = self.code_keywords.get('java', [])
        features['java_keyword_count'] = sum(content.count(keyword) for keyword in java_keywords)
        
        minecraft_keywords = self.code_keywords.get('minecraft', [])
        features['minecraft_keyword_count'] = sum(content.count(keyword) for keyword in minecraft_keywords)
        
        return features
    
    def _calculate_code_confidence(self, chunk: Chunk) -> float:
        """Calculate confidence score for code embedding."""
        features = self._extract_code_features(chunk)
        
        # Base confidence
        confidence = 0.5
        
        # Boost confidence for well-structured code
        if features.get('brace_count', 0) > 0:
            confidence += 0.1
        
        if features.get('java_keyword_count', 0) > 0:
            confidence += 0.2
        
        if features.get('minecraft_keyword_count', 0) > 0:
            confidence += 0.2
        
        # Adjust based on chunk type
        if chunk.chunk_type in [ChunkType.CODE_CLASS, ChunkType.CODE_METHOD]:
            confidence += 0.1
        
        return min(confidence, 1.0)


class ImageEmbeddingGenerator:
    """
    Embedding generator for image content.
    
    This generator handles texture files and other visual assets
    commonly found in Minecraft mods.
    """
    
    def __init__(self):
        self.supported_formats = {'.png', '.jpg', '.jpeg', '.gif', '.bmp'}
        self.texture_categories = {
            'blocks': ['block', 'blocks'],
            'items': ['item', 'items'],
            'entities': ['entity', 'entities', 'mobs'],
            'gui': ['gui', 'interface', 'ui'],
            'environment': ['environment', 'sky', 'particle']
        }
    
    async def generate_image_embedding(self, image_path: str, metadata: Dict[str, Any] = None) -> Optional[EmbeddingResult]:
        """
        Generate embedding for image content.
        
        Args:
            image_path: Path to the image file
            metadata: Additional metadata about the image
            
        Returns:
            Image embedding result
        """
        import time
        start_time = time.time()
        
        try:
            # For now, use a mock implementation
            # In a real implementation, you would use a model like CLIP or OpenCLIP
            mock_embedding = np.random.rand(512)  # 512-dimensional mock embedding
            
            processing_time = (time.time() - start_time) * 1000
            
            # Analyze image properties
            image_features = self._extract_image_features(image_path, metadata)
            
            return EmbeddingResult(
                embedding=mock_embedding,
                model_used="mock_clip_model",
                strategy=EmbeddingStrategy.MULTIMODAL,
                confidence=0.8,  # Mock confidence
                processing_time_ms=processing_time,
                metadata={
                    'image_path': image_path,
                    'image_features': image_features,
                    'texture_category': self._classify_texture(image_path, metadata)
                }
            )
            
        except Exception as e:
            logger.error(f"Error generating image embedding for {image_path}: {e}")
            return None
    
    def _extract_image_features(self, image_path: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Extract features from image file."""
        path = Path(image_path)
        
        features = {
            'filename': path.name,
            'extension': path.suffix.lower(),
            'directory': path.parent.name,
            'file_size': path.stat().st_size if path.exists() else 0
        }
        
        # Add metadata if available
        if metadata:
            features.update(metadata)
        
        # Detect animation from filename
        if 'anim' in path.name.lower() or '_' in path.stem and path.stem.split('_')[-1].isdigit():
            features['possibly_animated'] = True
        
        return features
    
    def _classify_texture(self, image_path: str, metadata: Dict[str, Any] = None) -> str:
        """Classify the type of texture based on path and metadata."""
        path_lower = image_path.lower()
        
        for category, keywords in self.texture_categories.items():
            if any(keyword in path_lower for keyword in keywords):
                return category
        
        if metadata and 'texture_category' in metadata:
            return metadata['texture_category']
        
        return 'unknown'


class MultiModalEmbeddingGenerator:
    """
    Main multi-modal embedding generator that coordinates different embedding strategies.
    
    This class automatically selects the appropriate embedding strategy based on
    content type and combines different modalities when needed.
    """
    
    def __init__(self):
        self.text_generator = EmbeddingGenerator()
        self.code_generator = CodeAwareEmbeddingGenerator()
        self.image_generator = ImageEmbeddingGenerator()
        
    async def generate_embedding(
        self, 
        content: Union[str, Chunk, Dict[str, Any]], 
        strategy: EmbeddingStrategy = EmbeddingStrategy.HYBRID
    ) -> Optional[EmbeddingResult]:
        """
        Generate embedding using the specified strategy.
        
        Args:
            content: Content to embed (string, chunk, or multi-modal dict)
            strategy: Embedding strategy to use
            
        Returns:
            Embedding result with metadata
        """
        if isinstance(content, str):
            return await self._generate_text_embedding(content, strategy)
        elif isinstance(content, Chunk):
            return await self._generate_chunk_embedding(content, strategy)
        elif isinstance(content, dict):
            return await self._generate_multimodal_embedding(content, strategy)
        else:
            logger.error(f"Unsupported content type: {type(content)}")
            return None
    
    async def _generate_text_embedding(self, text: str, strategy: EmbeddingStrategy) -> EmbeddingResult:
        """Generate embedding for plain text."""
        import time
        start_time = time.time()
        
        embeddings = await self.text_generator.generate_embeddings([text])
        
        if embeddings is None or len(embeddings) == 0:
            logger.error("Failed to generate text embedding")
            return None
        
        processing_time = (time.time() - start_time) * 1000
        
        return EmbeddingResult(
            embedding=embeddings[0],
            model_used=self.text_generator.model_name,
            strategy=strategy,
            confidence=0.7,  # Default confidence for text
            processing_time_ms=processing_time,
            metadata={'content_type': 'text', 'content_length': len(text)}
        )
    
    async def _generate_chunk_embedding(self, chunk: Chunk, strategy: EmbeddingStrategy) -> EmbeddingResult:
        """Generate embedding for a structured chunk."""
        if chunk.chunk_type in [ChunkType.CODE_CLASS, ChunkType.CODE_METHOD, ChunkType.CODE_BLOCK]:
            return await self.code_generator.generate_code_embedding(chunk)
        else:
            # Use text embedding for other chunk types
            return await self._generate_text_embedding(chunk.content, EmbeddingStrategy.TEXT_ONLY)
    
    async def _generate_multimodal_embedding(
        self, 
        content_dict: Dict[str, Any], 
        strategy: EmbeddingStrategy
    ) -> Optional[EmbeddingResult]:
        """
        Generate embedding for multi-modal content.
        
        Args:
            content_dict: Dictionary containing different types of content
                         (e.g., {'text': '...', 'image_path': '...', 'metadata': {...}})
            strategy: Embedding strategy
            
        Returns:
            Combined multi-modal embedding
        """
        import time
        start_time = time.time()
        
        embeddings = []
        metadata_combined = {}
        
        # Process text content
        if 'text' in content_dict and content_dict['text']:
            text_result = await self._generate_text_embedding(content_dict['text'], EmbeddingStrategy.TEXT_ONLY)
            if text_result:
                embeddings.append(('text', text_result.embedding, text_result.confidence))
                metadata_combined['text_metadata'] = text_result.metadata
        
        # Process image content
        if 'image_path' in content_dict and content_dict['image_path']:
            image_result = await self.image_generator.generate_image_embedding(
                content_dict['image_path'], 
                content_dict.get('metadata', {})
            )
            if image_result:
                embeddings.append(('image', image_result.embedding, image_result.confidence))
                metadata_combined['image_metadata'] = image_result.metadata
        
        # Process code content
        if 'code' in content_dict and content_dict['code']:
            # Create a temporary chunk for code processing
            from utils.advanced_chunker import Chunk, ChunkType
            code_chunk = Chunk(
                content=content_dict['code'],
                chunk_type=ChunkType.CODE_BLOCK,
                metadata=content_dict.get('metadata', {})
            )
            code_result = await self.code_generator.generate_code_embedding(code_chunk)
            if code_result:
                embeddings.append(('code', code_result.embedding, code_result.confidence))
                metadata_combined['code_metadata'] = code_result.metadata
        
        if not embeddings:
            logger.error("No valid embeddings generated for multi-modal content")
            return None
        
        # Combine embeddings using weighted average
        combined_embedding = self._combine_embeddings(embeddings)
        
        processing_time = (time.time() - start_time) * 1000
        
        # Calculate overall confidence
        confidences = [conf for _, _, conf in embeddings if conf is not None]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5
        
        return EmbeddingResult(
            embedding=combined_embedding,
            model_used="multimodal_combination",
            strategy=EmbeddingStrategy.MULTIMODAL,
            confidence=avg_confidence,
            processing_time_ms=processing_time,
            metadata={
                'modalities': [mod for mod, _, _ in embeddings],
                'embedding_count': len(embeddings),
                **metadata_combined
            }
        )
    
    def _combine_embeddings(self, embeddings: List[Tuple[str, np.ndarray, float]]) -> np.ndarray:
        """
        Combine multiple embeddings into a single representation.
        
        Args:
            embeddings: List of (modality, embedding, confidence) tuples
            
        Returns:
            Combined embedding vector
        """
        if len(embeddings) == 1:
            return embeddings[0][1]
        
        # Normalize all embeddings to the same dimension
        # For simplicity, we'll use the dimension of the first embedding
        target_dim = len(embeddings[0][1])
        
        # Weighted combination based on confidence
        total_weight = 0
        combined = np.zeros(target_dim)
        
        for modality, embedding, confidence in embeddings:
            # Resize embedding if needed (simple truncation or padding)
            if len(embedding) > target_dim:
                embedding = embedding[:target_dim]
            elif len(embedding) < target_dim:
                padding = np.zeros(target_dim - len(embedding))
                embedding = np.concatenate([embedding, padding])
            
            weight = confidence if confidence is not None else 0.5
            combined += embedding * weight
            total_weight += weight
        
        if total_weight > 0:
            combined /= total_weight
        
        return combined
    
    async def batch_generate_embeddings(
        self, 
        contents: List[Union[str, Chunk, Dict[str, Any]]], 
        strategy: EmbeddingStrategy = EmbeddingStrategy.HYBRID
    ) -> List[Optional[EmbeddingResult]]:
        """
        Generate embeddings for multiple content items in batch.
        
        Args:
            contents: List of content items to embed
            strategy: Embedding strategy to use
            
        Returns:
            List of embedding results
        """
        results = []
        
        for content in contents:
            result = await self.generate_embedding(content, strategy)
            results.append(result)
        
        logger.info(f"Generated {len([r for r in results if r is not None])} embeddings out of {len(contents)} items")
        return results