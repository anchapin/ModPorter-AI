# Blockbench Plugin Specification

Version: 1.0.0 (Draft)
Last Updated: 2026-05-06

## Overview

The PortKit Blockbench Plugin integrates Java-to-Bedrock conversion into Blockbench, primarily for projects that need to convert mods containing custom models, textures, or block definitions.

## Target Users

- Modelers and texture artists who receive Java mod assets to convert
- Developers working in Blockbench who need quick asset conversion
- Content creators who work with both Java and Bedrock formats

## Features

- **Convert Mod**: Convert Java mods directly from Blockbench
- **Model Preview**: Preview converted models in the Blockbench viewport
- **Direct Import**: Import converted assets directly into current project

## Technical Specification

### File Structure

```
blockbench/
├── index.js               # Main plugin entry point
├── manifest.json          # Blockbench plugin manifest
├── README.md              # Installation and usage guide
├── SPEC.md                # This specification
└── api/
    └── client.js          # PortKit API client
```

### Manifest.json

```json
{
  "id": "portkit",
  "name": "PortKit",
  "version": "1.0.0",
  "description": "Convert Java Edition mods to Bedrock Edition add-ons",
  "author": "PortKit Team",
  "dependencies": {},
  "tags": ["conversion", "minecraft", "bedrock"],
  "flags": [],
  "icon": "icon.png"
}
```

### Plugin API Usage

```javascript
// Main entry point
module.exports = {
  load() {
    console.log('[PortKit] Plugin loaded');

    this.registerAction();
    this.registerMenu();
  },

  registerAction() {
    Blockbench.addAction({
      id: 'portkit.convert',
      name: 'Convert from Java',
      icon: 'icon.png',
      click: (event) => this.showConvertDialog()
    });
  },

  registerMenu() {
    MenuBar.addMenu({
      id: 'portkit.menu',
      name: 'PortKit',
      items: [
        {
          id: 'convert',
          name: 'Convert from Java...',
          icon: 'refresh',
          click: () => this.showConvertDialog()
        },
        { type: 'separator' },
        {
          id: 'settings',
          name: 'Settings...',
          icon: 'settings',
          click: () => this.showSettings()
        }
      ]
    });
  },

  async showConvertDialog() {
    // Show file picker for .jar/.zip files
    const file = await Blockbench.pickFile({
      extensions: ['.jar', '.zip'],
      type: 'open'
    });

    if (file) {
      await this.convertFile(file.path, file.name);
    }
  },

  async convertFile(path, name) {
    // Read file and convert via PortKit API
    // Show progress notifications
    // Handle completion
  }
};
```

### API Client

```javascript
// api/client.js
class PortKitClient {
  constructor(options = {}) {
    this.endpoint = options.endpoint || 'https://api.portkit.com/api/v1/plugins';
    this.apiKey = options.apiKey;
  }

  async convert(fileData, fileName, targetVersion = '1.20.0') {
    const response = await fetch(`${this.endpoint}/convert`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(this.apiKey ? { 'Authorization': `Bearer ${this.apiKey}` } : {})
      },
      body: JSON.stringify({
        plugin_type: 'blockbench',
        file_data: fileData, // base64
        file_name: fileName,
        target_version: targetVersion
      })
    });

    if (!response.ok) {
      throw new Error(`Conversion failed: ${response.statusText}`);
    }

    return response.json();
  }

  async getStatus(jobId) {
    const response = await fetch(`${this.endpoint}/convert/${jobId}/status`, {
      headers: {
        'Authorization': `Bearer ${this.apiKey}`
      }
    });
    return response.json();
  }

  async download(jobId) {
    const response = await fetch(`${this.endpoint}/convert/${jobId}/download`);
    return response.arrayBuffer();
  }
}

module.exports = PortKitClient;
```

## Blockbench Compatibility

### Required Version
- Blockbench 4.8.0 or later

### Supported Platforms
- Windows (x64)
- macOS (x64, ARM64)
- Linux (x64)

### Plugin Flags
- `node` - Required for file system access (when packaging for desktop)

## Implementation Notes

### File Reading

In desktop mode, use Node.js `fs` module:
```javascript
const fs = require('fs');
const fileBuffer = fs.readFileSync(filePath);
const base64 = fileBuffer.toString('base64');
```

In web mode, use FileReader API.

### Model Preview

After conversion, if the converted addon contains `.json` model files, offer to:
1. Import models into current project
2. Open models in a new tab
3. Preview in viewport

## Testing

- Manual testing on each supported platform
- Verify file picker works correctly
- Verify API communication

## Milestones

1. **v1.0.0**: Basic conversion via menu action
2. **v1.1.0**: Direct model import and preview
3. **v1.2.0**: Batch conversion support