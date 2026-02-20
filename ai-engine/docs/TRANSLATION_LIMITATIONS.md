# Translation Limitations and Known Issues

This document outlines the known limitations of Java to Bedrock JavaScript translation,
providing transparency to users and developers about what can and cannot be
automatically converted.

## Table of Contents

1. [Overview](#overview)
2. [Critical Limitations](#critical-limitations)
3. [High-Impact Limitations](#high-impact-limitations)
4. [Medium-Impact Limitations](#medium-impact-limitations)
5. [Low-Impact Limitations](#low-impact-limitations)
6. [Workarounds and Best Practices](#workarounds-and-best-practices)
7. [When to Use Manual Review](#when-to-use-manual-review)

---

## Overview

The conversion from Java Edition mods to Bedrock Edition add-ons faces fundamental challenges:

1. **Paradigm Shift**: Java uses OOP with inheritance; Bedrock uses event-driven scripting
2. **API Gaps**: Many Java APIs have no direct Bedrock equivalent
3. **Platform Constraints**: Bedrock is more restrictive by design
4. **Performance Differences**: Event-driven vs object-oriented models

This document helps set realistic expectations about conversion quality and identifies
features that require manual intervention.

---

## Critical Limitations

Features that **cannot be translated** and will be **excluded** from conversion:

### Custom Dimensions

**Status**: Unsupported
**Impact**: Complete feature loss

Java Edition allows creating entirely new dimensions with custom world generation.
Bedrock Edition has no API for dimension creation.

**Example**:
```java
public class CustomDimension extends DimensionType {
    // Custom world generation
}
```

**Bedrock Consequence**:
- Dimension will not be created
- Smart Assumption: Convert to large pre-built structure in Overworld
- User Action: Review structure placement manually

### Client-Side Rendering / Shaders

**Status**: Unsupported
**Impact**: Complete feature loss

Java Edition allows client-side rendering, custom shaders, and visual effects.
Bedrock Edition's Render Dragon engine has no public API.

**Example**:
```java
@SubscribeEvent
public void onRenderGameOverlay(RenderGameOverlayEvent event) {
    // Custom overlay rendering
}
```

**Bedrock Consequence**:
- Visual effects will not be included
- Smart Assumption: Exclude rendering-related code
- User Action: Use resource packs for visual changes

### Custom GUI Screens

**Status**: Unsupported
**Impact**: Complete feature loss with workaround

Java Edition allows custom GUI screens with buttons, slots, and rendering.
Bedrock Edition has no custom UI API.

**Example**:
```java
public class CustomScreen extends Screen {
    public void render(PoseStack poseStack) {
        // Custom UI rendering
    }
}
```

**Bedrock Consequence**:
- Custom GUI will not work
- Smart Assumption: Convert to book/sign displays
- User Action: Manually create book-based interfaces

### Complex Block Entities / Machinery

**Status**: Unsupported
**Impact**: Significant functionality loss

Java Edition allows complex block entities with logic, power systems, and multi-block structures.
Bedrock Edition has limited block entity capabilities.

**Example**:
```java
public class AdvancedMachine extends BlockEntity {
    private int processingTime;
    private ItemStack inputSlot;

    @Override
    public void tick() {
        // Complex machinery logic
    }
}
```

**Bedrock Consequence**:
- Complex logic will be simplified or removed
- Smart Assumption: Convert to decorative blocks
- User Action: Accept decorative-only conversion

---

## High-Impact Limitations

Features that are **partially supported** with significant functionality reduction:

### Network Packet Handling

**Status**: Partial
**Impact**: High

Java Edition allows custom network packets for player-server communication.
Bedrock Edition has no packet API.

**Example**:
```java
public class PacketHandler {
    @SubscribeEvent
    public void onCustomPacket(CustomPacketEvent event) {
        // Packet handling
    }
}
```

**Bedrock Consequence**:
- Custom communication not possible
- Smart Assumption: Use events and dynamic properties
- User Action: Use alternative communication methods

### Threading / Async Operations

**Status**: Unsupported
**Impact**: High

Java Edition supports multi-threading and async operations.
Bedrock Edition scripts run synchronously on main thread.

**Example**:
```java
public class AsyncProcessor {
    private ExecutorService executor;

    public void processAsync(Runnable task) {
        executor.submit(task);
    }
}
```

**Bedrock Consequence**:
- Async code will run synchronously
- Smart Assumption: Use event-driven async patterns
- User Action: Restructure code to be event-driven

### Java Reflection

**Status**: Unsupported
**Impact**: High

Java Edition allows accessing private members via reflection.
Bedrock Edition JavaScript has no reflection capabilities.

**Example**:
```java
Field field = obj.getClass().getDeclaredField("privateField");
field.setAccessible(true);
Object value = field.get(obj);
```

**Bedrock Consequence**:
- Private member access not possible
- Smart Assumption: Use public APIs only
- User Action: Restrict to public API usage

### Custom Entity AI / Goals

**Status**: Partial
**Impact**: High

Java Edition allows custom entity AI and pathfinding goals.
Bedrock Edition has limited AI modification.

**Example**:
```java
public class CustomGoal extends Goal {
    public boolean canUse() {
        // Custom AI logic
    }
}
```

**Bedrock Consequence**:
- Custom AI behaviors may not work
- Smart Assumption: Use built-in AI behaviors
- User Action: Accept standard entity behaviors

---

## Medium-Impact Limitations

Features that are **partially supported** with moderate functionality reduction:

### State Management / Instance Variables

**Status**: Partial
**Impact**: Medium

Java Edition uses object-oriented state with instance variables.
Bedrock Edition is more stateless with different patterns.

**Example**:
```java
public class StatefulBlock extends Block {
    private int counter = 0;

    public void onTick() {
        counter++;
    }
}
```

**Bedrock Consequence**:
- Object state requires different approach
- Smart Assumption: Use dynamic properties or global state
- User Action: Implement state management manually

### Class Inheritance

**Status**: Unsupported
**Impact**: Medium

Java Edition supports class inheritance hierarchies.
Bedrock Edition JavaScript does not support inheritance.

**Example**:
```java
public class MetalBlock extends BaseBlock {
    public MetalBlock() {
        super(Properties.of(Material.METAL));
    }
}
```

**Bedrock Consequence**:
- Inheritance hierarchy must be flattened
- Smart Assumption: Use composition over inheritance
- User Action: Manually combine functionality

### Interface Implementation

**Status**: Unsupported
**Impact**: Medium

Java Edition uses interfaces for type contracts.
Bedrock Edition uses duck typing (structural typing).

**Example**:
```java
public class MyBlock implements ICustomBlock {
    public void customMethod() {
        // Implementation
    }
}
```

**Bedrock Consequence**:
- Interface constraints not enforced
- Smart Assumption: Use duck typing patterns
- User Action: Document expected structure

### NBT Data Manipulation

**Status**: Partial
**Impact**: Medium

Java Edition allows direct NBT tag manipulation.
Bedrock Edition uses component system instead.

**Example**:
```java
NBTTagCompound tag = item.getTag();
tag.putString("CustomKey", "value");
```

**Bedrock Consequence**:
- NBT operations must be converted to component operations
- Smart Assumption: Map to component system
- User Action: Learn Bedrock component API

---

## Low-Impact Limitations

Features with **minor functionality changes** or **direct equivalents**:

### Biome Manipulation

**Status**: Partial
**Impact**: Low

Java Edition allows reading and setting biomes.
Bedrock Edition allows reading but not setting biomes.

**Example**:
```java
Biome biome = world.getBiome(pos);
world.setBiome(pos, Biomes.PLAINS);
```

**Bedrock Consequence**:
- Biome reading works, setting does not
- Smart Assumption: Use static structures
- User Action: Pre-place in desired biomes

### Type System Changes

**Status**: Supported
**Impact**: Low

Java Edition has static typing with generics.
Bedrock Edition uses dynamic typing.

**Example**:
```java
List<String> names = new ArrayList<>();
Map<String, Integer> scores = new HashMap<>();
```

**Bedrock Consequence**:
- Generics ignored at runtime
- Type safety reduced
- Smart Assumption: Use comments to document types
- User Action: Test more thoroughly

### Method Overriding

**Status**: Partial
**Impact**: Low

Java Edition supports method overriding and polymorphism.
Bedrock Edition requires explicit function assignment.

**Example**:
```java
@Override
public void onBreak(BlockBreakEvent event) {
    // Override behavior
}
```

**Bedrock Consequence**:
- Polymorphism patterns don't apply
- Smart Assumption: Use event handlers explicitly
- User Action: Explicitly implement behaviors

---

## Workarounds and Best Practices

### State Management

**Problem**: Object state management in event-driven scripts

**Solution**:
```javascript
// Use dynamic properties for persistent state
world.setDynamicProperty("mod:my_state", {counter: 0});

// Later retrieve
const state = world.getDynamicProperty("mod:my_state");
```

### Async Operations

**Problem**: No threading support

**Solution**:
```javascript
// Use tick events with delays
let tickCounter = 0;

world.beforeEvents.tick.subscribe((event) => {
    tickCounter++;

    if (tickCounter > 20) {  // 1 second delay
        // Do delayed action
        tickCounter = 0;
    }
});
```

### Custom UI

**Problem**: No custom GUI API

**Solution**:
```javascript
// Use writable books
const book = new ItemStack("minecraft:writable_book");
// Set book pages
// Display to player
```

### Communication

**Problem**: No network packet API

**Solution**:
```javascript
// Use shared dynamic properties
// Use commands
// Use scoreboard system
```

---

## When to Use Manual Review

### Always Review When:

1. **Critical Features Detected**
   - Custom dimensions
   - Client-side rendering
   - Custom GUI screens
   - Complex machinery

2. **High Issue Count**
   - More than 2 high-impact warnings
   - More than 5 medium-impact warnings
   - Any critical warnings

3. **Low Validation Score**
   - Score below 0.7 indicates significant issues
   - Score below 0.5 requires major fixes

4. **Unknown Patterns**
   - Code contains complex or unusual patterns
   - Validation reports unexpected constructs

### Manual Review Checklist:

- [ ] Review all critical warnings
- [ ] Test converted add-on in Bedrock
- [ ] Verify core functionality works
- [ ] Check for missing features
- [ ] Assess performance impact
- [ ] Compare with original mod behavior
- [ ] Document any manual changes made

---

## Summary Table

| Category | Count | Severity |
|----------|--------|----------|
| Critical Limitations | 4 | Feature Exclusion |
| High-Impact Limitations | 4 | Major Redesign |
| Medium-Impact Limitations | 4 | Partial Support |
| Low-Impact Limitations | 3 | Minor Changes |

**Total Documented Limitations**: 15

---

## Version Information

- Document Version: 1.0
- Last Updated: 2026-02-19
- Applies To: Java 1.20.x - 1.21.x, Bedrock 1.20.10+

---

## Feedback and Updates

This document is living and will be updated as:
- New translation techniques are developed
- Bedrock API capabilities expand
- User feedback identifies additional limitations
- Testing reveals new patterns

To suggest updates or report issues, please create an issue on GitHub.
