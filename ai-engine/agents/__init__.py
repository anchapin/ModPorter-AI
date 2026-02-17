# ai-engine/agents/__init__.py

# Import RAG components first (no crewai dependency)
try:
    from .rag_agents import RAGAgents
    __all__ = ["RAGAgents"]
except ImportError as e:
    RAGAgents = None
    __all__ = []

# Import knowledge base (no crewai dependency)
try:
    from .knowledge_base_agent import KnowledgeBaseAgent
    __all__.append("KnowledgeBaseAgent")
except ImportError:
    KnowledgeBaseAgent = None

# Try to import crewai-dependent agents
try:
    from .asset_converter import AssetConverterAgent as AssetConverter
    __all__.append("AssetConverter")
except ImportError as e:
    AssetConverter = None
    print(f"Warning: Could not import AssetConverterAgent: {e}")

try:
    from .bedrock_architect import BedrockArchitectAgent as BedrockArchitect
    __all__.append("BedrockArchitect")
except ImportError:
    BedrockArchitect = None

try:
    from .java_analyzer import JavaAnalyzerAgent as JavaAnalyzer
    __all__.append("JavaAnalyzer")
except ImportError:
    JavaAnalyzer = None

try:
    from .logic_translator import LogicTranslatorAgent as LogicTranslator
    __all__.append("LogicTranslator")
except ImportError:
    LogicTranslator = None

try:
    from .packaging_agent import PackagingAgent
    __all__.append("PackagingAgent")
except ImportError:
    PackagingAgent = None

try:
    from .qa_validator import QAValidatorAgent as QAValidator
    __all__.append("QAValidator")
except ImportError:
    QAValidator = None

try:
    from .validation_agent import (
        ValidationAgent, 
        LLMSemanticAnalyzer, 
        BehaviorAnalysisEngine, 
        AssetIntegrityChecker, 
        ManifestValidator
    )
    __all__.extend([
        "ValidationAgent",
        "LLMSemanticAnalyzer",
        "BehaviorAnalysisEngine",
        "AssetIntegrityChecker",
        "ManifestValidator"
    ])
except ImportError:
    ValidationAgent = None
    LLMSemanticAnalyzer = None
    BehaviorAnalysisEngine = None
    AssetIntegrityChecker = None
    ManifestValidator = None
