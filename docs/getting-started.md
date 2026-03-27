# Getting Started with ModPorter AI

Welcome to ModPorter AI - the first AI-powered tool that converts Minecraft Java Edition mods to Bedrock Edition add-ons. This guide will help you get started with your first conversion.

## What is ModPorter AI?

ModPorter AI automates 60-80% of the work required to convert Java mods to Bedrock add-ons, saving you months of manual rewriting. Our multi-agent AI system:

- Analyzes Java code structure and dependencies
- Translates Java logic to JavaScript (Bedrock Script API)
- Converts textures, models, and sounds
- Validates the conversion for errors
- Packages everything into a ready-to-use .mcaddon file

## Prerequisites

Before you start, make sure you have:

- **A Java mod file** (.jar or .zip) that you want to convert
- **Basic understanding** of Minecraft modding (helpful but not required)
- **A Bedrock testing environment** (Minecraft Bedrock Edition on any platform)

## Quick Start (5 Minutes)

### Step 1: Upload Your Mod

1. Go to [modporter.ai](https://modporter.ai)
2. Click the "Upload Mod" button
3. Select your Java mod file (.jar or .zip)
4. Wait for the initial analysis (usually 30 seconds)

### Step 2: Review the Analysis

Once uploaded, you'll see:
- **Mod structure**: Detected items, blocks, entities
- **Complexity level**: Simple, Moderate, or Complex
- **Estimated conversion time**: 5-30 minutes depending on complexity
- **Potential issues**: Any features that may need manual adjustment

### Step 3: Start Conversion

Click "Start Conversion" and watch real-time progress:
- Java code analysis
- Bedrock code generation
- Asset conversion (textures, models, sounds)
- Quality validation
- Packaging

### Step 4: Download and Test

1. Download the .mcaddon file
2. Open Minecraft Bedrock Edition
3. Double-click the file to install
4. Create a new test world
5. Try out your converted features

## Understanding Conversion Results

### Success Rate

The conversion report shows:
- **Overall success rate**: Percentage of features successfully converted
- **Component inventory**: List of all converted items, blocks, entities
- **Assumptions made**: AI decisions during conversion
- **Manual steps**: What you need to finish yourself

### Common Manual Steps

Even with 60-80% automation, some features need manual work:

1. **Custom behaviors**: Complex logic may need adjustment
2. **GUI elements**: Java GUI doesn't map directly to Bedrock
3. **Network packets**: Bedrock uses different networking
4. **Rendering**: Custom renderers need manual porting

The conversion report will guide you through these steps.

## Next Steps

- Read the [Step-by-Step Tutorial](tutorial.md) for a detailed walkthrough
- Check the [FAQ](faq.md) for common questions
- Join our [Discord community](https://discord.gg/modporter) for help
- Report issues on [GitHub](https://github.com/modporter-ai/issues)

## Troubleshooting

### Conversion Failed

**Problem**: Conversion stopped with an error

**Solutions**:
- Check the error message in the conversion report
- Make sure your mod file is not corrupted
- Verify the mod uses standard Minecraft Forge/Fabric APIs
- Try again - some errors are transient

### Missing Features

**Problem**: Some features didn't convert

**Solutions**:
- Check the "Component Inventory" section of the report
- Look for "Manual Steps Required" notes
- Some Java features don't have Bedrock equivalents
- Consider simplifying your mod for Bedrock

### Add-on Won't Install

**Problem**: .mcaddon file won't install

**Solutions**:
- Make sure you're using Bedrock Edition (not Java)
- Check file size (max 100MB for Marketplace)
- Verify file extension is .mcaddon (not .zip)
- Try importing through Minecraft Settings → Storage

## Getting Help

- **Documentation**: [docs.modporter.ai](https://docs.modporter.ai)
- **Discord**: [discord.gg/modporter](https://discord.gg/modporter)
- **Email**: support@modporter.ai
- **GitHub Issues**: [github.com/modporter-ai/issues](https://github.com/modporter-ai/issues)

## What's Next?

Now that you've completed your first conversion:

1. **Explore advanced features**: Batch conversion, API access
2. **Join the community**: Share your conversions, get feedback
3. **Upgrade to Pro**: Unlimited conversions, priority support
4. **Contribute patterns**: Help improve the AI for everyone

Happy converting!
