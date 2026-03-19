# Context: Phase 12-01 - Semantic Equivalence Scoring

## Phase Overview
**Phase**: 12-01  
**Name**: Semantic Equivalence Scoring  
**Milestone**: v4.3 Conversion Quality  
**Goal**: Measure and track semantic similarity between Java source and Bedrock output

## Requirements
**REQ-4.1**: Semantic Equivalence Scoring
- Code embedding generation (Java & JavaScript)
- Data flow graph comparison
- Similarity scoring algorithm (0-100%)
- Semantic drift identification
- Score thresholds: Excellent (90%+), Good (70-89%), Needs Work (<70%)

## Technical Context

### Existing Implementation
The `ai-engine/services/semantic_equivalence.py` already contains:
- **DataFlowAnalyzer**: Builds data flow graphs from Java source
- **ControlFlowAnalyzer**: Builds control flow graphs
- **SemanticEquivalenceChecker**: Compares DFG and CFG between Java and Bedrock
- **EquivalenceResult**: Structured output with similarity scores
- **654 lines** of implementation

### What's Implemented
- Node types: ENTRY, EXIT, ASSIGNMENT, CONDITION, LOOP, METHOD_CALL, FIELD_ACCESS, RETURN, BRANCH, MERGE
- DFG/CFG construction
- Graph-based comparison
- Similarity scoring

### What's Missing (Gaps)
1. **Code embedding generation** - No implementation for embedding-based comparison
2. **JavaScript/Bedrock parsing** - Limited JS parsing capability
3. **Integration with conversion pipeline** - Not called during normal conversions
4. **Similarity thresholds** - No threshold application (90%+/70-89%/<70%)
5. **Drift identification** - Diffs exist but drift categorization incomplete
6. **Report integration** - Not included in conversion reports

## Dependencies
- REQ-1.6 (RAG infrastructure - already exists)
- JavaAnalyzerAgent (existing)
- LogicTranslatorAgent (existing)
- QAValidatorAgent (existing)

## Constraints
- Must work with existing semantic_equivalence.py module
- Should integrate with RAG system for pattern matching
- Needs to handle both Java and JavaScript code comparison

## Locked Decisions
- Using graph-based comparison (DFG + CFG) - from existing implementation
- Using javalang for Java AST parsing - from existing codebase
- Score range 0-100% - from roadmap

## Claude's Discretion Areas
1. Embedding model choice (sentence-transformers, OpenAI, or local)
2. Exact threshold values for categorizing scores
3. How to present drift identification in reports
4. Integration point in conversion pipeline

## Previous Work
- Phase 09: QA Suite implemented validators and regression detection
- Phase 10: Timeout & Robustness implemented input/output validation
- Phase 11: Error Recovery implemented retry and fallback strategies
