"""
Online Research Analysis Agent

This agent implements Mode 2 of the AI-Powered Validation & Comparison system.
It accepts URLs to CurseForge/Modrinth/YouTube for original mod content,
performs multimodal analysis, generates feature checklists, and validates
the converted addon against the checklist.

Issue: #495 (Phase 4b)
"""

import os
import json
import re
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SourceType(Enum):
    """Types of sources for online research."""
    CURSEFORGE = "curseforge"
    MODRINTH = "modrinth"
    YOUTUBE = "youtube"
    GENERIC_URL = "generic_url"
    UNKNOWN = "unknown"


@dataclass
class ResearchSource:
    """Represents a research source URL."""
    url: str
    source_type: SourceType
    title: str
    description: str
    metadata: Dict[str, Any]
    fetched_at: datetime


@dataclass
class FeatureChecklistItem:
    """A single feature in the checklist."""
    feature_name: str
    description: str
    category: str
    priority: str  # high, medium, low
    detected: bool
    evidence: List[str]
    validation_status: str  # verified, missing, unclear


@dataclass
class ValidationReport:
    """Report from validating converted addon against research."""
    overall_score: float
    feature_checklist: List[FeatureChecklistItem]
    verified_features: List[str]
    missing_features: List[str]
    unclear_features: List[str]
    recommendations: List[str]
    research_sources: List[ResearchSource]


class URLAnalyzer:
    """Analyzes URLs to determine source type and extract information."""
    
    def __init__(self):
        self.source_patterns = {
            SourceType.CURSEFORGE: [
                r'curseforge\.com/minecraft/mc-mods/([^/]+)',
                r'curseforge\.com/minecraft/modpacks/([^/]+)'
            ],
            SourceType.MODRINTH: [
                r'modrinth\.com/mod/([^/]+)',
                r'modrinth\.com/modpack/([^/]+)'
            ],
            SourceType.YOUTUBE: [
                r'youtube\.com/watch\?v=([^&]+)',
                r'youtu\.be/([^/]+)'
            ]
        }
    
    def analyze_url(self, url: str) -> SourceType:
        """Determine the type of URL."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        if 'curseforge' in domain:
            return SourceType.CURSEFORGE
        elif 'modrinth' in domain:
            return SourceType.MODRINTH
        elif 'youtube' in domain or 'youtu.be' in domain:
            return SourceType.YOUTUBE
        
        return SourceType.GENERIC_URL
    
    def extract_identifier(self, url: str, source_type: SourceType) -> Optional[str]:
        """Extract the mod/pack identifier from URL."""
        for pattern in self.source_patterns.get(source_type, []):
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None


class CurseForgeClient:
    """Client for fetching data from CurseForge API."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get('CURSEFORGE_API_KEY', '')
        self.base_url = "https://api.curseforge.com/v1"
        self.headers = {
            'Accept': 'application/json',
            'x-api-key': self.api_key
        } if self.api_key else {}
    
    def get_mod_info(self, mod_id: str) -> Dict:
        """Fetch mod information from CurseForge."""
        print(f"Fetching CurseForge mod info for: {mod_id}")
        
        # In production, would call actual API
        # For now, return mock data
        return {
            "id": mod_id,
            "name": "Example Mod",
            "summary": "A sample mod for testing",
            "description": "This mod adds various features...",
            "categories": [{"name": "Mechanics"}, {"name": "Tools"}],
            "latestFiles": [{"fileName": "mod-1.0.jar", "gameVersion": ["1.20.4"]}],
            "downloadCount": 10000
        }
    
    def get_mod_files(self, mod_id: str) -> List[Dict]:
        """Fetch mod files from CurseForge."""
        print(f"Fetching CurseForge files for: {mod_id}")
        
        # Mock response
        return [
            {
                "id": "file_1",
                "displayName": "mod-1.0.jar",
                "gameVersion": "1.20.4",
                "releaseType": "release",
                "downloadUrl": f"https://curseforge.com/minecraft/mc-mods/{mod_id}/download"
            },
            {
                "id": "file_2", 
                "displayName": "mod-1.1.jar",
                "gameVersion": "1.20.4",
                "releaseType": "release",
                "downloadUrl": f"https://curseforge.com/minecraft/mc-mods/{mod_id}/download"
            }
        ]
    
    def is_available(self) -> bool:
        """Check if API is available."""
        return bool(self.api_key)


class ModrinthClient:
    """Client for fetching data from Modrinth API."""
    
    def __init__(self):
        self.base_url = "https://api.modrinth.com/v2"
        self.headers = {'Accept': 'application/json'}
    
    def get_mod_info(self, mod_id: str) -> Dict:
        """Fetch mod information from Modrinth."""
        print(f"Fetching Modrinth mod info for: {mod_id}")
        
        # Mock response
        return {
            "id": mod_id,
            "title": "Example Mod",
            "description": "A sample mod for testing",
            "categories": ["mechanics", "tools"],
            "versions": ["1.20.4", "1.20.1"],
            "downloads": 5000
        }
    
    def get_mod_versions(self, mod_id: str) -> List[Dict]:
        """Fetch mod versions from Modrinth."""
        print(f"Fetching Modrinth versions for: {mod_id}")
        
        return [
            {
                "id": "version_1",
                "version_number": "1.0.0",
                "game_versions": ["1.20.4"],
                "loaders": ["fabric", "forge"]
            }
        ]
    
    def is_available(self) -> bool:
        """Check if API is available."""
        return True


class YouTubeAnalyzer:
    """Analyzer for YouTube content."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get('YOUTUBE_API_KEY', '')
        self.youtube_regex = r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})'
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from URL."""
        match = re.search(self.youtube_regex, url)
        return match.group(1) if match else None
    
    def get_video_info(self, video_id: str) -> Dict:
        """Fetch video information from YouTube."""
        print(f"Fetching YouTube video info for: {video_id}")
        
        # In production, would call YouTube API
        # Mock response
        return {
            "video_id": video_id,
            "title": "Mod Showcase Video",
            "description": "This video demonstrates the features of the mod...",
            "thumbnail_url": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
            "duration_seconds": 300,
            "channel_name": "Example Channel"
        }
    
    def extract_features_from_description(self, description: str) -> List[str]:
        """Extract feature mentions from video description."""
        features = []
        
        # Common feature patterns
        patterns = [
            r'(?:adds?|introduces?|features?)\s+([^\.]+)',
            r'(?:new|custom)\s+(\w+(?:\s+\w+)?)',
            r'(\w+)\s+(?:feature|mechanic|system)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, description, re.IGNORECASE)
            features.extend(matches)
        
        return list(set(features))[:10]  # Limit to 10 features
    
    def is_available(self) -> bool:
        """Check if API is available."""
        return True


class MultimodalAnalyzer:
    """Performs multimodal analysis on research content."""
    
    def __init__(self):
        # In production, would use actual LLM vision capabilities
        pass
    
    def analyze_image(self, image_url: str) -> Dict:
        """Analyze an image for feature detection."""
        print(f"Analyzing image: {image_url}")
        
        # Mock analysis
        return {
            "detected_elements": ["block", "item", "UI element"],
            "colors": ["#FF0000", "#00FF00", "#0000FF"],
            "text_detected": False,
            "confidence": 0.85
        }
    
    def analyze_video_frame(self, frame_data: bytes) -> Dict:
        """Analyze a video frame for features."""
        # Mock analysis
        return {
            "detected_gameplay": "building",
            "detected_items": ["stone", "wood"],
            "detected_entities": ["player"],
            "confidence": 0.78
        }
    
    def extract_features_from_text(self, text: str) -> List[str]:
        """Extract feature descriptions from text."""
        features = []
        
        # Common mod feature keywords
        feature_keywords = [
            'custom block', 'custom item', 'new dimension', 'new biome',
            'crafting recipe', 'smelting', 'breeding', 'spawning',
            'generation', 'structure', 'entity', 'tile entity',
            'texture', 'model', 'sound', 'particle', 'effect',
            'quest', 'achievement', 'skill', 'magic', 'tech'
        ]
        
        text_lower = text.lower()
        for keyword in feature_keywords:
            if keyword in text_lower:
                features.append(keyword)
        
        return list(set(features))


class FeatureChecklistGenerator:
    """Generates feature checklists from research data."""
    
    def __init__(self):
        self.feature_categories = {
            "blocks": ["custom block", "tile entity", "block state"],
            "items": ["custom item", "tool", "armor", "food", "potion"],
            "entities": ["mob", "entity", "projectile", "vehicle"],
            "world": ["dimension", "biome", "structure", "ore generation"],
            "mechanics": ["crafting", "smelting", "breeding", "enchanting"],
            "ui": ["gui", "screen", "inventory", "hud"],
            "audio": ["sound", "music", "ambient"],
            "visuals": ["particle", "effect", "texture", "model"]
        }
    
    def generate_checklist(
        self,
        research_data: Dict,
        source_type: SourceType
    ) -> List[FeatureChecklistItem]:
        """Generate a feature checklist from research data."""
        print("Generating feature checklist...")
        
        checklist = []
        
        # Extract features from different sources
        features = []
        
        # From description
        description = research_data.get('description', '')
        features.extend(self._extract_features_from_text(description))
        
        # From categories
        categories = research_data.get('categories', [])
        features.extend(self._categorize_features(categories))
        
        # From additional metadata
        metadata_features = research_data.get('features', [])
        features.extend(metadata_features)
        
        # Deduplicate and create checklist items
        seen_features = set()
        for feature in features:
            if feature not in seen_features:
                seen_features.add(feature)
                
                # Determine category
                category = self._determine_category(feature)
                priority = self._determine_priority(feature)
                
                item = FeatureChecklistItem(
                    feature_name=feature,
                    description=f"Feature detected: {feature}",
                    category=category,
                    priority=priority,
                    detected=True,
                    evidence=["Source analysis"],
                    validation_status="unclear"
                )
                checklist.append(item)
        
        # Add default checklist items if empty
        if not checklist:
            checklist = self._create_default_checklist()
        
        print(f"Generated checklist with {len(checklist)} items")
        return checklist
    
    def _extract_features_from_text(self, text: str) -> List[str]:
        """Extract features from text."""
        features = []
        
        # Simple keyword extraction
        text_lower = text.lower()
        
        for category, keywords in self.feature_categories.items():
            for keyword in keywords:
                if keyword in text_lower:
                    features.append(keyword)
        
        return features
    
    def _categorize_features(self, categories: List[str]) -> List[str]:
        """Map categories to features."""
        features = []
        
        category_mapping = {
            "mechanics": ["crafting", "smelting", "breeding"],
            "tools": ["tool", "utility"],
            "adventure": ["dimension", "biome", "structure"],
            "mobs": ["entity", "mob", "spawning"],
            "magic": ["spell", "effect", "potion"],
            "technology": ["machine", "automation", "energy"]
        }
        
        # Normalize categories: handle both dicts (CurseForge) and strings (Modrinth)
        normalized_categories = []
        for cat in categories:
            if isinstance(cat, dict):
                # CurseForge format: {"name": "Mechanics"}
                normalized_categories.append(cat.get('name', '').lower())
            elif isinstance(cat, str):
                # Modrinth format: "mechanics"
                normalized_categories.append(cat.lower())
        
        for category in normalized_categories:
            if category in category_mapping:
                features.extend(category_mapping[category])
        
        return features
    
    def _determine_category(self, feature: str) -> str:
        """Determine the category of a feature."""
        feature_lower = feature.lower()
        
        for category, keywords in self.feature_categories.items():
            if any(kw in feature_lower for kw in keywords):
                return category
        
        return "general"
    
    def _determine_priority(self, feature: str) -> str:
        """Determine the priority of a feature."""
        feature_lower = feature.lower()
        
        high_priority = ['dimension', 'entity', 'custom block', 'custom item']
        medium_priority = ['biome', 'structure', 'crafting', 'recipe']
        
        if any(hp in feature_lower for hp in high_priority):
            return "high"
        elif any(mp in feature_lower for mp in medium_priority):
            return "medium"
        
        return "low"
    
    def _create_default_checklist(self) -> List[FeatureChecklistItem]:
        """Create a default checklist for unknown mods."""
        return [
            FeatureChecklistItem(
                feature_name="custom blocks",
                description="Custom block definitions",
                category="blocks",
                priority="high",
                detected=True,
                evidence=["Default assumption"],
                validation_status="unclear"
            ),
            FeatureChecklistItem(
                feature_name="custom items",
                description="Custom item definitions",
                category="items",
                priority="high",
                detected=True,
                evidence=["Default assumption"],
                validation_status="unclear"
            ),
            FeatureChecklistItem(
                feature_name="crafting recipes",
                description="Custom crafting recipes",
                category="mechanics",
                priority="medium",
                detected=True,
                evidence=["Default assumption"],
                validation_status="unclear"
            )
        ]


class OnlineResearchAgent:
    """
    Main agent for online research analysis.
    
    This agent:
    1. Accepts URLs from CurseForge, Modrinth, YouTube
    2. Fetches and analyzes mod/modpack information
    3. Generates feature checklists
    4. Validates converted addons against checklists
    """
    
    def __init__(
        self,
        curseforge_api_key: Optional[str] = None,
        youtube_api_key: Optional[str] = None
    ):
        self.url_analyzer = URLAnalyzer()
        self.curseforge = CurseForgeClient(curseforge_api_key)
        self.modrinth = ModrinthClient()
        self.youtube = YouTubeAnalyzer(youtube_api_key)
        self.multimodal = MultimodalAnalyzer()
        self.checklist_generator = FeatureChecklistGenerator()
        
        self.research_history: List[ResearchSource] = []
    
    def analyze_url(self, url: str) -> ResearchSource:
        """Analyze a single URL and fetch its information."""
        print(f"\nAnalyzing URL: {url}")
        
        source_type = self.url_analyzer.analyze_url(url)
        identifier = self.url_analyzer.extract_identifier(url, source_type)
        
        # Fetch data based on source type
        metadata = {}
        title = ""
        description = ""
        
        if source_type == SourceType.CURSEFORGE:
            if self.curseforge.is_available() and identifier:
                mod_info = self.curseforge.get_mod_info(identifier)
                metadata = mod_info
                title = mod_info.get('name', 'Unknown Mod')
                description = mod_info.get('description', '')
            else:
                title = "CurseForge Mod"
                description = "Mod from CurseForge (API not configured)"
        
        elif source_type == SourceType.MODRINTH:
            mod_info = self.modrinth.get_mod_info(identifier or url)
            metadata = mod_info
            title = mod_info.get('title', 'Unknown Mod')
            description = mod_info.get('description', '')
        
        elif source_type == SourceType.YOUTUBE:
            video_id = self.youtube.extract_video_id(url)
            if video_id:
                video_info = self.youtube.get_video_info(video_id)
                metadata = video_info
                title = video_info.get('title', 'YouTube Video')
                description = video_info.get('description', '')
                
                # Extract features from video description
                features = self.youtube.extract_features_from_description(description)
                metadata['extracted_features'] = features
        
        else:
            title = "External Resource"
            description = "Generic URL content"
        
        source = ResearchSource(
            url=url,
            source_type=source_type,
            title=title,
            description=description,
            metadata=metadata,
            fetched_at=datetime.now()
        )
        
        self.research_history.append(source)
        
        print(f"Source analyzed: {source_type.value} - {title}")
        
        return source
    
    def research_mod(
        self,
        urls: List[str],
        conversion_id: Optional[str] = None
    ) -> Dict:
        """
        Perform research on multiple URLs.
        
        Args:
            urls: List of URLs to research
            conversion_id: Optional conversion ID to link research
            
        Returns:
            Research data dictionary
        """
        print(f"\n{'='*60}")
        print(f"Starting Online Research for conversion: {conversion_id or 'unknown'}")
        print(f"URLs to research: {urls}")
        print(f"{'='*60}\n")
        
        research_results = {
            "conversion_id": conversion_id,
            "sources": [],
            "all_features": [],
            "categories": set(),
            "researched_at": datetime.now().isoformat()
        }
        
        # Analyze each URL
        for url in urls:
            try:
                source = self.analyze_url(url)
                research_results["sources"].append({
                    "url": source.url,
                    "type": source.source_type.value,
                    "title": source.title,
                    "description": source.description
                })
                
                # Extract features from this source
                features = self.multimodal.extract_features_from_text(
                    source.description
                )
                research_results["all_features"].extend(features)
                
                # Track categories
                if 'categories' in source.metadata:
                    research_results["categories"].update(
                        source.metadata['categories']
                    )
                
            except Exception as e:
                print(f"Error analyzing URL {url}: {e}")
        
        # Deduplicate features
        research_results["all_features"] = list(
            set(research_results["all_features"])
        )
        
        # Convert categories set to list for JSON
        research_results["categories"] = list(
            research_results["categories"]
        )
        
        print(f"\nResearch complete. Found {len(research_results['all_features'])} features")
        
        return research_results
    
    def generate_checklist(
        self,
        research_data: Dict,
        source_type: SourceType = SourceType.GENERIC_URL
    ) -> List[FeatureChecklistItem]:
        """Generate a feature checklist from research data."""
        return self.checklist_generator.generate_checklist(
            research_data,
            source_type
        )
    
    def validate_addon(
        self,
        conversion_id: str,
        bedrock_addon_path: str,
        checklist: List[FeatureChecklistItem]
    ) -> ValidationReport:
        """
        Validate a converted addon against the feature checklist.
        
        Args:
            conversion_id: ID of the conversion
            bedrock_addon_path: Path to the converted Bedrock addon
            checklist: Feature checklist to validate against
            
        Returns:
            ValidationReport with results
        """
        print(f"\nValidating addon: {bedrock_addon_path}")
        
        # Analyze addon files
        addon_features = self._analyze_addon(bedrock_addon_path)
        
        # Validate each checklist item
        verified = []
        missing = []
        unclear = []
        
        for item in checklist:
            # Check if feature is present in addon
            if self._check_feature_in_addon(item.feature_name, addon_features):
                item.validation_status = "verified"
                item.detected = True
                verified.append(item.feature_name)
            elif self._partial_match(item.feature_name, addon_features):
                item.validation_status = "unclear"
                item.evidence.append("Partial match found in addon")
                unclear.append(item.feature_name)
            else:
                item.validation_status = "missing"
                item.detected = False
                missing.append(item.feature_name)
        
        # Calculate score
        total_items = len(checklist)
        if total_items > 0:
            score = (len(verified) / total_items) * 100
        else:
            score = 0.0
        
        # Generate recommendations
        recommendations = self._generate_validation_recommendations(
            verified, missing, unclear, score
        )
        
        report = ValidationReport(
            overall_score=round(score, 2),
            feature_checklist=checklist,
            verified_features=verified,
            missing_features=missing,
            unclear_features=unclear,
            recommendations=recommendations,
            research_sources=self.research_history
        )
        
        print(f"\nValidation complete. Score: {score:.1f}%")
        print(f"Verified: {len(verified)}, Missing: {len(missing)}, Unclear: {len(unclear)}")
        
        return report
    
    def _analyze_addon(self, addon_path: str) -> Dict[str, List[str]]:
        """Analyze addon files to extract features."""
        print(f"Analyzing addon at: {addon_path}")
        
        features = {
            "blocks": [],
            "items": [],
            "recipes": [],
            "loot_tables": [],
            "functions": [],
            "entities": []
        }
        
        # In production, would parse actual addon files
        # For now, return empty structure
        # This would read JSON files from the addon
        
        return features
    
    def _check_feature_in_addon(
        self,
        feature_name: str,
        addon_features: Dict
    ) -> bool:
        """Check if a feature exists in the addon."""
        feature_lower = feature_name.lower()
        
        # Check each category
        for category, items in addon_features.items():
            if any(feature_lower in item.lower() for item in items):
                return True
        
        return False
    
    def _partial_match(
        self,
        feature_name: str,
        addon_features: Dict
    ) -> bool:
        """Check for partial matches."""
        feature_words = feature_name.split()
        
        for category, items in addon_features.items():
            for item in items:
                item_lower = item.lower()
                if any(word in item_lower for word in feature_words if len(word) > 3):
                    return True
        
        return False
    
    def _generate_validation_recommendations(
        self,
        verified: List[str],
        missing: List[str],
        unclear: List[str],
        score: float
    ) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        if score >= 80:
            recommendations.append(
                "Excellent: Most features were successfully validated."
            )
        elif score >= 50:
            recommendations.append(
                "Good: Some features need review. Check missing features."
            )
        else:
            recommendations.append(
                "Warning: Many features are missing. Manual review required."
            )
        
        if missing:
            recommendations.append(
                f"Missing {len(missing)} features: {', '.join(missing[:5])}"
            )
        
        if unclear:
            recommendations.append(
                f"Review {len(unclear)} unclear features for accuracy."
            )
        
        # Add specific recommendations - use substring matching for robustness
        if any("dimension" in feature.lower() for feature in missing):
            recommendations.append(
                "Custom dimensions are not supported in Bedrock. Consider using structures or custom worlds."
            )

        if any("enchant" in feature.lower() for feature in missing):
            recommendations.append(
                "Enchanting systems may need to be converted to alternative mechanics in Bedrock."
            )

        if any("custom block" in feature.lower() for feature in missing):
            recommendations.append(
                "Check that all custom blocks have proper behavior definitions."
            )

        return recommendations
    
    def export_research_report(
        self,
        research_data: Dict,
        output_path: str
    ):
        """Export research data to a file."""
        with open(output_path, 'w') as f:
            json.dump(research_data, f, indent=2)
        
        print(f"Research report exported to: {output_path}")
    
    def export_validation_report(
        self,
        report: ValidationReport,
        output_path: str
    ):
        """Export validation report to a file."""
        report_dict = {
            "overall_score": report.overall_score,
            "verified_features": report.verified_features,
            "missing_features": report.missing_features,
            "unclear_features": report.unclear_features,
            "recommendations": report.recommendations,
            "checklist": [
                {
                    "feature": item.feature_name,
                    "category": item.category,
                    "priority": item.priority,
                    "status": item.validation_status,
                    "evidence": item.evidence
                }
                for item in report.feature_checklist
            ],
            "sources": [
                {
                    "url": s.url,
                    "type": s.source_type.value,
                    "title": s.title
                }
                for s in report.research_sources
            ]
        }
        
        with open(output_path, 'w') as f:
            json.dump(report_dict, f, indent=2)
        
        print(f"Validation report exported to: {output_path}")


if __name__ == '__main__':
    # Demo usage
    print("Initializing Online Research Agent...")
    
    agent = OnlineResearchAgent()
    
    # Demo URLs (these would be real URLs in production)
    demo_urls = [
        "https://curseforge.com/minecraft/mc-mods/example-mod",
        "https://modrinth.com/mod/example-mod",
        "https://youtube.com/watch?v=dQw4w9WgXcQ"
    ]
    
    print("\n" + "="*60)
    print("Demo: Research URLs")
    print("="*60)
    
    # Note: Would fail without real APIs, but shows the API
    # research_data = agent.research_mod(demo_urls, "conv_001")
    
    # Demo: Generate mock checklist
    mock_research = {
        "description": "A mod that adds custom blocks, items, and crafting recipes",
        "categories": ["Mechanics", "Tools"],
        "features": ["custom block", "custom item", "crafting"]
    }
    
    checklist = agent.generate_checklist(mock_research, SourceType.CURSEFORGE)
    
    print(f"\nGenerated {len(checklist)} checklist items:")
    for item in checklist:
        print(f"  - [{item.priority}] {item.feature_name} ({item.category})")
    
    print("\nDemo complete!")
