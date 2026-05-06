# VS Code Extension Specification

Version: 1.0.0 (Draft)
Last Updated: 2026-05-06

## Overview

The PortKit VS Code Extension brings Java-to-Bedrock conversion directly into the VS Code environment, targeting developers who work with both Java mods and Bedrock add-ons in the same workspace.

## Target Users

- Minecraft mod developers who also create Bedrock add-ons
- Developers using VS Code as their primary editor for Minecraft projects
- Teams with mixed Java/Bedrock development workflows

## Features

- **Convert from Java**: Right-click on `.jar` or `.zip` files to convert
- **Conversion View**: Track active conversions in the VS Code activity bar
- **Output Integration**: Automatically place converted files in Bedrock workspace
- **Status Bar**: Show conversion progress in the VS Code status bar

## Technical Specification

### File Structure

```
vscode/
├── package.json           # Extension manifest
├── tsconfig.json          # TypeScript configuration
├── README.md              # Installation and usage guide
├── SPEC.md                # This specification
├── src/
│   ├── extension.ts       # Main entry point
│   ├── commands/
│   │   └── convert.ts     # Convert command implementation
│   ├── providers/
│   │   └── status.ts      # Status bar and tree view providers
│   └── api/
│       └── client.ts      # PortKit API client
└── .vscodeignore
```

### Package.json Requirements

```json
{
  "name": "portkit-vscode",
  "displayName": "PortKit - Minecraft Converter",
  "version": "1.0.0",
  "engines": {
    "vscode": "^1.85.0"
  },
  "categories": [
    "Other",
    "Programming Languages"
  ],
  "activationEvents": [
    "onCommand:portkit.convert",
    "onView:portkit conversions"
  ],
  "main": "./dist/extension.js",
  "contributes": {
    "commands": [
      {
        "command": "portkit.convert",
        "title": "PortKit: Convert to Bedrock",
        "icon": "$(arrow-swap)"
      }
    ],
    "views": {
      "portkit": [
        {
          "id": "portkit.conversions",
          "name": "PortKit Conversions"
        }
      ]
    },
    "menus": {
      "explorer/context": [
        {
          "command": "portkit.convert",
          "when": "resourceExtname == .jar || resourceExtname == .zip",
          "group": "PortKit"
        }
      ]
    }
  }
}
```

### API Client

```typescript
// src/api/client.ts
interface PortKitClient {
  convert(request: ConversionRequest): Promise<ConversionResponse>;
  getStatus(jobId: string): Promise<ConversionStatus>;
  download(jobId: string): Promise<Uint8Array>;
}

interface ConversionRequest {
  plugin_type: "vscode";
  file_data: string; // base64
  file_name: string;
  target_version?: string;
  options?: Record<string, unknown>;
}
```

### Dependencies

- `@vscode/test-cli` - For integration testing
- `vsce` - For packaging the extension

## Implementation Notes

### Workspace Integration

The extension should detect Bedrock project structure by looking for:
- `bridge.json` at workspace root
- `manifest.json` files
- `BP/` or `RP/` directories

### Conversion Output Location

When conversion completes, offer to:
1. Save to a user-specified location
2. Add to the currently open Bedrock workspace folder
3. Replace the original file (with confirmation)

### Testing Strategy

- Unit tests for API client with mocked responses
- Integration tests for command execution
- UI tests for tree view and status bar updates

## Milestones

1. **v1.0.0**: Basic convert command with status tracking
2. **v1.1.0**: Conversion view and workspace integration
3. **v1.2.0**: Progress notifications and auto-import