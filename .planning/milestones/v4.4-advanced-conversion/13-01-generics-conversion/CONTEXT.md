# Phase 13-01: Generics Conversion

## Phase Overview

**Goal**: Implement support for converting Java generics to JavaScript/JSON for Bedrock add-ons

**Target Features**:
- Type parameter extraction and mapping
- Generic class conversion
- Generic method conversion
- Type bound handling (extends, super)
- Wildcard type support

## Current State

The converter currently handles basic Java types but lacks support for:
- Generic type declarations (`class Foo<T>`)
- Generic method signatures (`<T> void method(T arg)`)
- Bounded types (`<T extends Entity>`, `<T super Player>`)
- Wildcards (`<?>`, `<? extends X>`, `<? super Y>`)

## Success Criteria

1. Extract type parameters from Java class/method declarations
2. Map Java generic types to Bedrock-compatible representations
3. Handle type bounds correctly in conversions
4. Support wildcard types
5. At least 10 passing tests for generics handling

## Implementation Approach

1. Extend JavaAnalyzer to detect generic declarations
2. Create TypeParameterMapper for type mapping
3. Add GenericTypeConverter for conversion logic
4. Integrate with existing conversion pipeline
