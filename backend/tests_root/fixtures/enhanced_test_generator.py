"""
Enhanced Test Mod Generator for ModPorter AI
Creates comprehensive test mods covering entities, GUIs, complex logic, and more.

Implements Issue #213: Create Curated Test Sample Repository
"""

import json
import zipfile
from pathlib import Path
from typing import Dict, List, Optional


class EnhancedTestModGenerator:
    """Generates diverse test mods for comprehensive ModPorter AI testing."""
    
    def __init__(self, output_dir: Optional[str] = None):
        """Initialize the enhanced test mod generator.
        
        Args:
            output_dir: Directory to create test mods in
        """
        if output_dir:
            self.output_dir = Path(output_dir)
            self.output_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.output_dir = Path(__file__).parent / "test_mods"
            self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.created_mods = []
    
    def create_entity_mod(self, mod_type: str = "passive") -> Path:
        """Create test mod with custom entities.
        
        Args:
            mod_type: Type of entity mod - 'passive', 'hostile', or 'custom_ai'
            
        Returns:
            Path to created JAR file
        """
        mod_name = f"{mod_type}_entity_mod"
        jar_path = self.output_dir / "entities" / f"{mod_name}.jar"
        jar_path.parent.mkdir(parents=True, exist_ok=True)
        
        with zipfile.ZipFile(jar_path, 'w') as zf:
            # Fabric mod metadata
            fabric_mod = {
                "schemaVersion": 1,
                "id": mod_name,
                "version": "1.0.0",
                "name": f"{mod_type.title()} Entity Test Mod",
                "description": f"Test mod with {mod_type} entities for ModPorter AI testing",
                "authors": ["ModPorter AI Test Suite"],
                "license": "MIT",
                "environment": "*",
                "entrypoints": {
                    "main": [f"com.example.{mod_name}.{mod_type.title()}EntityMod"]
                },
                "depends": {
                    "fabricloader": ">=0.14.0",
                    "minecraft": "~1.19.2"
                }
            }
            zf.writestr('fabric.mod.json', json.dumps(fabric_mod, indent=2))
            
            # Create entity class based on type
            if mod_type == "passive":
                entity_class = self._create_passive_entity_class(mod_name)
            elif mod_type == "hostile":
                entity_class = self._create_hostile_entity_class(mod_name)
            else:  # custom_ai
                entity_class = self._create_custom_ai_entity_class(mod_name)
            
            zf.writestr(f'com/example/{mod_name}/{mod_type.title()}Entity.java', entity_class)
            
            # Main mod class
            main_class = f'''package com.example.{mod_name};

import net.fabricmc.api.ModInitializer;
import net.minecraft.entity.EntityType;
import net.minecraft.entity.SpawnGroup;
import net.minecraft.util.Identifier;
import net.minecraft.util.registry.Registry;

public class {mod_type.title()}EntityMod implements ModInitializer {{
    
    public static final EntityType<{mod_type.title()}Entity> {mod_type.upper()}_ENTITY = EntityType.Builder
        .create({mod_type.title()}Entity::new, SpawnGroup.{"CREATURE" if mod_type == "passive" else "MONSTER"})
        .setDimensions(0.6f, 1.8f)
        .build("{mod_type}_entity");
    
    @Override
    public void onInitialize() {{
        Registry.register(Registry.ENTITY_TYPE, 
                         new Identifier("{mod_name}", "{mod_type}_entity"), 
                         {mod_type.upper()}_ENTITY);
    }}
}}'''
            zf.writestr(f'com/example/{mod_name}/{mod_type.title()}EntityMod.java', main_class)
            
            # Entity texture
            texture_data = self._create_test_texture(16, 32)  # Entity texture size
            zf.writestr(f'assets/{mod_name}/textures/entity/{mod_type}_entity.png', texture_data)
            
            # Entity model
            entity_model = {
                "texture_width": 64,
                "texture_height": 64,
                "elements": [
                    {
                        "name": "head",
                        "from": [4, 24, 4],
                        "to": [12, 32, 12],
                        "faces": {
                            "north": {"uv": [8, 8, 16, 16], "texture": "#0"},
                            "east": {"uv": [0, 8, 8, 16], "texture": "#0"},
                            "south": {"uv": [24, 8, 32, 16], "texture": "#0"},
                            "west": {"uv": [16, 8, 24, 16], "texture": "#0"},
                            "up": {"uv": [8, 0, 16, 8], "texture": "#0"},
                            "down": {"uv": [16, 0, 24, 8], "texture": "#0"}
                        }
                    }
                ]
            }
            zf.writestr(f'assets/{mod_name}/models/entity/{mod_type}_entity.json', 
                       json.dumps(entity_model, indent=2))
            
            # Loot table
            loot_table = {
                "type": "minecraft:entity",
                "pools": [
                    {
                        "rolls": 1,
                        "entries": [
                            {
                                "type": "minecraft:item",
                                "name": "minecraft:string",
                                "weight": 1
                            }
                        ]
                    }
                ]
            }
            zf.writestr(f'data/{mod_name}/loot_tables/entities/{mod_type}_entity.json',
                       json.dumps(loot_table, indent=2))
            
            self._add_common_files(zf, mod_name)
        
        self.created_mods.append(jar_path)
        return jar_path
    
    def create_gui_mod(self, gui_type: str = "inventory") -> Path:
        """Create test mod with custom GUI interfaces.
        
        Args:
            gui_type: Type of GUI - 'inventory', 'config', or 'hud'
            
        Returns:
            Path to created JAR file
        """
        mod_name = f"{gui_type}_gui_mod"
        jar_path = self.output_dir / "gui_mods" / f"{mod_name}.jar"
        jar_path.parent.mkdir(parents=True, exist_ok=True)
        
        with zipfile.ZipFile(jar_path, 'w') as zf:
            # Fabric mod metadata
            fabric_mod = {
                "schemaVersion": 1,
                "id": mod_name,
                "version": "1.0.0",
                "name": f"{gui_type.title()} GUI Test Mod",
                "description": f"Test mod with {gui_type} GUI for ModPorter AI testing",
                "authors": ["ModPorter AI Test Suite"],
                "license": "MIT",
                "environment": "client",
                "entrypoints": {
                    "main": [f"com.example.{mod_name}.{gui_type.title()}GuiMod"],
                    "client": [f"com.example.{mod_name}.client.{gui_type.title()}GuiClient"]
                },
                "depends": {
                    "fabricloader": ">=0.14.0",
                    "minecraft": "~1.19.2"
                }
            }
            zf.writestr('fabric.mod.json', json.dumps(fabric_mod, indent=2))
            
            # Create GUI classes based on type
            if gui_type == "inventory":
                gui_classes = self._create_inventory_gui_classes(mod_name)
            elif gui_type == "config":
                gui_classes = self._create_config_gui_classes(mod_name)
            else:  # hud
                gui_classes = self._create_hud_gui_classes(mod_name)
            
            for class_path, class_content in gui_classes.items():
                zf.writestr(class_path, class_content)
            
            # GUI textures
            gui_texture = self._create_test_texture(256, 256)  # GUI texture size
            zf.writestr(f'assets/{mod_name}/textures/gui/{gui_type}_gui.png', gui_texture)
            
            self._add_common_files(zf, mod_name)
        
        self.created_mods.append(jar_path)
        return jar_path
    
    def create_complex_logic_mod(self, logic_type: str = "machinery") -> Path:
        """Create test mod with complex logic systems.
        
        Args:
            logic_type: Type of complex logic - 'machinery', 'multiblock', or 'automation'
            
        Returns:
            Path to created JAR file
        """
        mod_name = f"{logic_type}_logic_mod"
        jar_path = self.output_dir / "complex_logic" / f"{mod_name}.jar"
        jar_path.parent.mkdir(parents=True, exist_ok=True)
        
        with zipfile.ZipFile(jar_path, 'w') as zf:
            # Fabric mod metadata
            fabric_mod = {
                "schemaVersion": 1,
                "id": mod_name,
                "version": "1.0.0",
                "name": f"{logic_type.title()} Logic Test Mod",
                "description": f"Test mod with {logic_type} logic for ModPorter AI testing",
                "authors": ["ModPorter AI Test Suite"],
                "license": "MIT",
                "environment": "*",
                "entrypoints": {
                    "main": [f"com.example.{mod_name}.{logic_type.title()}LogicMod"]
                },
                "depends": {
                    "fabricloader": ">=0.14.0",
                    "minecraft": "~1.19.2"
                }
            }
            zf.writestr('fabric.mod.json', json.dumps(fabric_mod, indent=2))
            
            # Create complex logic classes
            if logic_type == "machinery":
                logic_classes = self._create_machinery_classes(mod_name)
            elif logic_type == "multiblock":
                logic_classes = self._create_multiblock_classes(mod_name)
            else:  # automation
                logic_classes = self._create_automation_classes(mod_name)
            
            for class_path, class_content in logic_classes.items():
                zf.writestr(class_path, class_content)
            
            # Block states and models
            if logic_type == "machinery":
                blockstate = {
                    "variants": {
                        "facing=north,powered=false": {"model": f"{mod_name}:block/machine_off"},
                        "facing=north,powered=true": {"model": f"{mod_name}:block/machine_on"},
                        "facing=east,powered=false": {"model": f"{mod_name}:block/machine_off", "y": 90},
                        "facing=east,powered=true": {"model": f"{mod_name}:block/machine_on", "y": 90}
                    }
                }
                zf.writestr(f'assets/{mod_name}/blockstates/machine_block.json',
                           json.dumps(blockstate, indent=2))
            
            # Block textures
            block_texture = self._create_test_texture(16, 16)
            zf.writestr(f'assets/{mod_name}/textures/block/{logic_type}_block.png', block_texture)
            
            self._add_common_files(zf, mod_name)
        
        self.created_mods.append(jar_path)
        return jar_path
    
    def _create_passive_entity_class(self, mod_name: str) -> str:
        """Create passive entity class."""
        return f'''package com.example.{mod_name};

import net.minecraft.entity.EntityType;
import net.minecraft.entity.ai.goal.WanderAroundFarGoal;
import net.minecraft.entity.ai.goal.LookAtEntityGoal;
import net.minecraft.entity.ai.goal.LookAroundGoal;
import net.minecraft.entity.passive.AnimalEntity;
import net.minecraft.entity.player.PlayerEntity;
import net.minecraft.server.world.ServerWorld;
import net.minecraft.world.World;

public class PassiveEntity extends AnimalEntity {{
    
    public PassiveEntity(EntityType<? extends PassiveEntity> entityType, World world) {{
        super(entityType, world);
    }}
    
    @Override
    protected void initGoals() {{
        this.goalSelector.add(0, new WanderAroundFarGoal(this, 1.0D));
        this.goalSelector.add(1, new LookAtEntityGoal(this, PlayerEntity.class, 6.0F));
        this.goalSelector.add(2, new LookAroundGoal(this));
    }}
    
    @Override
    public AnimalEntity createChild(ServerWorld world, PassiveEntity entity) {{
        return new PassiveEntity(PassiveEntityMod.PASSIVE_ENTITY, world);
    }}
}}'''
    
    def _create_hostile_entity_class(self, mod_name: str) -> str:
        """Create hostile entity class."""
        return f'''package com.example.{mod_name};

import net.minecraft.entity.EntityType;
import net.minecraft.entity.ai.goal.MeleeAttackGoal;
import net.minecraft.entity.ai.goal.RevengeGoal;
import net.minecraft.entity.ai.goal.WanderAroundFarGoal;
import net.minecraft.entity.ai.goal.LookAtEntityGoal;
import net.minecraft.entity.ai.goal.ActiveTargetGoal;
import net.minecraft.entity.mob.HostileEntity;
import net.minecraft.entity.player.PlayerEntity;
import net.minecraft.world.World;

public class HostileEntity extends HostileEntity {{
    
    public HostileEntity(EntityType<? extends HostileEntity> entityType, World world) {{
        super(entityType, world);
    }}
    
    @Override
    protected void initGoals() {{
        this.goalSelector.add(0, new MeleeAttackGoal(this, 1.0D, false));
        this.goalSelector.add(1, new WanderAroundFarGoal(this, 0.8D));
        this.goalSelector.add(2, new LookAtEntityGoal(this, PlayerEntity.class, 8.0F));
        
        this.targetSelector.add(0, new RevengeGoal(this));
        this.targetSelector.add(1, new ActiveTargetGoal<>(this, PlayerEntity.class, true));
    }}
}}'''
    
    def _create_custom_ai_entity_class(self, mod_name: str) -> str:
        """Create entity with custom AI behavior."""
        return f'''package com.example.{mod_name};

import net.minecraft.entity.EntityType;
import net.minecraft.entity.ai.goal.Goal;
import net.minecraft.entity.ai.goal.WanderAroundFarGoal;
import net.minecraft.entity.ai.goal.LookAtEntityGoal;
import net.minecraft.entity.passive.AnimalEntity;
import net.minecraft.entity.player.PlayerEntity;
import net.minecraft.server.world.ServerWorld;
import net.minecraft.world.World;

public class CustomAiEntity extends AnimalEntity {{
    
    public CustomAiEntity(EntityType<? extends CustomAiEntity> entityType, World world) {{
        super(entityType, world);
    }}
    
    @Override
    protected void initGoals() {{
        this.goalSelector.add(0, new CustomBehaviorGoal(this));
        this.goalSelector.add(1, new WanderAroundFarGoal(this, 1.0D));
        this.goalSelector.add(2, new LookAtEntityGoal(this, PlayerEntity.class, 6.0F));
    }}
    
    private static class CustomBehaviorGoal extends Goal {{
        private final CustomAiEntity entity;
        private int timer = 0;
        
        public CustomBehaviorGoal(CustomAiEntity entity) {{
            this.entity = entity;
        }}
        
        @Override
        public boolean canStart() {{
            return this.entity.age % 100 == 0;
        }}
        
        @Override
        public void tick() {{
            this.timer++;
            // Custom AI behavior: periodically jump
            if (this.timer % 20 == 0) {{
                this.entity.jump();
            }}
        }}
    }}
    
    @Override
    public AnimalEntity createChild(ServerWorld world, CustomAiEntity entity) {{
        return new CustomAiEntity(CustomAiEntityMod.CUSTOM_AI_ENTITY, world);
    }}
}}'''
    
    def _create_inventory_gui_classes(self, mod_name: str) -> Dict[str, str]:
        """Create inventory GUI classes."""
        classes = {}
        
        # Block entity with inventory
        classes[f'com/example/{mod_name}/InventoryBlockEntity.java'] = f'''package com.example.{mod_name};

import net.minecraft.block.BlockState;
import net.minecraft.block.entity.BlockEntity;
import net.minecraft.inventory.Inventories;
import net.minecraft.inventory.Inventory;
import net.minecraft.item.ItemStack;
import net.minecraft.nbt.NbtCompound;
import net.minecraft.util.collection.DefaultedList;
import net.minecraft.util.math.BlockPos;

public class InventoryBlockEntity extends BlockEntity implements Inventory {{
    private DefaultedList<ItemStack> items = DefaultedList.ofSize(9, ItemStack.EMPTY);
    
    public InventoryBlockEntity(BlockPos pos, BlockState state) {{
        super(InventoryGuiMod.INVENTORY_BLOCK_ENTITY, pos, state);
    }}
    
    @Override
    public int size() {{
        return this.items.size();
    }}
    
    @Override
    public boolean isEmpty() {{
        return this.items.stream().allMatch(ItemStack::isEmpty);
    }}
    
    @Override
    public ItemStack getStack(int slot) {{
        return this.items.get(slot);
    }}
    
    @Override
    public ItemStack removeStack(int slot, int amount) {{
        return Inventories.splitStack(this.items, slot, amount);
    }}
    
    @Override
    public ItemStack removeStack(int slot) {{
        return Inventories.removeStack(this.items, slot);
    }}
    
    @Override
    public void setStack(int slot, ItemStack stack) {{
        this.items.set(slot, stack);
        if (stack.getCount() > this.getMaxCountPerStack()) {{
            stack.setCount(this.getMaxCountPerStack());
        }}
    }}
    
    @Override
    public void readNbt(NbtCompound nbt) {{
        super.readNbt(nbt);
        this.items = DefaultedList.ofSize(this.size(), ItemStack.EMPTY);
        Inventories.readNbt(nbt, this.items);
    }}
    
    @Override
    public void writeNbt(NbtCompound nbt) {{
        super.writeNbt(nbt);
        Inventories.writeNbt(nbt, this.items);
    }}
}}'''
        
        # Screen handler
        classes[f'com/example/{mod_name}/InventoryScreenHandler.java'] = f'''package com.example.{mod_name};

import net.minecraft.entity.player.PlayerEntity;
import net.minecraft.entity.player.PlayerInventory;
import net.minecraft.inventory.Inventory;
import net.minecraft.inventory.SimpleInventory;
import net.minecraft.screen.ScreenHandler;
import net.minecraft.screen.slot.Slot;

public class InventoryScreenHandler extends ScreenHandler {{
    private final Inventory inventory;
    
    public InventoryScreenHandler(int syncId, PlayerInventory playerInventory) {{
        this(syncId, playerInventory, new SimpleInventory(9));
    }}
    
    public InventoryScreenHandler(int syncId, PlayerInventory playerInventory, Inventory inventory) {{
        super(InventoryGuiMod.INVENTORY_SCREEN_HANDLER, syncId);
        this.inventory = inventory;
        
        // Add custom inventory slots
        for (int i = 0; i < 3; ++i) {{
            for (int j = 0; j < 3; ++j) {{
                this.addSlot(new Slot(inventory, j + i * 3, 62 + j * 18, 17 + i * 18));
            }}
        }}
        
        // Add player inventory slots
        for (int i = 0; i < 3; ++i) {{
            for (int j = 0; j < 9; ++j) {{
                this.addSlot(new Slot(playerInventory, j + i * 9 + 9, 8 + j * 18, 84 + i * 18));
            }}
        }}
        
        // Add hotbar slots
        for (int i = 0; i < 9; ++i) {{
            this.addSlot(new Slot(playerInventory, i, 8 + i * 18, 142));
        }}
    }}
    
    @Override
    public boolean canUse(PlayerEntity player) {{
        return this.inventory.canPlayerUse(player);
    }}
}}'''
        
        return classes
    
    def _create_config_gui_classes(self, mod_name: str) -> Dict[str, str]:
        """Create config GUI classes."""
        classes = {}
        
        classes[f'com/example/{mod_name}/ConfigScreen.java'] = f'''package com.example.{mod_name};

import net.minecraft.client.gui.screen.Screen;
import net.minecraft.client.gui.widget.ButtonWidget;
import net.minecraft.client.gui.widget.TextFieldWidget;
import net.minecraft.client.util.math.MatrixStack;
import net.minecraft.text.Text;

public class ConfigScreen extends Screen {{
    private final Screen parent;
    private TextFieldWidget nameField;
    private ButtonWidget saveButton;
    
    public ConfigScreen(Screen parent) {{
        super(Text.literal("Configuration"));
        this.parent = parent;
    }}
    
    @Override
    protected void init() {{
        // Name field
        this.nameField = new TextFieldWidget(this.textRenderer, 
                                           this.width / 2 - 100, 60, 200, 20, 
                                           Text.literal("Name"));
        this.addSelectableChild(this.nameField);
        
        // Save button
        this.saveButton = ButtonWidget.builder(Text.literal("Save"), 
                                             button -> this.saveConfig())
                                      .dimensions(this.width / 2 - 50, 100, 100, 20)
                                      .build();
        this.addDrawableChild(this.saveButton);
        
        // Cancel button
        this.addDrawableChild(ButtonWidget.builder(Text.literal("Cancel"), 
                                                  button -> this.client.setScreen(this.parent))
                                         .dimensions(this.width / 2 - 50, 130, 100, 20)
                                         .build());
    }}
    
    private void saveConfig() {{
        // Save configuration logic
        this.client.setScreen(this.parent);
    }}
    
    @Override
    public void render(MatrixStack matrices, int mouseX, int mouseY, float delta) {{
        this.renderBackground(matrices);
        super.render(matrices, mouseX, mouseY, delta);
        
        this.drawCenteredText(matrices, this.textRenderer, this.title, 
                             this.width / 2, 20, 0xFFFFFF);
    }}
}}'''
        
        return classes
    
    def _create_hud_gui_classes(self, mod_name: str) -> Dict[str, str]:
        """Create HUD overlay classes."""
        classes = {}
        
        classes[f'com/example/{mod_name}/client/HudOverlay.java'] = f'''package com.example.{mod_name}.client;

import net.fabricmc.fabric.api.client.rendering.v1.HudRenderCallback;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.util.math.MatrixStack;
import net.minecraft.text.Text;

public class HudOverlay implements HudRenderCallback {{
    
    @Override
    public void onHudRender(MatrixStack matrixStack, float tickDelta) {{
        MinecraftClient client = MinecraftClient.getInstance();
        
        if (client.player != null && !client.options.debugEnabled) {{
            int x = 10;
            int y = 10;
            
            // Draw custom HUD element
            client.textRenderer.draw(matrixStack, 
                                   Text.literal("Custom HUD: " + client.player.getHealth()),
                                   x, y, 0xFFFFFF);
        }}
    }}
}}'''
        
        return classes
    
    def _create_machinery_classes(self, mod_name: str) -> Dict[str, str]:
        """Create machinery logic classes."""
        classes = {}
        
        classes[f'com/example/{mod_name}/MachineBlock.java'] = f'''package com.example.{mod_name};

import net.minecraft.block.Block;
import net.minecraft.block.BlockState;
import net.minecraft.block.entity.BlockEntity;
import net.minecraft.entity.player.PlayerEntity;
import net.minecraft.state.StateManager;
import net.minecraft.state.property.BooleanProperty;
import net.minecraft.state.property.Properties;
import net.minecraft.util.ActionResult;
import net.minecraft.util.Hand;
import net.minecraft.util.hit.BlockHitResult;
import net.minecraft.util.math.BlockPos;
import net.minecraft.world.World;

public class MachineBlock extends Block {{
    public static final BooleanProperty POWERED = Properties.POWERED;
    
    public MachineBlock(Settings settings) {{
        super(settings);
        this.setDefaultState(this.stateManager.getDefaultState().with(POWERED, false));
    }}
    
    @Override
    public ActionResult onUse(BlockState state, World world, BlockPos pos, 
                            PlayerEntity player, Hand hand, BlockHitResult hit) {{
        if (!world.isClient) {{
            // Toggle machine power
            boolean powered = state.get(POWERED);
            world.setBlockState(pos, state.with(POWERED, !powered));
            
            BlockEntity blockEntity = world.getBlockEntity(pos);
            if (blockEntity instanceof MachineBlockEntity) {{
                ((MachineBlockEntity) blockEntity).setPowered(!powered);
            }}
        }}
        return ActionResult.SUCCESS;
    }}
    
    @Override
    protected void appendProperties(StateManager.Builder<Block, BlockState> builder) {{
        builder.add(POWERED);
    }}
}}'''
        
        classes[f'com/example/{mod_name}/MachineBlockEntity.java'] = f'''package com.example.{mod_name};

import net.minecraft.block.BlockState;
import net.minecraft.block.entity.BlockEntity;
import net.minecraft.nbt.NbtCompound;
import net.minecraft.util.Tickable;
import net.minecraft.util.math.BlockPos;

public class MachineBlockEntity extends BlockEntity implements Tickable {{
    private boolean powered = false;
    private int processTime = 0;
    private static final int MAX_PROCESS_TIME = 100;
    
    public MachineBlockEntity(BlockPos pos, BlockState state) {{
        super(MachineryLogicMod.MACHINE_BLOCK_ENTITY, pos, state);
    }}
    
    @Override
    public void tick() {{
        if (this.powered && this.processTime < MAX_PROCESS_TIME) {{
            this.processTime++;
            
            if (this.processTime >= MAX_PROCESS_TIME) {{
                this.completeProcess();
                this.processTime = 0;
            }}
        }}
    }}
    
    private void completeProcess() {{
        // Machine processing logic
        System.out.println("Machine completed processing!");
    }}
    
    public void setPowered(boolean powered) {{
        this.powered = powered;
        this.markDirty();
    }}
    
    @Override
    public void readNbt(NbtCompound nbt) {{
        super.readNbt(nbt);
        this.powered = nbt.getBoolean("powered");
        this.processTime = nbt.getInt("processTime");
    }}
    
    @Override
    public void writeNbt(NbtCompound nbt) {{
        super.writeNbt(nbt);
        nbt.putBoolean("powered", this.powered);
        nbt.putInt("processTime", this.processTime);
    }}
}}'''
        
        return classes
    
    def _create_multiblock_classes(self, mod_name: str) -> Dict[str, str]:
        """Create multiblock structure classes."""
        classes = {}
        
        classes[f'com/example/{mod_name}/MultiblockController.java'] = f'''package com.example.{mod_name};

import net.minecraft.block.entity.BlockEntity;
import net.minecraft.util.math.BlockPos;
import net.minecraft.world.World;
import java.util.HashSet;
import java.util.Set;

public class MultiblockController {{
    private final World world;
    private final BlockPos masterPos;
    private final Set<BlockPos> structureBlocks = new HashSet<>();
    private boolean isFormed = false;
    
    public MultiblockController(World world, BlockPos masterPos) {{
        this.world = world;
        this.masterPos = masterPos;
    }}
    
    public boolean checkStructure() {{
        structureBlocks.clear();
        
        // Check for 3x3x3 structure
        for (int x = -1; x <= 1; x++) {{
            for (int y = 0; y <= 2; y++) {{
                for (int z = -1; z <= 1; z++) {{
                    BlockPos checkPos = masterPos.add(x, y, z);
                    
                    if (isValidStructureBlock(checkPos)) {{
                        structureBlocks.add(checkPos);
                    }} else {{
                        return false;
                    }}
                }}
            }}
        }}
        
        this.isFormed = structureBlocks.size() == 27;
        return this.isFormed;
    }}
    
    private boolean isValidStructureBlock(BlockPos pos) {{
        // Check if block at position is part of valid multiblock structure
        return world.getBlockState(pos).getBlock() instanceof MultiblockBlock;
    }}
    
    public void processMultiblock() {{
        if (!isFormed) return;
        
        // Multiblock processing logic
        for (BlockPos pos : structureBlocks) {{
            BlockEntity entity = world.getBlockEntity(pos);
            if (entity instanceof MultiblockBlockEntity) {{
                ((MultiblockBlockEntity) entity).contribute();
            }}
        }}
    }}
    
    public boolean isFormed() {{
        return isFormed;
    }}
}}'''
        
        return classes
    
    def _create_automation_classes(self, mod_name: str) -> Dict[str, str]:
        """Create automation system classes."""
        classes = {}
        
        classes[f'com/example/{mod_name}/AutomationNode.java'] = f'''package com.example.{mod_name};

import net.minecraft.item.ItemStack;
import net.minecraft.util.math.BlockPos;
import net.minecraft.world.World;
import java.util.ArrayList;
import java.util.List;

public class AutomationNode {{
    private final World world;
    private final BlockPos pos;
    private final List<AutomationNode> connectedNodes = new ArrayList<>();
    private ItemStack buffer = ItemStack.EMPTY;
    
    public AutomationNode(World world, BlockPos pos) {{
        this.world = world;
        this.pos = pos;
    }}
    
    public void connectTo(AutomationNode other) {{
        if (!connectedNodes.contains(other)) {{
            connectedNodes.add(other);
            other.connectedNodes.add(this);
        }}
    }}
    
    public void tick() {{
        // Automation logic: move items through network
        if (!buffer.isEmpty()) {{
            for (AutomationNode node : connectedNodes) {{
                if (node.canReceive(buffer)) {{
                    ItemStack transferred = node.receive(buffer.copy());
                    buffer.decrement(transferred.getCount());
                    
                    if (buffer.isEmpty()) {{
                        break;
                    }}
                }}
            }}
        }}
        
        // Try to extract from connected inventories
        extractFromInventories();
    }}
    
    private void extractFromInventories() {{
        // Extract items from nearby inventories
        // This would interact with nearby chests, machines, etc.
    }}
    
    public boolean canReceive(ItemStack stack) {{
        return buffer.isEmpty() || 
               (ItemStack.canCombine(buffer, stack) && 
                buffer.getCount() + stack.getCount() <= buffer.getMaxCount());
    }}
    
    public ItemStack receive(ItemStack stack) {{
        if (buffer.isEmpty()) {{
            buffer = stack.copy();
            return stack;
        }} else if (ItemStack.canCombine(buffer, stack)) {{
            int canAdd = buffer.getMaxCount() - buffer.getCount();
            int toAdd = Math.min(canAdd, stack.getCount());
            buffer.increment(toAdd);
            
            ItemStack result = stack.copy();
            result.setCount(toAdd);
            return result;
        }}
        return ItemStack.EMPTY;
    }}
}}'''
        
        return classes
    
    def _create_test_texture(self, width: int, height: int) -> bytes:
        """Create a simple test texture as PNG bytes."""
        # Simple PNG header for a test texture
        png_header = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'
            + width.to_bytes(4, 'big') + height.to_bytes(4, 'big') +
            b'\x08\x06\x00\x00\x00\x1f\xf3\xffa\x00\x00\x00\x04gAMA\x00\x00\xb1\x8f'
            b'\x0b\xfca\x05\x00\x00\x00\x01sRGB\x00\xae\xce\x1c\xe9\x00\x00\x00 cHRM'
            b'z%\x00\x00\x80\x83\x00\x00\xf9\x7f\x00\x00\x80\xe9\x00\x00u0\x00\x00'
            b'\xea`\x00\x00:\x98\x00\x00\x17o\x92_\xc5F\x00\x00\x00\tpHYs\x00\x00\x0b'
            b'\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00IEND\xaeB`\x82'
        )
        return png_header
    
    def _add_common_files(self, zf: zipfile.ZipFile, mod_name: str):
        """Add common files to mod JAR."""
        # Manifest file
        manifest = f'''Manifest-Version: 1.0
Created-By: ModPorter AI Test Suite
Specification-Title: {mod_name.replace('_', ' ').title()}
Specification-Version: 1.0.0
Implementation-Title: {mod_name}
Implementation-Version: 1.0.0
'''
        zf.writestr('META-INF/MANIFEST.MF', manifest)
        
        # Pack.mcmeta
        pack_mcmeta = {
            "pack": {
                "pack_format": 9,
                "description": f"{mod_name} test fixture for ModPorter AI"
            }
        }
        zf.writestr('pack.mcmeta', json.dumps(pack_mcmeta, indent=2))
    
    def create_all_test_mods(self) -> List[Path]:
        """Create all test mod categories.
        
        Returns:
            List of paths to created JAR files
        """
        created_mods = []
        
        # Create entity mods
        for entity_type in ["passive", "hostile", "custom_ai"]:
            created_mods.append(self.create_entity_mod(entity_type))
        
        # Create GUI mods
        for gui_type in ["inventory", "config", "hud"]:
            created_mods.append(self.create_gui_mod(gui_type))
        
        # Create complex logic mods
        for logic_type in ["machinery", "multiblock", "automation"]:
            created_mods.append(self.create_complex_logic_mod(logic_type))
        
        return created_mods
    
    def cleanup(self):
        """Clean up created test mods."""
        for mod_path in self.created_mods:
            if mod_path.exists():
                mod_path.unlink()
        self.created_mods.clear()


def create_curated_test_suite(output_dir: Optional[str] = None) -> Dict[str, List[Path]]:
    """Create the complete curated test sample repository.
    
    Args:
        output_dir: Directory to create test mods in
        
    Returns:
        Dictionary mapping category names to lists of created JAR paths
    """
    generator = EnhancedTestModGenerator(output_dir)
    
    test_suite = {
        "entities": [],
        "gui_mods": [],
        "complex_logic": []
    }
    
    # Generate all test mods
    all_mods = generator.create_all_test_mods()
    
    # Categorize the created mods
    for mod_path in all_mods:
        if "entity" in mod_path.name:
            test_suite["entities"].append(mod_path)
        elif "gui" in mod_path.name:
            test_suite["gui_mods"].append(mod_path)
        elif "logic" in mod_path.name:
            test_suite["complex_logic"].append(mod_path)
    
    return test_suite


if __name__ == "__main__":
    # Create all test mods when run directly
    output_dir = Path(__file__).parent / "test_mods"
    test_suite = create_curated_test_suite(str(output_dir))
    
    print("="*60)
    print("CURATED TEST SAMPLE REPOSITORY CREATED")
    print("="*60)
    
    for category, mods in test_suite.items():
        print(f"\n{category.upper()} ({len(mods)} mods):")
        for mod_path in mods:
            size = mod_path.stat().st_size if mod_path.exists() else 0
            print(f"  ✅ {mod_path.name} ({size} bytes)")
    
    total_mods = sum(len(mods) for mods in test_suite.values())
    print(f"\n🎯 Total: {total_mods} comprehensive test mods created")
    print("Ready for ModPorter AI conversion testing!")