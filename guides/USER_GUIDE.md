# ModPorter AI User Guide

## 🎯 Overview

ModPorter AI is an intelligent tool that converts Minecraft Java Edition mods to Bedrock Edition add-ons using AI-powered analysis and automated conversion processes.

### Key Features
- **One-Click Conversion**: Upload or provide URL for instant conversion
- **AI-Powered Analysis**: Smart detection and conversion of mod components
- **Real-Time Progress**: Live updates during conversion process
- **Behavior Editor**: Visual editing of converted behaviors
- **Performance Optimization**: Automatic optimization for Bedrock performance
- **Comprehensive Reports**: Detailed conversion reports with insights

## 🚀 Getting Started

### Prerequisites
- Modern web browser (Chrome, Firefox, Safari, Edge)
- Stable internet connection
- Java mod files (.jar) or mod pack URLs

### Quick Start

1. **Access the Application**
   - Open your web browser
   - Navigate to `http://localhost:3000` (development) or your deployment URL

2. **Start Your First Conversion**
   - Click "Start Conversion" on the main page
   - Choose your input method:
     - **File Upload**: Drag and drop or browse for `.jar` files
     - **URL Input**: Paste CurseForge, Modrinth, or direct download URLs

3. **Configure Conversion Options**
   - **Smart Assumptions**: Let AI make intelligent decisions for unclear mappings
   - **Include Dependencies**: Automatically include required dependencies
   - **Target Version**: Select Minecraft Bedrock Edition version

4. **Monitor Progress**
   - Real-time progress bar shows conversion stages
   - Live updates for each processing step
   - Estimated time remaining

5. **Download Results**
   - Download converted `.mcaddon` file
   - View detailed conversion report
   - Access behavior editor for fine-tuning

## 📁 Supported Input Formats

### File Uploads
- **Single Mods**: `.jar` files containing individual mods
- **Mod Packs**: `.zip` files containing multiple mods
- **Maximum File Size**: 100MB per file
- **Multiple Files**: Upload up to 10 files simultaneously

### URL Sources
- **CurseForge**: Direct project or file URLs
- **Modrinth**: Project and version URLs
- **Direct Downloads**: HTTP/HTTPS URLs to `.jar` files
- **GitHub Releases**: Direct file download links

## 🔧 Conversion Options

### Smart Assumptions
When enabled, the AI makes intelligent decisions for:
- Block property mappings
- Entity behavior translations
- Recipe conversions
- Texture adaptations

### Dependencies
- **Automatic Detection**: Scans for required dependencies
- **Version Matching**: Finds compatible Bedrock alternatives
- **Conflict Resolution**: Identifies and resolves mod conflicts

### Target Platforms
- **Minecraft Bedrock Edition**: Latest stable release
- **Custom Platforms**: Legacy versions for specific needs
- **Performance Profiles**: Optimized for different device types

## 📊 Understanding Conversion Results

### Success Metrics
- **Overall Success Rate**: Percentage of successfully converted components
- **Component Breakdown**: Success rates for blocks, items, entities, etc.
- **Quality Score**: AI assessment of conversion quality

### Conversion Report
Each conversion includes a detailed report with:
- **Summary**: Overview of conversion success and issues
- **Component Details**: Status of each converted component
- **Changes Made**: List of all transformations applied
- **Limitations**: Known issues or unsupported features
- **Recommendations**: Suggestions for manual improvements

### Download Options
- **Complete Package**: `.mcaddon` file ready for installation
- **Source Files**: Raw converted files for developers
- **Behavior JSON**: Separated behavior files for customization
- **Report PDF**: Printable conversion summary

## 🎨 Using the Behavior Editor

### Access
- Click "Edit Behaviors" from conversion results
- Access from the main menu under "Tools"

### Features
- **Visual Editor**: Drag-and-drop interface for behavior editing
- **Code View**: Direct JSON editing with syntax highlighting
- **Validation**: Real-time validation of behavior JSON
- **Preview**: Test behavior changes before applying
- **Templates**: Pre-built behavior patterns for common use cases

### Common Use Cases
- **Block Properties**: Modify break speed, light emission, etc.
- **Entity Behaviors**: Adjust AI, movement, and interactions
- **Item Behaviors**: Configure usage, durability, and effects
- **Recipe Changes**: Add or modify crafting recipes

## 🔍 Troubleshooting

### Common Issues

#### Conversion Fails
- **Check File Format**: Ensure files are valid `.jar` or `.zip`
- **Verify URL**: Make sure URLs are accessible and contain valid files
- **File Size**: Large files may time out; try smaller files first
- **Network**: Check internet connection for URL-based conversions

#### Partial Success
- **Review Report**: Check conversion report for specific issues
- **Dependencies**: Missing dependencies may cause partial failures
- **Compatibility**: Some Java features have no Bedrock equivalent

#### Behavior Editor Issues
- **Validation Errors**: Check JSON syntax and required fields
- **Performance**: Complex behaviors may impact game performance
- **Testing**: Always test behaviors in Minecraft Bedrock Edition

### Getting Help

1. **Check Documentation**: Review this guide and API documentation
2. **Review Reports**: Conversion reports often contain specific guidance
3. **Community Support**: Visit our Discord or GitHub Discussions
4. **Bug Reports**: Report issues on GitHub with detailed information

### Performance Tips

#### For Better Conversions
- **Clean Mods**: Use well-structured, clean mod files
- **Single Purpose**: Avoid mods with multiple conflicting purposes
- **Updated Versions**: Use recent mod versions with better compatibility

#### For Performance
- **Moderate Size**: Large mod packs may take significant time
- **Batch Processing**: Process similar mods together for efficiency
- **Resource Usage**: Monitor system resources during conversion

## 📚 Advanced Features

### Batch Conversion
- **Queue Multiple**: Add multiple files/URLs to conversion queue
- **Parallel Processing**: Process compatible conversions simultaneously
- **Progress Tracking**: Monitor all conversions in one view

### Custom Templates
- **Save Configurations**: Save frequently used conversion settings
- **Share Templates**: Export and share conversion templates
- **Version Control**: Track changes to conversion approaches

### API Integration
- **Developer Access**: API keys for programmatic access
- **Webhooks**: Notifications for conversion completion
- **Integration**: Connect with build systems and CI/CD pipelines

## 🛡️ Privacy and Security

### Data Handling
- **Local Processing**: Files are processed securely on our servers
- **Temporary Storage**: Files are automatically deleted after conversion
- **No Data Mining**: We don't store or analyze your mod content

### Best Practices
- **Sensitive Content**: Avoid uploading mods with sensitive information
- **Copyright**: Ensure you have rights to convert and distribute mods
- **Attribution**: Give proper credit to original mod authors

## 📈 Tips for Success

### Before Converting
1. **Test Original**: Ensure the Java mod works correctly
2. **Backup**: Keep original files safe
3. **Documentation**: Review mod documentation for special requirements
4. **Dependencies**: Identify all required dependencies

### During Conversion
1. **Monitor Progress**: Watch for any error messages
2. **Patience**: Complex conversions may take time
3. **Resources**: Ensure sufficient system resources
4. **Network**: Maintain stable internet connection

### After Conversion
1. **Test Thoroughly**: Test converted content in Minecraft Bedrock
2. **Review Report**: Check conversion report for issues
3. **Fine-tune**: Use behavior editor for adjustments
4. **Feedback**: Report issues and provide feedback

## 🔗 Additional Resources

### Documentation
- [API Documentation](../API.md) - Developer API reference
- [Technical Architecture](../ARCHITECTURE.md) - System design details
- [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues and solutions

### Community
- **GitHub Repository**: Source code and issue tracking
- **Discord Server**: Real-time community support
- **YouTube Channel**: Video tutorials and demos
- **Blog**: Updates, tips, and best practices

### Support
- **Help Center**: Comprehensive FAQ and guides
- **Contact Support**: Direct support for premium users
- **Feature Requests**: Suggest new features and improvements

---

## 🎯 Next Steps

Now that you understand how to use ModPorter AI:

1. **Try a Simple Conversion**: Start with a basic block mod
2. **Explore Behavior Editor**: Customize converted behaviors
3. **Join Community**: Connect with other users and developers
4. **Provide Feedback**: Help improve the tool with your experience

Happy converting! 🚀
