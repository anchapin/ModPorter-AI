package com.example.mowziesmobs;

import net.minecraft.block.Block;
import net.minecraft.item.Item;
import net.minecraft.entity.EntityType;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.eventbus.api.IEventBus;
import net.minecraftforge.fml.javafmlmod.FMLJavaModLoadingContext;

@Mod("mowziesmobs")
public class MowziesMobsMod {
    public static final String MOD_ID = "mowziesmobs";
    
    public MowziesMobsMod() {
        IEventBus modEventBus = FMLJavaModLoadingContext.get().getModEventBus();
        
        // Register mod content
        ModBlocks.BLOCKS.register(modEventBus);
        ModItems.ITEMS.register(modEventBus);
        ModEntities.ENTITIES.register(modEventBus);
    }
    
    // Example block class
    public static class ModBlocks {
        public static final Block EXAMPLE_BLOCK = new Block(Block.Properties.create(Material.ROCK));
    }
    
    // Example item class
    public static class ModItems {
        public static final Item EXAMPLE_ITEM = new Item(new Item.Properties());
    }
    
    // Example entity class
    public static class ModEntities {
        public static final EntityType<?> EXAMPLE_ENTITY = EntityType.Builder.create(ExampleEntity::new, EntityClassification.CREATURE).build("example_entity");
    }
}