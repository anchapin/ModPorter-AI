# Limitations Guide

This document provides an explicit list of content types and features that do not convert or have limited support in Portkit. Understanding these limitations helps set accurate expectations before conversion and reduces post-conversion frustration.

---

## Conversion Limitations Table

| Content Type | Support Level | What Fails | Workaround |
|--------------|---------------|------------|------------|
| Enchantments (Custom) | Partial | Custom enchantment IDs, non-standard effects | Use vanilla enchantment IDs; implement custom effects via behavior pack scripts |
| Custom GUIs | None | Java AWT/Swing, JavaFX, custom UI frameworks | Recreate with Bedrock Forms API or custom UI forms |
| Network Code | None | Packet handlers, custom protocols, client-server sync | Rewrite with Bedrock networking API; use available events |
| Custom Rendering | None | OpenGL calls, shader modifications, display lists | Rewrite render controllers; adjust model formats; recreate shader effects |
| Third-Party Libraries | None | Forge API, Fabric API, mod loader dependencies | Identify library usage; find Bedrock equivalents; manually implement |
| Reflection-Based Code | None | Field/method reflection, runtime class inspection | Remove reflection; use direct references; static implementations only |
| NMS (Netty/Minecraft Server) | None | CraftBukkit/NMS specific code, server internals | Remove NMS dependencies; use Mojang-defined APIs only |
| Custom Packet Types | None | Protocol extensions, custom serialization | Use Bedrock's built-in packet system |
| Java-Only Features | None | Java-specific APIs (java.nio, java.util.concurrent, etc.) | Replace with Bedrock Script API equivalents |

---

## Partially Supported Features

The following features convert with limitations and require manual work:

### Enchantments

**What Converts:**
- Standard vanilla enchantments (Sharpness, Protection, etc.)
- Basic enchantment properties

**What Fails:**
- Custom enchantment IDs (integer-based)
- Enchantment effects that require Java hook infrastructure
- Enchantments with custom logic handlers

**Detection Method:**
```javascript
// Check for custom enchant registration
if (class.extends("net.minecraft.core.IRegistry") ||
    method.calls("registerEnchantment")) {
  // Has custom enchantment
}
```

**Workaround:**
Replace custom enchant IDs with equivalent vanilla IDs. Implement custom effects using Bedrock's `minecraft:behavior` components and entity event system.

### Custom AI Behaviors

**What Converts:**
- Basic goal-based AI
- Simple target selection
- Basic movement

**What Fails:**
- Complex behavior trees
- Custom goal classes
- State machine implementations with many states
- Behavior priorities requiring fine-tuning

**Detection Method:**
```javascript
// Look for custom AI classes
if (class.extends("EntityAI") ||
    class.hasField("goalSelector") ||
    class.hasField("targetSelector")) {
  // Has custom AI
}
```

**Workaround:**
Manually recreate AI using Bedrock's `minecraft:behavior` components. Break complex behaviors into simpler goals and sequences.

### Custom Dimensions

**What Converts:**
- Basic dimension JSON structure
- Portal block definitions
- World generation presets

**What Fails:**
- Custom dimension providers
- Complex biome blending
- Special world generation algorithms
- Dimension-specific entity spawning

**Detection Method:**
```javascript
// Check for dimension-related code
if (class.extends("Dimension") ||
    class.extends("WorldProvider") ||
    method.calls("registerDimension")) {
  // Has custom dimension
}
```

**Workaround:**
Use Bedrock's standard dimension system. Manually configure portal blocks and use vanilla world generation with custom biome weights.

### Biome Mapping

**What Converts:**
- Basic biome IDs
- Simple climate settings
- Standard biome structure

**What Fails:**
- Custom biome decorators
- Complex terrain generation
- Custom vegetation placement
- Biome-specific entity spawning rules

**Detection Method:**
```javascript
// Look for biome registration
if (class.extends("Biome") ||
    method.calls("registerBiome") ||
    method.calls("setBiome")) {
  // Has custom biome
}
```

**Workaround:**
Use Bedrock's `biomes.json` for basic biome definitions. Manually adjust terrain using editor tools post-conversion.

### Scoreboard & Objectives

**What Converts:**
- Basic score objectives
- Simple team definitions
- Standard score operations

**What Fails:**
- Complex objective criteria
- Custom scoreboard displays
- Dynamic team management
- Score-based triggers requiring Java events

**Detection Method:**
```javascript
// Check for scoreboard usage
if (class.calls("Scoreboard") ||
    method.calls("setScore") ||
    class.extends("Objective")) {
  // Has custom scoreboard
}
```

**Workaround:**
Implement scoreboard using Bedrock commands (`/scoreboard objectives add`). Use command blocks for score-based triggers.

---

## Features That Require Complete Rewrite

### Custom GUI Systems

Java mods often use AWT, Swing, or JavaFX for custom interfaces. Bedrock does not support these.

**Detection Method:**
```javascript
// Look for GUI imports
if (imports.contains("java.awt") ||
    imports.contains("javax.swing") ||
    imports.contains("javafx")) {
  // Has Java GUI
}
```

**Workaround:**
Recreate interfaces using:
- Bedrock Forms API (JSON-based UI)
- Custom command-based interfaces
- HTML/Markdown documentation for complex menus

### Network & Packet Handling

Java mods use custom packet handlers for client-server communication. Bedrock's networking is different.

**Detection Method:**
```javascript
// Check for packet handling
if (class.extends("Packet") ||
    method.calls("sendPacket") ||
    method.calls("handlePacket")) {
  // Has custom networking
}
```

**Workaround:**
- Use Bedrock's built-in `player.onChat` events
- Implement synchronization via `execute` commands
- Use `setBlock`/`getBlock` for data sync when needed

### Mod Loader Integration

Forge/Fabric API calls do not exist in Bedrock.

**Detection Method:**
```javascript
// Look for mod loader APIs
if (imports.contains("net.minecraftforge") ||
    imports.contains("fabric") ||
    class.hasAnnotation("Mod")) {
  // Has mod loader dependency
}
```

**Workaround:**
1. Identify all mod loader API calls
2. Find Bedrock equivalent functionality
3. Remove mod-specific dependencies
4. Implement missing features manually

---

## Impact Descriptions

| Category | Impact Level | Description |
|----------|--------------|-------------|
| Enchantments | Medium | Custom enchantments need reimplementation; basic ones work |
| Custom GUIs | High | Requires complete UI redesign; no automatic path |
| Network Code | High | Synchronization logic must be rebuilt |
| Custom Rendering | High | Visual effects need manual recreation |
| Third-Party Libs | Medium | Common libraries may have no Bedrock equivalent |
| Reflection Code | Critical | Must be eliminated entirely; no conversion path |
| NMS Code | Critical | Server internals have no Bedrock equivalent |

---

## Community Workarounds

The following workarounds are collected from community experience:

### Enchantment Workaround
```javascript
// Instead of custom enchant ID
"minecraft:sharpness": {
  "level": 3
}

// Use behavior pack enchant via command
/event entity @[minecraft:sharpness] ...
```

### GUI Workaround
```javascript
// Create forms JSON
{
  "form_id": "custom_gui",
  "buttons": [...],
  "title": "My Custom GUI"
}
```

### Network Sync Workaround
```javascript
// Use entity data for sync instead of packets
"minecraft:inventory": {
  // ...
}
// Update via tick event
```

---

## Verification Steps

Before converting, run these checks:

1. **Enchantment Check**
   ```bash
   grep -r "registerEnchantment\|customEnchant" ./src
   ```

2. **GUI Check**
   ```bash
   grep -r "java.awt\|javax.swing\|javafx" ./src
   ```

3. **Network Check**
   ```bash
   grep -r "sendPacket\|handlePacket\|Packet" ./src
   ```

4. **Reflection Check**
   ```bash
   grep -r "Method\|Field\|getDeclaredMethod\|getField" ./src
   ```

---

## Getting Help

- **Discord**: [discord.gg/modporter](https://discord.gg/modporter) - #limitations channel
- **GitHub Issues**: [github.com/portkit/issues](https://github.com/portkit/issues)
- **Community Wiki**: [wiki.portkit.cloud](https://wiki.portkit.cloud)

---

## Related Documentation

- [Conversion Guide](conversion-guide.md) - Full conversion process
- [Troubleshooting](guides/TROUBLESHOOTING.md) - Common issues and solutions
- [FAQ](faq.md) - Frequently asked questions

---

*Last updated: 2024-11 | Version 1.0*