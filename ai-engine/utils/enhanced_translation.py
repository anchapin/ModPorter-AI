"""
Enhanced Translation Engine - Integrates semantic context, data flow analysis, and pattern matching.

This module provides an enhanced translation pipeline that uses:
- SemanticContextEngine for context-aware translation
- DataFlowAnalyzer for data flow tracking
- PatternMatcher for Minecraft mod pattern recognition
"""

from typing import Dict, List, Any, Optional
from utils.semantic_context import SemanticContextEngine, create_semantic_context_engine
from utils.data_flow import DataFlowAnalyzer, create_data_flow_analyzer
from utils.pattern_matcher import PatternMatcher, create_pattern_matcher


class EnhancedTranslationEngine:
    """
    Enhanced translation engine that combines semantic context, data flow analysis,
    and pattern matching for improved Java to Bedrock translation.
    """
    
    def __init__(self):
        self.semantic_engine: SemanticContextEngine = create_semantic_context_engine()
        self.data_flow_analyzer: DataFlowAnalyzer = create_data_flow_analyzer()
        self.pattern_matcher: PatternMatcher = create_pattern_matcher()
        self.logger = None
        
    def set_logger(self, logger):
        """Set logger for all components."""
        self.logger = logger
        self.semantic_engine.set_logger(logger)
        self.data_flow_analyzer.set_logger(logger)
        self.pattern_matcher.set_logger(logger)
        
    def analyze_and_translate(self, java_source: str, class_name: str = "") -> Dict[str, Any]:
        """
        Analyze Java source and provide enhanced translation.
        
        Args:
            java_source: Java source code to translate
            class_name: Optional class name for context
            
        Returns:
            Dictionary containing:
            - translation: Translated JavaScript code
            - semantic_context: Context information for the LLM
            - data_flow: Data flow analysis results
            - patterns: Pattern matches found
            - confidence: Overall translation confidence
        """
        result = {
            'translation': '',
            'semantic_context': {},
            'data_flow': {},
            'patterns': [],
            'confidence': 0.0,
            'recommendations': []
        }
        
        try:
            # Step 1: Semantic Context Analysis
            semantic_context = self.semantic_engine.parse_with_context(java_source, class_name)
            result['semantic_context'] = semantic_context
            
            # Step 2: Data Flow Analysis
            data_flow = self.data_flow_analyzer.analyze_method(java_source)
            result['data_flow'] = {
                'mutations': [(m.variable_name, m.mutation_type, m.value) 
                             for m in data_flow.variable_mutations],
                'bedrock_operations': self.data_flow_analyzer.map_to_bedrock_operations()
            }
            
            # Step 3: Pattern Matching
            patterns = self.pattern_matcher.find_matches(java_source)
            result['patterns'] = [
                {
                    'id': p.pattern_id,
                    'type': p.pattern_type.value,
                    'confidence': p.confidence,
                    'translation': p.translation
                }
                for p in patterns[:10]  # Top 10 patterns
            ]
            
            # Step 4: Calculate overall confidence
            confidence_scores = [p['confidence'] for p in result['patterns']]
            if confidence_scores:
                result['confidence'] = sum(confidence_scores) / len(confidence_scores)
                
            # Step 5: Generate recommendations
            recommendations = self.pattern_matcher.recommend_patterns(java_source)
            result['recommendations'] = [
                {'pattern_id': p.pattern_id, 'description': p.description, 'score': s}
                for p, s in recommendations[:5]
            ]
            
            # Step 6: Build context prompt for LLM
            result['context_prompt'] = self._build_context_prompt(result)
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error in enhanced translation: {e}")
            result['error'] = str(e)
            
        return result
        
    def _build_context_prompt(self, analysis_result: Dict[str, Any]) -> str:
        """Build a context prompt for the LLM based on analysis results."""
        prompt_parts = []
        
        # Add semantic context
        if analysis_result.get('semantic_context'):
            ctx = analysis_result['semantic_context']
            if ctx.get('classes'):
                prompt_parts.append("### Classes Found")
                for cls in ctx['classes'][:3]:
                    parts = [cls['name']]
                    if cls.get('extends'):
                        parts.append(f"extends {cls['extends']}")
                    prompt_parts.append(" - ".join(parts))
                    
        # Add pattern matches
        if analysis_result.get('patterns'):
            prompt_parts.append("\n### Pattern Matches")
            for pattern in analysis_result['patterns'][:5]:
                prompt_parts.append(
                    f"- {pattern['id']}: {pattern['type']} "
                    f"(confidence: {pattern['confidence']:.2f})"
                )
                
        # Add data flow summary
        if analysis_result.get('data_flow'):
            df = analysis_result['data_flow']
            if df.get('mutations'):
                prompt_parts.append("\n### Variable Mutations")
                for var, mut_type, value in df['mutations'][:5]:
                    prompt_parts.append(f"- {var}: {mut_type} = {value}")
                    
        # Add recommendations
        if analysis_result.get('recommendations'):
            prompt_parts.append("\n### Recommendations")
            for rec in analysis_result['recommendations'][:3]:
                prompt_parts.append(f"- {rec['description']} (score: {rec['score']:.2f})")
                
        return "\n".join(prompt_parts)
        
    def translate_with_context(self, java_source: str, llm_translation: str, 
                               class_name: str = "") -> str:
        """
        Enhance an LLM translation with semantic context.
        
        Args:
            java_source: Original Java source code
            llm_translation: LLM-generated translation
            class_name: Optional class name
            
        Returns:
            Enhanced translation with semantic improvements
        """
        analysis = self.analyze_and_translate(java_source, class_name)
        
        # Apply pattern-based fixes
        enhanced = llm_translation
        
        # Apply data flow based corrections
        for var, mut_type, value in analysis.get('data_flow', {}).get('mutations', []):
            if mut_type == 'declaration' and value:
                # Ensure proper initialization
                if f"let {var};" in enhanced or f"var {var};" in enhanced:
                    # Fix uninitialized declarations
                    enhanced = enhanced.replace(
                        f"let {var};",
                        f"let {var} = {value};"
                    )
                    
        return enhanced


# Singleton instance
_enhanced_engine: Optional[EnhancedTranslationEngine] = None


def get_enhanced_translation_engine() -> EnhancedTranslationEngine:
    """Get singleton instance of the enhanced translation engine."""
    global _enhanced_engine
    if _enhanced_engine is None:
        _enhanced_engine = EnhancedTranslationEngine()
    return _enhanced_engine
