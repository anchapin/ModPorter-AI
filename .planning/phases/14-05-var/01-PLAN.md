# Phase 14-05: Var Type Inference

**Phase ID**: 14-05  
**Milestone**: v4.5 Java Patterns Complete  
**Pattern**: Var - Local Variable Type Inference (Java 10+)

## Goal
Implement conversion support for Java `var` keyword to inferred TypeScript types.

## Implementation Requirements

### 1. VarDetector
- Detect `var` declarations: `var x = new ArrayList<String>();`
- Handle var with different initializer types
- Handle var in for loops: `for (var item : items)`

### 2. VarTypeInference
- Infer type from initializer expression
- Handle complex initializers: lambdas, method references, constructors
- Convert `var` to explicit TypeScript type

### 3. VarScopeHandler
- Track var declarations within scope
- Handle var shadowing
- Handle var with diamond operator: `var list = new ArrayList<>()`

## Success Criteria
- All var patterns correctly inferred and converted
- Proper TypeScript type output
- Tests cover at least 8 var patterns

## Dependencies
- None

## Implementation Location
`ai-engine/converters/patterns/var_inference.py`
