# Behavior Editor - Issue #578 Implementation

## Overview

This implementation enhances the visual editor for Bedrock behavior files, providing improved UI/UX features, undo/redo functionality, schema validation, and drag-and-drop file management.

## New Components

### 1. CodeEditorEnhanced (`CodeEditorEnhanced.tsx`)

An enhanced version of the Monaco code editor with the following features:

- **Schema Integration**: Bedrock JSON schemas for real-time validation
- **Auto-Completion**: Context-aware suggestions for Bedrock components
- **Undo/Redo**: Built-in history management (Ctrl+Z / Ctrl+Y)
- **Keyboard Shortcuts**:
  - `Ctrl+S` / `Cmd+S`: Save file
  - `Ctrl+Z` / `Cmd+Z`: Undo
  - `Ctrl+Y` / `Cmd+Y` / `Ctrl+Shift+Z`: Redo
  - `Ctrl+C` / `Cmd+C`: Copy all (if no selection)
- **Status Bar**: Shows cursor position and character count
- **Validation Error Indicator**: Visual count of validation errors
- **Context Menu**: Additional actions (copy, download, upload)

### 2. BehaviorFileTreeEnhanced (`BehaviorFileTreeEnhanced.tsx`)

An enhanced file tree component with:

- **Search/Filter**: Real-time file search
- **Drag and Drop**: Move files between folders
- **Context Menu**: Right-click actions for files and folders
- **File Operations**:
  - Create new files/folders
  - Rename files/folders
  - Delete files/folders
  - Download files
  - Copy file paths
- **Folder Count Badges**: Shows number of items in each folder
- **Visual Icons**: Color-coded icons by file type

### 3. useUndoRedo Hook (`useUndoRedo.ts`)

A reusable hook for undo/redo functionality with:

- **History Management**: Configurable max history size
- **Debounced Updates**: Optional debouncing for performance
- **Function Updates**: Support for function-based state updates
- **History Inspection**: Access to full history state

Usage:
```typescript
const {
  state,
  updateState,
  undo,
  redo,
  canUndo,
  canRedo,
  clearHistory
} = useUndoRedo(initialState, { maxHistory: 50 });
```

### 4. BedrockSchemaLoader (`BedrockSchemaLoader.ts`)

Service for managing Bedrock JSON schemas:

- **Schema Registration**: Load and register JSON schemas
- **Auto-Completion**: Provide context-aware completions
- **Pattern Matching**: Match schemas to file paths
- **Remote Loading**: Load schemas from API endpoints

## Updated Components

### RecipeBuilder (`RecipeBuilder/RecipeBuilder.tsx`)

Enhanced with:

- **Undo/Redo Integration**: Full history support
- **UI Controls**: Undo/redo buttons in toolbar
- **Keyboard Shortcuts**: Ctrl+Z / Ctrl+Y support

## Features Implemented

### Acceptance Criteria Status

- [x] Integrate Monaco editor with Bedrock schemas
- [x] Add real-time JSON validation
- [x] Create visual block property editor (existing)
- [x] Implement recipe builder with drag-and-drop (existing)
- [x] Add file tree with context menus
- [x] Create undo/redo functionality

### Additional Features

- [x] Search/filter functionality in file tree
- [x] Drag-and-drop file organization
- [x] File create/rename/delete operations
- [x] Status bar with cursor position
- [x] Validation error indicators
- [x] Download/upload file actions
- [x] Keyboard shortcuts for common actions

## Testing

### Test Files

1. **useUndoRedo.test.ts**: Comprehensive tests for the undo/redo hook
   - Basic functionality
   - Undo/redo operations
   - History management
   - Debounce options
   - Complex state types
   - Edge cases

2. **RecipeBuilder.test.ts**: Tests for the RecipeBuilder component
   - Initial rendering
   - Recipe type selection
   - Recipe properties editing
   - Recipe grid interactions
   - Undo/redo functionality
   - Validation
   - Read-only mode
   - Recipe saving

### Running Tests

```bash
cd frontend
pnpm test
pnpm test:useUndoRedo
pnpm test:RecipeBuilder
```

## Schema Support

### Bedrock Schemas

The editor includes support for the following Bedrock schemas:

1. **Block Definitions** (`bedrock_block_schema.json`)
   - Location: `frontend/src/schemas/bedrock_block_schema.json`
   - Properties: identifier, components, permutations

2. **Item Definitions** (`bedrock_item_schema.json`)
   - To be loaded from API

3. **Recipe Definitions** (`bedrock_recipe_schema.json`)
   - To be loaded from API

4. **Loot Table Definitions** (`bedrock_loot_table_schema.json`)
   - To be loaded from API

5. **Entity Definitions** (`bedrock_entity_schema.json`)
   - To be loaded from API

### Auto-Completion

The editor provides auto-completion for:

- **Block Components**:
  - `minecraft:display_name`
  - `minecraft:destroy_time`
  - `minecraft:explosion_resistance`
  - `minecraft:friction`
  - `minecraft:light_emission`
  - `minecraft:material`
  - `minecraft:geometry`

## Usage

### Using Enhanced Code Editor

```typescript
import { CodeEditorEnhanced } from './components/BehaviorEditor';

<CodeEditorEnhanced
  fileId={fileId}
  filePath={filePath}
  fileType={fileType}
  onContentChange={handleChange}
  onSave={handleSave}
  readOnly={false}
/>
```

### Using Enhanced File Tree

```typescript
import { BehaviorFileTreeEnhanced } from './components/BehaviorEditor';

<BehaviorFileTreeEnhanced
  conversionId={conversionId}
  onFileSelect={handleFileSelect}
  selectedFileId={selectedFileId}
  readOnly={false}
/>
```

### Using Undo/Redo Hook

```typescript
import { useUndoRedo } from './hooks/useUndoRedo';

const MyComponent = () => {
  const {
    state,
    updateState,
    undo,
    redo,
    canUndo,
    canRedo
  } = useUndoRedo(initialState, {
    maxHistory: 50,
    enableDebounce: true,
    debounceMs: 500
  });

  return (
    <div>
      <button onClick={undo} disabled={!canUndo}>Undo</button>
      <button onClick={redo} disabled={!canRedo}>Redo</button>
    </div>
  );
};
```

## Performance Considerations

1. **Debouncing**: State updates are debounced by default to reduce history entries
2. **History Size**: Default max history is 50 entries to limit memory usage
3. **Schema Loading**: Schemas are loaded on-demand to reduce initial bundle size
4. **Virtualization**: Large file trees use efficient rendering patterns

## Browser Compatibility

- **Monaco Editor**: Requires modern browsers (Chrome, Firefox, Safari, Edge)
- **Drag and Drop**: HTML5 Drag and Drop API
- **Local Storage**: Not currently used, but could be added for persistence

## Future Enhancements

1. **Collaborative Editing**: WebSocket-based real-time collaboration
2. **Offline Support**: Service Worker for offline editing
3. **Version Control**: Integration with Git for file history
4. **Advanced Search**: Full-text search across all behavior files
5. **Plugin System**: Extensible editor with custom plugins
6. **3D Preview**: Live 3D preview of block/entity changes

## Migration Notes

### From Original Components

To migrate from the original components to the enhanced versions:

1. **CodeEditor → CodeEditorEnhanced**:
   - Update import path
   - No breaking changes in props
   - Additional features available automatically

2. **BehaviorFileTree → BehaviorFileTreeEnhanced**:
   - Update import path
   - Same props interface
   - Additional context menu features available

3. **RecipeBuilder**:
   - No import changes needed
   - Undo/redo now integrated automatically

## Known Limitations

1. **Schema Validation**: Only validates structure, not semantics
2. **Large Files**: Files > 1MB may have performance issues
3. **Undo History**: Limited to 50 entries by default
4. **Drag and Drop**: Only works within the file tree

## Dependencies

- **@monaco-editor/react**: Monaco editor integration
- **@mui/material**: UI components
- **React**: Component framework

## Contributing

When adding new features:

1. Follow existing component patterns
2. Add comprehensive tests
3. Update this README
4. Consider accessibility (keyboard shortcuts, screen readers)
5. Test with large files for performance

## License

This implementation is part of the ModPorter AI project.
