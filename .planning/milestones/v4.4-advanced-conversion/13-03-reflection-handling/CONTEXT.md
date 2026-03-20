# Phase 13-03: Reflection API Handling

## Phase Overview

**Goal**: Implement support for detecting and converting Java Reflection API calls to JavaScript equivalents for Bedrock add-ons

**Target Features**:
- Reflection API detection (Class, Field, Method, Constructor)
- Dynamic class loading conversion
- Field/method introspection handling
- Dynamic invocation handling
- Incompatibility warnings for unsupported patterns

## Relationship to Previous Phases

This phase builds upon:
- **Phase 13-01 (Generics)**: Type parameter extraction provides foundation for analyzing generic types in reflection
- **Phase 13-02 (Lambda)**: Lambda detection handles functional interfaces used in reflection patterns

## Current State

The converter handles:
- Basic Java types and structures
- Generics (Phase 13-01)
- Lambda expressions (Phase 13-02)

Missing support for:
- `Class.forName()` dynamic loading
- `getDeclaredFields()`, `getMethods()`, `getConstructors()` introspection
- `Field.set()`, `Field.get()` dynamic field access
- `Method.invoke()` dynamic method calls
- `Constructor.newInstance()` dynamic instantiation

## Common Java Reflection Patterns in Mods

1. **Dynamic Registration**: `Class.forName("com.mod.Item")` → register at compile time
2. **Field Inspection**: `clazz.getDeclaredFields()` → static analysis
3. **Method Invocation**: `method.invoke(target, args)` → direct call conversion
4. **Annotation Reading**: `field.getAnnotations()` → metadata conversion

## Success Criteria

1. Detect reflection API calls in Java source code
2. Analyze reflection targets (fields, methods, constructors)
3. Convert safe patterns to JavaScript equivalents
4. Flag incompatible patterns with warnings
5. At least 15 passing tests for reflection handling
6. Integration with existing conversion pipeline

## Implementation Approach

1. Create ReflectionDetector to find reflection patterns in AST
2. Create ReflectionAnalyzer to determine what is being reflected
3. Create ReflectionMapper to convert or warn about patterns
4. Add detection hooks in JavaAnalyzer agent
5. Integrate warnings into conversion report

## Technical Considerations

- Many reflection uses can be converted to direct calls
- Dynamic class loading often indicates mod loader integration
- Field/method accessibility may not apply in Bedrock
- Some patterns have no direct JavaScript equivalent

## Dependencies

- javalang (AST parsing)
- Phase 13-01 utilities (type analysis)
- JavaAnalyzer agent
- ConversionReport system
