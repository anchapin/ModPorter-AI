package com.example.mod;

import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.item.v1.FabricItemSettings;
import net.minecraft.item.Item;
import net.minecraft.item.BlockItem;
import net.minecraft.block.Block;
import net.minecraft.block.AbstractBlock;
import net.minecraft.util.Identifier;
import net.minecraft.util.registry.Registry;

public class TestMod implements ModInitializer {
    public static final String MOD_ID = "test_mod";
    
    // Define a simple copper block
    public static final Block COPPER_BLOCK = new Block(AbstractBlock.Settings.create());
    public static final Item COPPER_BLOCK_ITEM = new BlockItem(COPPER_BLOCK, new FabricItemSettings());
    
    @Override
    public void onInitialize() {
        // Register the copper block
        Registry.register(Registry.BLOCK, new Identifier(MOD_ID, "copper_block"), COPPER_BLOCK);
        Registry.register(Registry.ITEM, new Identifier(MOD_ID, "copper_block"), COPPER_BLOCK_ITEM);
    }
}