# PortKit Plugin for bridge.

Convert Minecraft Java Edition mods to Bedrock Edition add-ons directly from the bridge. IDE.

## Features

- **One-click conversion**: Select a `.jar` or `.zip` mod file and convert to Bedrock format
- **Seamless integration**: Works with your existing bridge. workflow
- **Real-time progress**: Track conversion progress with notifications
- **Automatic import**: Converted add-ons can be automatically imported into your project

## Requirements

- bridge. v2.0.0 or later
- PortKit API key (get one at https://portkit.com)

## Installation

### From Source

1. Clone the repository:
   ```bash
   git clone https://github.com/anchapin/portkit.git
   cd portkit/plugins/bridge
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Build the plugin:
   ```bash
   npm run build
   ```

4. Copy the output to your bridge. plugins directory:
   ```bash
   # On macOS/Linux
   cp -r dist/* ~/.config/bridge./plugins/portkit/

   # On Windows
   copy dist\* %APPDATA%\bridge.\plugins\portkit\
   ```

### From Marketplace (when available)

1. Open bridge.
2. Go to Settings > Plugins
3. Search for "PortKit"
4. Click Install

## Configuration

1. Open bridge. Settings
2. Navigate to Plugins > PortKit
3. Enter your PortKit API key
4. Optionally customize the API endpoint (for self-hosted instances)

## Usage

### Converting a Mod

1. **Select a mod file** in the bridge. file browser:
   - Right-click on a `.jar` or `.zip` file
   - Select "Convert to Bedrock" from the context menu

   Or use the action panel:
   - Click the PortKit icon in the action bar
   - Select "Convert from Java"

2. **Wait for conversion** - you'll receive notifications as progress updates come in

3. **Get your converted add-on** - once complete, the `.mcaddon` file will be saved and you can choose to import it directly into your project

### Checking Conversion Status

If you want to check the status of a recent conversion:

1. Click the PortKit icon in the action bar
2. Select "Check Conversion Status"

## Troubleshooting

### "No mod file selected"
- Ensure you've selected a `.jar` or `.zip` file before invoking the conversion
- Right-click on the file in the file browser to bring up the context menu

### "Conversion failed"
- Check your internet connection
- Verify your API key is valid in PortKit settings
- Ensure the mod file isn't corrupted or password-protected
- Check that the file size is under 100MB

### "API error"
- Make sure the PortKit API is accessible from your network
- If using a custom API endpoint, verify it's correct in settings

## Development

### Project Structure

```
bridge/
├── src/
│   └── index.ts          # Main plugin code
├── dist/                  # Compiled output
├── package.json          # NPM configuration
├── tsconfig.json         # TypeScript configuration
├── manifest.json         # bridge. plugin manifest
└── API_CONTRACT.md       # API specification
```

### Building

```bash
# Development build with watch mode
npm run watch

# Production build
npm run build
```

### Testing

```bash
# Run TypeScript type checking
npx tsc --noEmit
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      bridge. IDE                        │
│  ┌─────────────────────────────────────────────────┐   │
│  │              PortKit Plugin                       │   │
│  │  - File selection & context menu               │   │
│  │  - Base64 encoding of mod files                 │   │
│  │  - Polling for conversion status                │   │
│  │  - Download & import converted add-ons         │   │
│  └──────────────────────┬──────────────────────────┘   │
└─────────────────────────┼───────────────────────────────┘
                          │ HTTPS (REST)
                          ▼
┌─────────────────────────────────────────────────────────┐
│               PortKit Cloud API                         │
│  /api/v1/plugins/convert     - Start conversion        │
│  /api/v1/plugins/convert/{id} - Check status           │
│  /api/v1/plugins/convert/{id} - Download result        │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│            Conversion Engine & AI Pipeline             │
│  - Java mod analysis                                   │
│  - Bedrock add-on generation                           │
│  - Asset conversion                                    │
│  - Packaging (.mcaddon creation)                       │
└─────────────────────────────────────────────────────────┘
```

## License

MIT License - see https://github.com/anchapin/portkit/blob/main/LICENSE