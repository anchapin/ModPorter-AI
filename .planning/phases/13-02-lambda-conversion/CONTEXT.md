# Phase 13-02 Context: Lambda Expression Support

**Phase**: 13-02  
**Milestone**: v4.4 - Advanced Conversion  
**Previous Phase**: 13-01 (Generics Conversion) ✅ Complete

---

## Overview

This phase implements Java lambda expression support for the ModPorter-AI conversion system. Lambda expressions are a core Java 8+ feature that require special handling during conversion to Bedrock JavaScript.

---

## Background

### What are Lambda Expressions?

Java lambda expressions are anonymous functions that can be passed around as values. They have the syntax:

```java
// Expression lambdas
(x, y) -> x + y
s -> s.length()

// Block lambdas
x -> { return x * 2; }

// Method references
String::length
ArrayList::new
```

### Why This Matters for Conversion

- Lambda expressions are extremely common in modern Java mods
- They require conversion to JavaScript functions
- Need to handle closures (captured variables)
- Method references need special handling
- Type inference is needed for functional interfaces

---

## Relationship to Other Components

### Phase 13-01 (Generics) - Completed
- TypeParameterExtractor provides type information used by lambda type inference
- GenericTypeMapper handles generic types within lambda bodies

### Phase 13-03 (Reflection) - Future
- Lambda expressions may contain reflective calls
- Need to coordinate handling of Method references

---

## Technical Implementation Notes

### AST Handling
- Lambda expressions appear as `LambdaExpression` nodes in javalang AST
- Parameters can be typed or untyped
- Body can be expression or block

### JavaScript Conversion Target
```java
// Java
list.stream().filter(x -> x > 5).map(x -> x * 2)

// Bedrock JavaScript
list.stream().filter(x => x > 5).map(x => x * 2)
```

### Method References
```java
// Java
String::length
System.out::println
ArrayList::new

// Bedrock JavaScript
s => s.length()
x => console.log(x)
() => new ArrayList()
```

### Closures
```java
// Java
int factor = 2;
list.stream().map(x -> x * factor)

// Bedrock JavaScript
const factor = 2;
list.stream().map(x => x * factor)
```

---

## Scope

### In Scope
1. Expression lambdas (e.g., `x -> x + 1`)
2. Block lambdas (e.g., `x -> { return x + 1; }`)
3. Method references (instance, static, constructor)
4. Captured variables/closures
5. Type inference for common functional interfaces
6. Lambda in stream operations

### Out of Scope
1. Complex generic lambdas (defer to future enhancement)
2. Lambda serialization
3. Thread-local captured variables

---

## Success Criteria

- Detect and analyze lambda expressions from Java AST
- Convert lambdas to JavaScript functions with correct syntax
- Handle method references appropriately
- Support captured variables via closures
- Infer types for common functional interfaces
- 15+ passing tests

---

## Estimated Complexity

- **Medium-High** complexity due to:
  - Multiple lambda forms to handle
  - Closure scope management
  - Method reference variety
  - Type inference logic
