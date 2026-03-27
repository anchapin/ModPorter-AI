"""
Java pattern registry for common Minecraft modding patterns.

Contains pre-populated Java modding patterns for items, blocks, entities,
recipes, events, and other common mod components.
"""

from typing import Dict, List, Optional
from .base import ConversionPattern


class JavaPatternRegistry:
    """
    Registry of Java modding patterns.

    Pre-populated with 25+ common Java modding patterns from
    Forge, Fabric, and NeoForge.
    """

    def __init__(self):
        """Initialize registry with default patterns."""
        self.patterns: Dict[str, ConversionPattern] = {}
        self._initialize_patterns()

    def _initialize_patterns(self) -> None:
        """Initialize registry with default patterns."""
        # Item Patterns
        self._add_item_patterns()

        # Block Patterns
        self._add_block_patterns()

        # Entity Patterns
        self._add_entity_patterns()

        # Recipe Patterns
        self._add_recipe_patterns()

        # Event Handler Patterns
        self._add_event_patterns()

        # Capability Patterns
        self._add_capability_patterns()

        # Tile Entity Patterns
        self._add_tile_entity_patterns()

        # Network Patterns
        self._add_network_patterns()

    def _add_item_patterns(self) -> None:
        """Add item-related patterns."""
        # Simple Item
        self.patterns["java_simple_item"] = ConversionPattern(
            id="java_simple_item",
            name="Simple Item Registration",
            description="Basic item class extending Item with properties",
            java_example="""public class CustomItem extends Item {
    public CustomItem() {
        super(new Item.Properties()
            .tab(CreativeModeTab.TAB_MISC)
            .stacksTo(64));
    }
}""",
            bedrock_example="See bedrock_simple_item",
            category="item",
            tags=["item", "simple", "registration"],
            complexity="simple",
        )

        # Item with Custom Properties
        self.patterns["java_item_properties"] = ConversionPattern(
            id="java_item_properties",
            name="Item with Custom Properties",
            description="Item with durability, max damage, and creative tab",
            java_example="""public class CustomToolItem extends Item {
    public CustomToolItem() {
        super(new Item.Properties()
            .tab(CreativeModeTab.TAB_TOOLS)
            .durability(500)
            .stacksTo(1));
    }
}""",
            bedrock_example="See bedrock_item_durability",
            category="item",
            tags=["item", "properties", "durability"],
            complexity="simple",
        )

        # Food Item
        self.patterns["java_food_item"] = ConversionPattern(
            id="java_food_item",
            name="Food Item",
            description="Edible item with nutrition value",
            java_example="""public class CustomFoodItem extends Item {
    public CustomFoodItem() {
        super(new Item.Properties()
            .tab(CreativeModeTab.TAB_FOOD)
            .food(new FoodProperties.Builder()
                .nutrition(4)
                .saturationMod(0.6f)
                .build()));
    }
}""",
            bedrock_example="See bedrock_food_item",
            category="item",
            tags=["item", "food", "consumable"],
            complexity="simple",
        )

        # Ranged Weapon Item
        self.patterns["java_ranged_weapon"] = ConversionPattern(
            id="java_ranged_weapon",
            name="Ranged Weapon (Bow-like)",
            description="Item that fires projectiles on use",
            java_example="""public class CustomBowItem extends BowItem {
    @Override
    public void releaseUsing(ItemStack stack, Level level, LivingEntity entity, int charge) {
        if (!level.isClientSide) {
            Projectile projectile = new Arrow(level, entity);
            projectile.shootFromRotation(entity, entity.getXRot(), entity.getYRot(), 0.0f, 2.0f, 1.0f);
            level.addFreshEntity(projectile);
        }
    }
}""",
            bedrock_example="See bedrock_ranged_weapon",
            category="item",
            tags=["item", "weapon", "projectile"],
            complexity="medium",
        )

    def _add_block_patterns(self) -> None:
        """Add block-related patterns."""
        # Simple Block
        self.patterns["java_simple_block"] = ConversionPattern(
            id="java_simple_block",
            name="Simple Block",
            description="Basic block class extending Block",
            java_example="""public class CustomBlock extends Block {
    public CustomBlock() {
        super(BlockBehaviour.Properties.of()
            .mapColor(MapColor.WOOD)
            .strength(2.0f, 3.0f)
            .sound(SoundType.WOOD));
    }
}""",
            bedrock_example="See bedrock_simple_block",
            category="block",
            tags=["block", "simple", "properties"],
            complexity="simple",
        )

        # Block with Custom Properties
        self.patterns["java_block_properties"] = ConversionPattern(
            id="java_block_properties",
            name="Block with State Properties",
            description="Block with directional or integer state properties",
            java_example="""public class CustomStateBlock extends Block {
    public static final IntegerProperty AGE = IntegerProperty.create("age", 0, 3);
    public static final DirectionProperty FACING = DirectionProperty.create("facing");

    public CustomStateBlock() {
        super(BlockBehaviour.Properties.of());
        this.registerDefaultState(this.stateDefinition.any()
            .setValue(AGE, 0)
            .setValue(FACING, Direction.NORTH));
    }

    @Override
    protected void createBlockStateDefinition(StateDefinition.Builder<Block, BlockState> builder) {
        builder.add(AGE, FACING);
    }
}""",
            bedrock_example="See bedrock_block_states",
            category="block",
            tags=["block", "states", "properties"],
            complexity="medium",
        )

        # Rotatable Block
        self.patterns["java_rotatable_block"] = ConversionPattern(
            id="java_rotatable_block",
            name="Rotatable Block (Horizontal)",
            description="Block that can be placed in 4 horizontal directions",
            java_example="""public class CustomRotatableBlock extends HorizontalDirectionalBlock {
    public CustomRotatableBlock() {
        super(BlockBehaviour.Properties.of()
            .mapColor(MapColor.METAL)
            .strength(3.0f));
    }

    @Override
    public BlockState getStateForPlacement(BlockPlaceContext context) {
        return this.defaultBlockState()
            .setValue(FACING, context.getHorizontalDirection().getOpposite());
    }
}""",
            bedrock_example="See bedrock_rotatable_block",
            category="block",
            tags=["block", "rotation", "direction"],
            complexity="medium",
        )

    def _add_entity_patterns(self) -> None:
        """Add entity-related patterns."""
        # Simple Entity
        self.patterns["java_simple_entity"] = ConversionPattern(
            id="java_simple_entity",
            name="Simple Entity",
            description="Basic entity class extending Mob or PathfinderMob",
            java_example="""public class CustomEntity extends PathfinderMob {
    public CustomEntity(EntityType<? extends PathfinderMob> type, Level level) {
        super(type, level);
    }

    @Override
    protected void registerGoals() {
        this.goalSelector.addGoal(0, new FloatGoal(this));
        this.goalSelector.addGoal(1, new RandomStrollGoal(this, 1.0d));
        this.goalSelector.addGoal(2, new LookAtPlayerGoal(this, Player.class, 8.0f));
    }
}""",
            bedrock_example="See bedrock_simple_entity",
            category="entity",
            tags=["entity", "mob", "ai"],
            complexity="medium",
        )

        # Entity Attributes
        self.patterns["java_entity_attributes"] = ConversionPattern(
            id="java_entity_attributes",
            name="Entity with Custom Attributes",
            description="Entity with health, speed, attack damage attributes",
            java_example="""public class CustomEntity extends PathfinderMob {
    public static final AttributeSupplier ATTRIBUTES = DefaultAttributes.getSupplier(EntityType.ZOMBIE)
        .add(Attributes.MAX_HEALTH, 20.0d)
        .add(Attributes.MOVEMENT_SPEED, 0.23d)
        .add(Attributes.ATTACK_DAMAGE, 3.0d);

    @Override
    public AttributeSupplier.Builder getDefaultAttributes() {
        return ATTRIBUTES;
    }
}""",
            bedrock_example="See bedrock_entity_attributes",
            category="entity",
            tags=["entity", "attributes", "stats"],
            complexity="medium",
        )

    def _add_recipe_patterns(self) -> None:
        """Add recipe patterns."""
        # Shaped Recipe
        self.patterns["java_shaped_recipe"] = ConversionPattern(
            id="java_shaped_recipe",
            name="Shaped Crafting Recipe",
            description="3x3 shaped crafting recipe",
            java_example="""public class CustomRecipes {
    public static void register(RecipeHolder register) {
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, Items.DIAMOND, 1)
            .pattern("XXX")
            .pattern("X#X")
            .pattern("XXX")
            .define('X', Items.IRON_INGOT)
            .define('#', Items.GOLD_INGOT)
            .unlockedBy("has_iron", has(Items.IRON_INGOT))
            .save(register, new ResourceLocation("mod", "custom_recipe"));
    }
}""",
            bedrock_example="See bedrock_shaped_recipe",
            category="recipe",
            tags=["recipe", "shaped", "crafting"],
            complexity="simple",
        )

        # Shapeless Recipe
        self.patterns["java_shapeless_recipe"] = ConversionPattern(
            id="java_shapeless_recipe",
            name="Shapeless Crafting Recipe",
            description="Shapeless crafting recipe (any arrangement)",
            java_example="""public class CustomRecipes {
    public static void register(RecipeHolder register) {
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, Items.TORCH, 4)
            .requires(Items.COAL)
            .requires(Items.STICK)
            .unlockedBy("has_coal", has(Items.COAL))
            .save(register, new ResourceLocation("mod", "torch_recipe"));
    }
}""",
            bedrock_example="See bedrock_shapeless_recipe",
            category="recipe",
            tags=["recipe", "shapeless", "crafting"],
            complexity="simple",
        )

        # Smelting Recipe
        self.patterns["java_smelting_recipe"] = ConversionPattern(
            id="java_smelting_recipe",
            name="Smelting Recipe",
            description="Furnace smelting recipe",
            java_example="""public class CustomRecipes {
    public static void register(RecipeHolder register) {
        SimpleCookingRecipeBuilder.smelting(
            Ingredient.of(Items.IRON_ORE),
            RecipeCategory.MISC,
            Items.IRON_INGOT,
            0.7f,
            200
        ).unlockedBy("has_ore", has(Items.IRON_ORE))
         .save(register, new ResourceLocation("mod", "smelting_recipe"));
    }
}""",
            bedrock_example="See bedrock_smelting_recipe",
            category="recipe",
            tags=["recipe", "smelting", "furnace"],
            complexity="simple",
        )

    def _add_event_patterns(self) -> None:
        """Add event handler patterns."""
        # Player Interact Event
        self.patterns["java_player_interact"] = ConversionPattern(
            id="java_player_interact",
            name="Player Interact Event",
            description="Handle player right-click interaction",
            java_example="""@SubscribeEvent
public static void onPlayerInteract(PlayerInteractEvent.RightClickBlock event) {
    Level level = event.getLevel();
    BlockPos pos = event.getPos();
    Player player = event.getEntity();
    ItemStack stack = event.getItemStack();

    if (!level.isClientSide && stack.is(Items.DIAMOND)) {
        level.setBlockAndUpdate(pos, Blocks.GOLD_BLOCK.defaultBlockState());
        event.setCanceled(true);
    }
}""",
            bedrock_example="See bedrock_player_interact",
            category="event",
            tags=["event", "player", "interaction"],
            complexity="simple",
        )

        # Block Break Event
        self.patterns["java_block_break"] = ConversionPattern(
            id="java_block_break",
            name="Block Break Event",
            description="Handle block being broken by player",
            java_example="""@SubscribeEvent
public static void onBlockBreak(BlockEvent.BreakEvent event) {
    Level level = event.getLevel();
    BlockPos pos = event.getPos();
    Player player = event.getPlayer();

    if (!level.isClientSide && level.getBlockState(pos).is(Blocks.DIAMOND_BLOCK)) {
        player.sendSystemMessage(Component.literal("You broke a diamond block!"));
        event.setExpToDrop(100);
    }
}""",
            bedrock_example="See bedrock_block_break",
            category="event",
            tags=["event", "block", "break"],
            complexity="simple",
        )

        # Entity Join World Event
        self.patterns["java_entity_join"] = ConversionPattern(
            id="java_entity_join",
            name="Entity Join World Event",
            description="Handle entity spawning in world",
            java_example="""@SubscribeEvent
public static void onEntityJoin(EntityJoinLevelEvent event) {
    if (!event.getLevel().isClientSide) {
        Entity entity = event.getEntity();
        if (entity instanceof Zombie) {
            Zombie zombie = (Zombie) entity;
            zombie.setCustomName(Component.literal("Custom Zombie"));
        }
    }
}""",
            bedrock_example="See bedrock_entity_spawn",
            category="event",
            tags=["event", "entity", "spawn"],
            complexity="simple",
        )

    def _add_capability_patterns(self) -> None:
        """Add capability patterns."""
        # Item Handler Capability
        self.patterns["java_item_handler"] = ConversionPattern(
            id="java_item_handler",
            name="Item Handler Capability",
            description="Block with inventory (item storage)",
            java_example="""public class CustomItemHandler implements IItemHandler {
    private final NonNullList<ItemStack> stacks = NonNullList.withSize(9, ItemStack.EMPTY);

    @Override
    public int getSlots() {
        return stacks.size();
    }

    @Override
    public ItemStack getStackInSlot(int slot) {
        return slot >= 0 && slot < stacks.size() ? stacks.get(slot) : ItemStack.EMPTY;
    }

    @Override
    public ItemStack insertItem(int slot, ItemStack stack, boolean simulate) {
        if (slot < 0 || slot >= stacks.size() || !stacks.get(slot).isEmpty()) {
            return stack;
        }
        if (!simulate) {
            stacks.set(slot, stack.copy());
        }
        return ItemStack.EMPTY;
    }

    @Override
    public ItemStack extractItem(int slot, int amount, boolean simulate) {
        if (slot < 0 || slot >= stacks.size()) {
            return ItemStack.EMPTY;
        }
        ItemStack existing = stacks.get(slot);
        if (existing.isEmpty()) {
            return ItemStack.EMPTY;
        }
        int toExtract = Math.min(amount, existing.getCount());
        if (!simulate) {
            stacks.set(slot, existing.copyWithCount(existing.getCount() - toExtract));
        }
        return existing.copyWithCount(toExtract);
    }
}""",
            bedrock_example="See bedrock_item_container",
            category="capability",
            tags=["capability", "inventory", "items"],
            complexity="complex",
        )

        # Fluid Handler Capability
        self.patterns["java_fluid_handler"] = ConversionPattern(
            id="java_fluid_handler",
            name="Fluid Handler Capability",
            description="Block with fluid storage tank",
            java_example="""public class CustomFluidHandler implements IFluidHandler {
    private FluidStack fluid = FluidStack.EMPTY;
    private final int capacity = 10000;

    @Override
    public int getTanks() {
        return 1;
    }

    @Override
    public FluidStack getFluidInTank(int tank) {
        return fluid;
    }

    @Override
    public int getTankCapacity(int tank) {
        return capacity;
    }

    @Override
    public boolean isFluidValid(int tank, FluidStack stack) {
        return true;
    }

    @Override
    public int fill(FluidStack resource, FluidAction action) {
        int amount = Math.min(resource.getAmount(), capacity - fluid.getAmount());
        if (action.execute()) {
            fluid = new FluidStack(resource.getFluid(), fluid.getAmount() + amount);
        }
        return amount;
    }

    @Override
    public FluidStack drain(FluidStack resource, FluidAction action) {
        if (fluid.getFluid() != resource.getFluid()) {
            return FluidStack.EMPTY;
        }
        return drain(resource.getAmount(), action);
    }

    @Override
    public FluidStack drain(int maxDrain, FluidAction action) {
        int amount = Math.min(maxDrain, fluid.getAmount());
        FluidStack drained = new FluidStack(fluid.getFluid(), amount);
        if (action.execute()) {
            fluid = new FluidStack(fluid.getFluid(), fluid.getAmount() - amount);
        }
        return drained;
    }
}""",
            bedrock_example="See bedrock_fluid_container",
            category="capability",
            tags=["capability", "fluid", "storage"],
            complexity="complex",
        )

    def _add_tile_entity_patterns(self) -> None:
        """Add tile entity (block entity) patterns."""
        # Simple Tile Entity
        self.patterns["java_tile_entity"] = ConversionPattern(
            id="java_tile_entity",
            name="Simple Tile Entity",
            description="Block entity with data storage",
            java_example="""public class CustomTileEntity extends BlockEntity {
    private int counter = 0;

    public CustomTileEntity(BlockPos pos, BlockState state) {
        super(ModTileEntities.CUSTOM_TILE.get(), pos, state);
    }

    @Override
    public void load(CompoundTag tag) {
        super.load(tag);
        this.counter = tag.getInt("counter");
    }

    @Override
    protected void saveAdditional(CompoundTag tag) {
        super.saveAdditional(tag);
        tag.putInt("counter", this.counter);
    }

    public void increment() {
        this.counter++;
        this.setChanged();
    }

    public int getCounter() {
        return this.counter;
    }
}""",
            bedrock_example="See bedrock_block_entity",
            category="tileentity",
            tags=["tileentity", "storage", "data"],
            complexity="medium",
        )

        # Ticking Tile Entity
        self.patterns["java_ticking_tile"] = ConversionPattern(
            id="java_ticking_tile",
            name="Ticking Tile Entity",
            description="Block entity that updates every tick",
            java_example="""public class CustomTickingTileEntity extends BlockEntity {
    private int tickCounter = 0;

    public CustomTickingTileEntity(BlockPos pos, BlockState state) {
        super(ModTileEntities.CUSTOM_TICKING_TILE.get(), pos, state);
    }

    public static void tick(Level level, BlockPos pos, BlockState state, CustomTickingTileEntity blockEntity) {
        if (!level.isClientSide) {
            blockEntity.tickCounter++;
            if (blockEntity.tickCounter % 20 == 0) {
                // Do something every second
                level.playSound(null, pos, SoundTypes.EXPERIENCE_ORB_PICKUP, SoundSource.BLOCKS, 1.0f, 1.0f);
            }
        }
    }
}""",
            bedrock_example="See bedrock_ticking_block",
            category="tileentity",
            tags=["tileentity", "tick", "update"],
            complexity="medium",
        )

    def _add_network_patterns(self) -> None:
        """Add network packet patterns."""
        # Simple Network Packet
        self.patterns["java_network_packet"] = ConversionPattern(
            id="java_network_packet",
            name="Simple Network Packet",
            description="Custom network packet for client-server communication",
            java_example="""public class CustomPacket {
    public static void register() {
        Instance.register(CustomMessage.class, CustomMessage::encode, CustomMessage::decode, CustomMessage::handle);
    }

    public static class CustomMessage {
        private final String message;
        private final int value;

        public CustomMessage(String message, int value) {
            this.message = message;
            this.value = value;
        }

        public static void encode(CustomMessage msg, FriendlyByteBuf buf) {
            buf.writeUtf(msg.message);
            buf.writeInt(msg.value);
        }

        public static CustomMessage decode(FriendlyByteBuf buf) {
            return new CustomMessage(buf.readUtf(), buf.readInt());
        }

        public static void handle(CustomMessage msg, CustomPayloadEvent.Context ctx) {
            ctx.enqueueWork(() -> {
                // Handle packet on receiving side
                Minecraft.getInstance().player.displayClientMessage(Component.literal(msg.message), true);
            });
            ctx.setPacketHandled(true);
        }
    }
}""",
            bedrock_example="See bedrock_network_packet",
            category="network",
            tags=["network", "packet", "communication"],
            complexity="complex",
        )

    def get_pattern(self, pattern_id: str) -> Optional[ConversionPattern]:
        """
        Get a pattern by ID.

        Args:
            pattern_id: Pattern identifier

        Returns:
            Pattern if found, None otherwise
        """
        return self.patterns.get(pattern_id)

    def get_all_patterns(self) -> List[ConversionPattern]:
        """
        Get all registered patterns.

        Returns:
            List of all patterns
        """
        return list(self.patterns.values())

    def get_by_category(self, category: str) -> List[ConversionPattern]:
        """
        Get all patterns in a category.

        Args:
            category: Category name

        Returns:
            List of patterns in the category
        """
        return [
            pattern
            for pattern in self.patterns.values()
            if pattern.category == category
        ]

    def get_stats(self) -> Dict[str, int]:
        """
        Get registry statistics.

        Returns:
            Dictionary with total patterns and counts by category
        """
        stats = {"total": len(self.patterns)}
        category_counts: Dict[str, int] = {}
        for pattern in self.patterns.values():
            category_counts[pattern.category] = category_counts.get(pattern.category, 0) + 1
        stats["by_category"] = category_counts
        return stats
