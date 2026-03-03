# API Mapping Documentation: Java to Bedrock JavaScript

This document provides comprehensive mappings between Java Edition modding APIs and Bedrock Edition scripting APIs. This is a critical reference for the Logic Translation Agent.

## Overview

Converting Java code to Bedrock JavaScript requires understanding the fundamental differences in architecture:
- **Java Edition**: Object-oriented, event-driven with class inheritance
- **Bedrock Edition**: Event-driven scripting, component-based entities, no class inheritance

## Table of Contents

1. [Player API Mappings](#player-api-mappings)
2. [World API Mappings](#world-api-mappings)
3. [Entity API Mappings](#entity-api-mappings)
4. [Item API Mappings](#item-api-mappings)
5. [Block API Mappings](#block-api-mappings)
6. [Event Handler Mappings](#event-handler-mappings)
7. [Type System Mappings](#type-system-mappings)
8. [Unsupported Features](#unsupported-features)
9. [Translation Limitations](#translation-limitations)

---

## Player API Mappings

### Health & Status

| Java API | Bedrock JavaScript Equivalent | Notes | Complexity |
|-----------|----------------------------|--------|------------|
| `player.getHealth()` | `player.getComponent("minecraft:health").currentValue` | Requires accessing component | Low |
| `player.setHealth(value)` | `player.getComponent("minecraft:health").setCurrentValue(value)` | | Low |
| `player.getMaxHealth()` | `player.getComponent("minecraft:health").effectiveMax` | | Low |
| `player.isDead()` | `player.getComponent("minecraft:health").currentValue <= 0` | Boolean expression | Low |
| `player.heal(amount)` | `player.getComponent("minecraft:health").addCurrent(amount)` | | Low |

### Inventory

| Java API | Bedrock JavaScript Equivalent | Notes | Complexity |
|-----------|----------------------------|--------|------------|
| `player.getInventory()` | `player.container` | Container component | Low |
| `player.getItemInHand()` | `player.getComponent('minecraft:equipped_item').item` | Main hand only | Low |
| `player.getSelectedItem()` | `player.getComponent('minecraft:equipped_item')` | Returns component | Low |
| `player.getMainHandItem()` | `player.getComponent('minecraft:equipped_item').item` | | Low |
| `player.getOffhandItem()` | `// Not directly supported` | Bedrock has no offhand | High |
| `player.setItemInHand(item)` | `player.getComponent('minecraft:equipped_item').setItem(item)` | | Low |

### Movement & Position

| Java API | Bedrock JavaScript Equivalent | Notes | Complexity |
|-----------|----------------------------|--------|------------|
| `player.getLocation()` | `player.location` | Vector3 | Low |
| `player.getX()` | `player.location.x` | | Low |
| `player.getY()` | `player.location.y` | | Low |
| `player.getZ()` | `player.location.z` | | Low |
| `player.teleport(location)` | `player.teleport(location)` | | Low |
| `player.setVelocity(vector)` | `player.applyVelocity(vector)` | | Medium |
| `player.getVelocity()` | `player.velocity` | | Medium |
| `player.getDirection()` | `player.direction` | | Low |
| `player.getYaw()` | `player.rotation.y` | | Low |
| `player.getPitch()` | `player.rotation.x` | | Low |

### State & Conditions

| Java API | Bedrock JavaScript Equivalent | Notes | Complexity |
|-----------|----------------------------|--------|------------|
| `player.isSneaking()` | `player.isSneaking` | Property | Low |
| `player.isSprinting()` | `player.isSprinting` | Property | Low |
| `player.isFlying()` | `player.isFlying` | Property | Low |
| `player.isOnGround()` | `player.isOnGround` | Property | Low |
| `player.isSleeping()` | `// Not directly supported` | | High |
| `player.isBurning()` | `player.isOnFire` | Property | Low |
| `player.isInWater()` | `player.isInWater` | Property | Low |
| `player.isInLava()` | `player.isInLava` | Property | Low |

### Experience & Levels

| Java API | Bedrock JavaScript Equivalent | Notes | Complexity |
|-----------|----------------------------|--------|------------|
| `player.getExperienceLevel()` | `player.level` | | Low |
| `player.setExperienceLevel(level)` | `player.addLevels(level - player.level)` | | Medium |
| `player.getExp()` | `// Not directly supported` | No XP value access | High |
| `player.giveExp(amount)` | `player.addExperience(amount)` | | Low |
| `player.getTotalExperience()` | `// Not directly supported` | | High |

### Hunger & Saturation

| Java API | Bedrock JavaScript Equivalent | Notes | Complexity |
|-----------|----------------------------|--------|------------|
| `player.getFoodLevel()` | `player.getComponent("minecraft:food").foodLevel` | | Low |
| `player.setFoodLevel(level)` | `player.getComponent("minecraft:food").foodLevel = level` | | Low |
| `player.getSaturation()` | `player.getComponent("minecraft:food").saturation` | | Low |
| `player.setSaturation(value)` | `player.getComponent("minecraft:food").saturation = value` | | Low |

### Permissions

| Java API | Bedrock JavaScript Equivalent | Notes | Complexity |
|-----------|----------------------------|--------|------------|
| `player.hasPermission(node)` | `player.hasPermission(node)` | | Low |
| `player.isOp()` | `player.isOp()` | | Low |
| `player.setOp(value)` | `// Not directly supported` | Cannot change OP status | High |

---

## World API Mappings

### Block Access

| Java API | Bedrock JavaScript Equivalent | Notes | Complexity |
|-----------|----------------------------|--------|------------|
| `world.getBlockAt(x, y, z)` | `world.getBlock(location)` | Returns block permutation | Low |
| `world.setBlock(x, y, z, block)` | `dimension.setBlockPermutation(location, block)` | Different approach | Medium |
| `world.getBlockState(location)` | `world.getBlock(location).permutation` | | Low |
| `world.setBlockState(location, state)` | `dimension.setBlockPermutation(location, blockPermutation)` | | Medium |
| `world.isAirBlock(location)` | `block.typeId === 'minecraft:air'` | | Low |
| `world.getTypeId(location)` | `block.typeId` | | Low |
| `world.breakBlock(location)` | `dimension.getBlock(location).destroy()` | | Low |

### Time & Weather

| Java API | Bedrock JavaScript Equivalent | Notes | Complexity |
|-----------|----------------------------|--------|------------|
| `world.getTime()` | `world.getTime()` | | Low |
| `world.setTime(time)` | `world.setTime(time)` | | Low |
| `world.getDayTime()` | `world.dayTime` | Property | Low |
| `world.setDayTime(time)` | `world.dayTime = time` | | Low |
| `world.hasStorm()` | `world.isRaining()` | | Low |
| `world.setStorm(raining)` | `world.setRaining(raining)` | | Low |
| `world.isThundering()` | `world.isLightning()` | | Low |
| `world.setThundering(thunder)` | `// Not directly supported` | | Medium |
| `world.getDifficulty()` | `world.difficulty` | Property | Low |
| `world.setDifficulty(difficulty)` | `world.difficulty = difficulty` | | Low |

### Biome & Environment

| Java API | Bedrock JavaScript Equivalent | Notes | Complexity |
|-----------|----------------------------|--------|------------|
| `world.getBiome(location)` | `world.getBiome(location)` | | Low |
| `world.setBiome(location, biome)` | `// Not directly supported` | Cannot change biome | High |
| `world.getTemperature()` | `// Not directly supported` | No biome property access | High |
| `world.getHumidity()` | `// Not directly supported` | | High |

### Entity Spawning

| Java API | Bedrock JavaScript Equivalent | Notes | Complexity |
|-----------|----------------------------|--------|------------|
| `world.spawnEntity(type, location)` | `world.spawnEntity(type, location)` | | Low |
| `world.spawnEntity(type, x, y, z)` | `world.spawnEntity(type, {x, y, z})` | | Low |
| `world.spawnParticle(type, location)` | `world.spawnParticle(type, location)` | | Low |
| `world.createExplosion(location, power)` | `dimension.createExplosion(location, power)` | | Low |

### Dimension Access

| Java API | Bedrock JavaScript Equivalent | Notes | Complexity |
|-----------|----------------------------|--------|------------|
| `player.getWorld()` | `player.dimension` | | Low |
| `world.getDimension()` | `// Not applicable` | | N/A |
| `Bukkit.getWorld(name)` | `world.getDimension(name)` | | Medium |

---

## Entity API Mappings

### Health & Status

| Java API | Bedrock JavaScript Equivalent | Notes | Complexity |
|-----------|----------------------------|--------|------------|
| `entity.getHealth()` | `entity.getComponent("minecraft:health").currentValue` | | Low |
| `entity.setHealth(value)` | `entity.getComponent("minecraft:health").setCurrentValue(value)` | | Low |
| `entity.getMaxHealth()` | `entity.getComponent("minecraft:health").effectiveMax` | | Low |
| `entity.isDead()` | `entity.getComponent("minecraft:health").currentValue <= 0` | | Low |
| `entity.damage(amount, source)` | `entity.applyDamage(amount, source)` | | Low |
| `entity.kill()` | `entity.kill()` | | Low |
| `entity.remove()` | `entity.destroy()` | | Low |

### Movement & Position

| Java API | Bedrock JavaScript Equivalent | Notes | Complexity |
|-----------|----------------------------|--------|------------|
| `entity.getLocation()` | `entity.location` | | Low |
| `entity.getX()` | `entity.location.x` | | Low |
| `entity.getY()` | `entity.location.y` | | Low |
| `entity.getZ()` | `entity.location.z` | | Low |
| `entity.teleport(location)` | `entity.teleport(location)` | | Low |
| `entity.getVelocity()` | `entity.velocity` | | Low |
| `entity.setVelocity(vector)` | `entity.velocity = vector` | | Low |
| `entity.setRotation(yaw, pitch)` | `entity.setRotation(yaw, pitch)` | | Low |
| `entity.getYaw()` | `entity.rotation.y` | | Low |
| `entity.getPitch()` | `entity.rotation.x` | | Low |

### Properties & Identification

| Java API | Bedrock JavaScript Equivalent | Notes | Complexity |
|-----------|----------------------------|--------|------------|
| `entity.getType()` | `entity.typeId` | String identifier | Low |
| `entity.getName()` | `entity.nameTag` | | Low |
| `entity.setCustomName(name)` | `entity.nameTag = name` | | Low |
| `entity.getCustomName()` | `entity.nameTag` | | Low |
| `entity.isSilent()` | `entity.isSilent` | | Low |
| `entity.setSilent(value)` | `entity.isSilent = value` | | Low |
| `entity.hasGravity()` | `entity.hasGravity` | | Low |
| `entity.setGravity(value)` | `entity.hasGravity = value` | | Low |
| `entity.isInvulnerable()` | `// Not directly supported` | | Medium |

### AI & Behavior

| Java API | Bedrock JavaScript Equivalent | Notes | Complexity |
|-----------|----------------------------|--------|------------|
| `entity.getGoalTarget()` | `// Not directly supported` | No AI access | High |
| `entity.setGoalTarget(target)` | `// Not directly supported` | | High |
| `entity.getAttackTarget()` | `// Not directly supported` | | High |
| `entity.setAttackTarget(target)` | `// Not directly supported` | | High |
| `entity.getNavigation()` | `// Not directly supported` | | High |

### Inventory & Equipment

| Java API | Bedrock JavaScript Equivalent | Notes | Complexity |
|-----------|----------------------------|--------|------------|
| `entity.getInventory()` | `entity.container` | | Low |
| `entity.getEquipment()` | `entity.getComponent('minecraft:equipment')` | | Low |
| `entity.getEquipment(slot)` | `entity.getComponent('minecraft:equipment').getEquipment(slot)` | | Medium |
| `entity.setEquipment(slot, item)` | `entity.getComponent('minecraft:equipment').setEquipment(slot, item)` | | Medium |

---

## Item API Mappings

### ItemStack Basic

| Java API | Bedrock JavaScript Equivalent | Notes | Complexity |
|-----------|----------------------------|--------|------------|
| `new ItemStack(type)` | `new ItemStack(type)` | | Low |
| `new ItemStack(type, count)` | `new ItemStack(type, count)` | | Low |
| `ItemStack.EMPTY` | `ItemStack.empty()` | | Low |
| `.getType()` | `.typeId` | | Low |
| `.setType(type)` | `.typeId = type` | | Low |
| `.getAmount()` | `.amount` | | Low |
| `.setAmount(count)` | `.amount = count` | | Low |
| `.isEmpty()` | `.amount === 0` | | Low |

### Item Durability

| Java API | Bedrock JavaScript Equivalent | Notes | Complexity |
|-----------|----------------------------|--------|------------|
| `.getDurability()` | `.getComponent('minecraft:damageable').damage` | | Low |
| `.setDurability(value)` | `.getComponent('minecraft:damageable').damage = value` | | Low |
| `.getMaxDurability()` | `.getComponent('minecraft:damageable').maxDurability` | | Low |
| `.isDamaged()` | `.getComponent('minecraft:damageable').damage > 0` | | Low |

### Item Meta & Enchantments

| Java API | Bedrock JavaScript Equivalent | Notes | Complexity |
|-----------|----------------------------|--------|------------|
| `.getItemMeta()` | `.getComponent('minecraft:item')` | | Low |
| `.setItemMeta(meta)` | `// Not directly supported` | | High |
| `.hasItemMeta()` | `.hasComponent('minecraft:item')` | | Low |
| `.getEnchantments()` | `.getComponent('minecraft:enchantable')` | | Medium |
| `.addEnchantment(ench)` | `.getComponent('minecraft:enchantable').addEnchantment(ench)` | | Medium |
| `.hasEnchantment(ench)` | `// Complex check required` | | High |

### Item Lore & Display

| Java API | Bedrock JavaScript Equivalent | Notes | Complexity |
|-----------|----------------------------|--------|------------|
| `.getDisplayName()` | `.nameTag` | | Low |
| `.setDisplayName(name)` | `.nameTag = name` | | Low |
| `.getLore()` | `.getComponent('minecraft:display_name').value` | | Medium |
| `.setLore(lore)` | `// Not directly supported` | | High |

---

## Block API Mappings

### Block State & Type

| Java API | Bedrock JavaScript Equivalent | Notes | Complexity |
|-----------|----------------------------|--------|------------|
| `block.getType()` | `block.typeId` | | Low |
| `block.getTypeId()` | `block.typeId` | | Low |
| `block.setType(type)` | `block.setType(type)` | | Low |
| `block.getData()` | `block.permutation` | | Low |
| `block.getState()` | `block.permutation` | | Low |
| `block.setState(state)` | `block.setPermutation(state)` | | Low |

### Block Properties

| Java API | Bedrock JavaScript Equivalent | Notes | Complexity |
|-----------|----------------------------|--------|------------|
| `block.isEmpty()` | `block.typeId === 'minecraft:air'` | | Low |
| `block.isSolid()` | `// Not directly supported` | Requires property check | Medium |
| `block.isLiquid()` | `// Check typeId` | | Medium |
| `block.getLightLevel()` | `block.getLight()` | | Low |
| `block.isPowerSource()` | `// Not directly supported` | | Medium |
| `block.isPowerSink()` | `// Not directly supported` | | Medium |

### Block Position

| Java API | Bedrock JavaScript Equivalent | Notes | Complexity |
|-----------|----------------------------|--------|------------|
| `block.getLocation()` | `block.location` | | Low |
| `block.getX()` | `block.location.x` | | Low |
| `block.getY()` | `block.location.y` | | Low |
| `block.getZ()` | `block.location.z` | | Low |
| `block.getWorld()` | `block.dimension` | | Low |

### Block Interaction

| Java API | Bedrock JavaScript Equivalent | Notes | Complexity |
|-----------|----------------------------|--------|------------|
| `block.breakNaturally()` | `block.destroy()` | | Low |
| `block.getDrops()` | `// Not directly supported` | | High |
| `block.update()` | `// Not directly supported` | | Medium |

---

## Event Handler Mappings

### Block Events

| Java Event | Bedrock Event | Notes | Complexity |
|------------|----------------|--------|------------|
| `BlockBreakEvent` | `world.afterEvents.playerBreakBlock` | | Low |
| `BlockPlaceEvent` | `world.afterEvents.blockPlace` | | Low |
| `BlockFromToEvent` | `// Not directly supported` | | High |
| `BlockPhysicsEvent` | `// Not directly supported` | | High |
| `BlockRedstoneEvent` | `// Not directly supported` | | High |

### Player Events

| Java Event | Bedrock Event | Notes | Complexity |
|------------|----------------|--------|------------|
| `PlayerJoinEvent` | `world.afterEvents.playerJoin` | | Low |
| `PlayerQuitEvent` | `world.afterEvents.playerLeave` | | Low |
| `PlayerChatEvent` | `world.afterEvents.chatSend` | | Low |
| `PlayerInteractEvent` | `world.afterEvents.itemUse` (for items) | Medium |
| `PlayerInteractEntityEvent` | `world.afterEvents.entityHit` | | Medium |
| `PlayerMoveEvent` | `world.beforeEvents.playerMovement` (limited) | Medium |
| `PlayerRespawnEvent` | `world.afterEvents.entitySpawn` (filter players) | Medium |

### Entity Events

| Java Event | Bedrock Event | Notes | Complexity |
|------------|----------------|--------|------------|
| `EntityDeathEvent` | `world.afterEvents.entityDie` | | Low |
| `EntitySpawnEvent` | `world.afterEvents.entitySpawn` | | Low |
| `EntityDamageEvent` | `world.afterEvents.entityHit` | | Low |
| `EntityCombustEvent` | `// Not directly supported` | | Medium |

### Item Events

| Java Event | Bedrock Event | Notes | Complexity |
|------------|----------------|--------|------------|
| `ItemUseEvent` | `world.afterEvents.itemUse` | | Low |
| `ItemUseOnEvent` | `world.afterEvents.itemUseOn` | | Low |
| `PlayerItemConsumeEvent` | `world.afterEvents.itemCompleteUse` | | Low |

### Other Events

| Java Event | Bedrock Event | Notes | Complexity |
|------------|----------------|--------|------------|
| `ServerCommandEvent` | `world.afterEvents.commandExecute` | | Low |
| `ProjectileHitEvent` | `world.afterEvents.projectileHit` | | Medium |
| `InventoryClickEvent` | `// Not directly supported` | High |
| `InventoryCloseEvent` | `// Not directly supported` | High |

---

## Type System Mappings

### Primitive Types

| Java Type | JavaScript Type | Notes |
|------------|----------------|--------|
| `int` | `number` | |
| `double` | `number` | |
| `float` | `number` | |
| `long` | `number` | |
| `boolean` | `boolean` | |
| `String` | `string` | |
| `void` | `void` | |
| `char` | `string` | |

### Collection Types

| Java Type | JavaScript Type | Notes |
|------------|----------------|--------|
| `List<T>` | `Array<T>` | |
| `ArrayList<T>` | `Array<T>` | |
| `LinkedList<T>` | `Array<T>` | |
| `Set<T>` | `Set<T>` | |
| `HashSet<T>` | `Set<T>` | |
| `Map<K, V>` | `Map<K, V>` | |
| `HashMap<K, V>` | `Map<K, V>` | |
| `Queue<T>` | `Array<T>` | |
| `Stack<T>` | `Array<T>` | |
| `Iterator<T>` | `Iterator<T>` | |

### Optional Types

| Java Type | JavaScript Type | Notes |
|------------|----------------|--------|
| `Optional<T>` | `T | null` | Use null checks |
| `OptionalInt` | `number | null` | |
| `OptionalDouble` | `number | null` | |
| `OptionalLong` | `number | null` | |

### Common Enums

| Java Enum | Bedrock String/Constant | Notes |
|-----------|---------------------|--------|
| `BlockFace.DOWN` | `Directions.DOWN` | |
| `BlockFace.UP` | `Directions.UP` | |
| `BlockFace.NORTH` | `Directions.NORTH` | |
| `BlockFace.SOUTH` | `Directions.SOUTH` | |
| `BlockFace.EAST` | `Directions.EAST` | |
| `BlockFace.WEST` | `Directions.WEST` | |
| `EntityType.ZOMBIE` | `'minecraft:zombie'` | |
| `EntityType.SKELETON` | `'minecraft:skeleton'` | |
| `EntityType.PLAYER` | `'minecraft:player'` | |
| `Material.STONE` | `'minecraft:stone'` | |
| `Material.AIR` | `'minecraft:air'` | |

---

## Unsupported Features

### Java Features with No Bedrock Equivalent

These features cannot be directly translated and require smart assumptions:

| Java Feature | Bedrock Limitation | Smart Assumption |
|--------------|-------------------|------------------|
| Custom Dimensions | No dimension creation API | Convert to large structure in Overworld |
| Complex Machinery | No power/redstone logic API | Convert to decorative blocks |
| Custom GUI Screens | No custom UI API | Convert to book/sign interfaces |
| Client-Side Rendering | No Render Dragon access | Exclude with warning |
| NBT Data Manipulation | No NBT equivalent | Use component properties |
| Multi-Block Structures | No multi-block API | Treat as individual blocks |
| Block Update Observers | No update event | Use tick checks (expensive) |
| Custom Particle Effects | Limited particle support | Use built-in particles |
| Sound Pack Customization | Limited sound API | Use built-in sounds |
| Shader Effects | No shader API | Exclude with warning |
| Network Packet Handling | No packet access | Use events where possible |
| Potion Effect Customization | Limited potion API | Use built-in effects |

### High Translation Risk Areas

1. **State Management**: Java objects maintain state; Bedrock is more stateless
2. **Inheritance**: No inheritance in Bedrock; use composition
3. **Interfaces**: No interface support; use duck typing
4. **Reflection**: No reflection API; cannot access private members
5. **Threading**: No threading; use tick events with caution

---

## Translation Limitations

### Known Limitations

1. **Event Timing**: Bedrock event order may differ from Java
2. **Precision**: Floating-point precision differences possible
3. **Performance**: Tick-based polling vs event-driven (less efficient)
4. **Security**: Different permission model
5. **Scope**: Limited API surface area

### Workarounds

1. **State Storage**: Use world.setDynamicProperty / world.getDynamicProperty
2. **Inheritance**: Flatten classes into component-based structures
3. **Interfaces**: Use common function patterns
4. **Reflection**: Avoid; use public APIs only
5. **Threading**: Use tick events sparingly

### Best Practices

1. **Always validate generated JavaScript code**
2. **Check for unsupported APIs before translation**
3. **Provide clear user warnings for functionality loss**
4. **Use RAG to find alternative implementations**
5. **Test translated code in Bedrock environment**

---

## Complexity Legend

| Complexity | Description |
|------------|-------------|
| Low | Direct 1:1 mapping, minimal transformation |
| Medium | Requires pattern change, some logic adjustment |
| High | No direct equivalent, significant redesign needed |

---

## Version Notes

This documentation covers:
- Java Edition: 1.20.x - 1.21.x
- Bedrock Edition: 1.20.10+

Last Updated: 2026-02-19
Document Version: 1.0
