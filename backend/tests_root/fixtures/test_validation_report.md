# ModPorter AI Test Mod Validation Report

```
================================================================================
MODPORTER AI TEST MOD VALIDATION REPORT
================================================================================

📊 SUMMARY:
   Total test mods: 12
   Valid mods: 10
   Invalid mods: 2
   Success rate: 83.3%

📁 EXISTING CATEGORY (3 mods):
------------------------------------------------------------
   ❌ INVALID placeholder
      🚨 Errors: 1
         - Invalid ZIP/JAR file format

   ❌ INVALID simple_test_mod
      🚨 Errors: 1
         - Invalid ZIP/JAR file format

   ✅ VALID simple_copper_block
      Features: Fabric mod ID: simple_copper, Java sources: 2, Class files: 1...
      🎯 Conversion challenges: Mixin bytecode manipulation, Java to Bedrock API mapping...


📁 COMPLEX_LOGIC CATEGORY (3 mods):
------------------------------------------------------------
   ✅ VALID machinery_logic_mod
      Features: Fabric mod ID: machinery_logic_mod, machinery: Machine, Block entities: 1...
      ⚠️  Warnings: 1
      🎯 Conversion challenges: Complex state management, Multi-block structure recognition...

   ✅ VALID automation_logic_mod
      Features: Fabric mod ID: automation_logic_mod, automation: Automation, automation: Node...
      ⚠️  Warnings: 1
      🎯 Conversion challenges: Complex state management, Multi-block structure recognition...

   ✅ VALID multiblock_logic_mod
      Features: Fabric mod ID: multiblock_logic_mod, multiblock: Multiblock, multiblock: Controller...
      ⚠️  Warnings: 1
      🎯 Conversion challenges: Complex state management, Multi-block structure recognition...


📁 ENTITIES CATEGORY (3 mods):
------------------------------------------------------------
   ✅ VALID custom_ai_entity_mod
      Features: Fabric mod ID: custom_ai_entity_mod, Entity classes: 1, Entity textures: 1...
      ⚠️  Warnings: 1
      🎯 Conversion challenges: Entity AI behavior conversion, Entity model format conversion...

   ✅ VALID passive_entity_mod
      Features: Fabric mod ID: passive_entity_mod, Entity classes: 1, Entity textures: 1...
      ⚠️  Warnings: 1
      🎯 Conversion challenges: Entity AI behavior conversion, Entity model format conversion...

   ✅ VALID hostile_entity_mod
      Features: Fabric mod ID: hostile_entity_mod, Entity classes: 1, Entity textures: 1...
      ⚠️  Warnings: 1
      🎯 Conversion challenges: Entity AI behavior conversion, Entity model format conversion...


📁 EXPECTED_OUTPUTS CATEGORY (0 mods):
------------------------------------------------------------

📁 GUI_MODS CATEGORY (3 mods):
------------------------------------------------------------
   ✅ VALID hud_gui_mod
      Features: Fabric mod ID: hud_gui_mod, GUI classes: 2, GUI textures: 1...
      ⚠️  Warnings: 1
      🎯 Conversion challenges: Custom GUI layout conversion, Screen interaction mapping...

   ✅ VALID config_gui_mod
      Features: Fabric mod ID: config_gui_mod, GUI classes: 2, GUI textures: 1...
      ⚠️  Warnings: 1
      🎯 Conversion challenges: Custom GUI layout conversion, Screen interaction mapping...

   ✅ VALID inventory_gui_mod
      Features: Fabric mod ID: inventory_gui_mod, GUI classes: 3, GUI textures: 1...
      ⚠️  Warnings: 1
      🎯 Conversion challenges: Custom GUI layout conversion, Screen interaction mapping...


================================================================================
✅ VALIDATION COMPLETE
   Test suite ready for ModPorter AI conversion testing!
================================================================================
```
