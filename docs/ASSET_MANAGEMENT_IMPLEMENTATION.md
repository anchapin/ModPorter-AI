# Asset Management Implementation

This document describes the implementation of the asset management system for the ModPorter-AI addon editor.

## Overview

The asset management system allows users to upload, manage, and organize assets (textures, sounds, models, etc.) associated with their Minecraft Bedrock addons. The implementation consists of backend CRUD operations, API endpoints, and frontend components.

## Backend Implementation

### CRUD Operations

The following CRUD operations have been implemented in `/backend/src/db/crud.py`:

#### `get_addon_asset(session: AsyncSession, asset_id: PyUUID) -> Optional[models.AddonAsset]`

Retrieves a specific addon asset by its ID.

#### `create_addon_asset(session: AsyncSession, *, addon_id: PyUUID, file, asset_type: str, commit: bool = True) -> models.AddonAsset`

Creates a new addon asset entry in the database and saves the file.

#### `update_addon_asset(session: AsyncSession, *, asset_id: PyUUID, file, commit: bool = True) -> Optional[models.AddonAsset]`

Updates an existing addon asset with a new file.

#### `delete_addon_asset(session: AsyncSession, *, asset_id: PyUUID, commit: bool = True) -> Optional[dict]`

Deletes an addon asset from the database and removes the file from storage.

#### `create_addon_asset_from_local_path(session: AsyncSession, *, addon_id: PyUUID, source_file_path: str, asset_type: str, original_filename: Optional[str] = None, commit: bool = True) -> models.AddonAsset`

Creates an addon asset entry from a local file path.

## API Endpoints

The following API endpoints are available in `/backend/src/main.py`:

### POST `/api/v1/addons/{addon_id}/assets`

Uploads a new asset for a given addon.

### GET `/api/v1/addons/{addon_id}/assets/{asset_id}`

Downloads/serves an addon asset file.

### PUT `/api/v1/addons/{addon_id}/assets/{asset_id}`

Replaces an existing asset file and its metadata.

### DELETE `/api/v1/addons/{addon_id}/assets/{asset_id}`

Deletes an addon asset (file and database record).

## Frontend Components

The frontend includes the following components in `/frontend/src/components/Editor/AssetManager/`:

### `AssetManager.tsx`

Main container component that combines asset upload and list components.

### `AssetUpload.tsx`

Handles uploading new assets to an addon.

### `AssetList.tsx`

Displays a list of existing assets and provides actions (delete, replace).

## Usage Examples

### Backend Usage

```python
# Create a new asset
new_asset = await crud.create_addon_asset(
    session=db_session,
    addon_id=addon_id,
    file=uploaded_file,
    asset_type="texture_block"
)

# Get an existing asset
asset = await crud.get_addon_asset(session=db_session, asset_id=asset_id)

# Update an asset
updated_asset = await crud.update_addon_asset(
    session=db_session,
    asset_id=asset_id,
    file=new_uploaded_file
)

# Delete an asset
deleted_info = await crud.delete_addon_asset(
    session=db_session,
    asset_id=asset_id
)
```

### Frontend Usage

The frontend components automatically integrate with the backend API through the `api.ts` service layer. Users can:

1. Upload new assets through the `AssetUpload` component
2. View existing assets in the `AssetList` component
3. Replace or delete assets using the action buttons

## Asset Types

Supported asset types include:
- `texture_block`: Block textures
- `texture_item`: Item textures
- `texture_entity`: Entity textures
- `texture_ui`: UI textures
- `sound_effect`: Sound effects
- `sound_music`: Music tracks
- `model_entity`: Entity models
- `model_block`: Custom block models
- `script`: Script files
- `other`: Other asset types

## File Storage

Assets are stored in a dedicated directory structure:
```
backend/addon_assets/
├── {addon_id}/
│   ├── {asset_uuid}_{original_filename}
│   └── ...
└── ...
```

Each asset is stored with a unique UUID prefix to prevent naming conflicts.

## Security Considerations

- File uploads are validated for type and size
- Asset access is restricted to the owning addon
- All API endpoints require proper authentication (handled by existing middleware)

## Git LFS for Large Assets

To keep the repository size manageable, large binary files should be tracked using [Git LFS](https://git-lfs.github.com/).

### Tracked File Types
The following file types are automatically tracked by Git LFS as configured in `.gitattributes`:
- **Archives:** `.jar`, `.zip`
- **Images:** `.png`, `.jpg`, `.jpeg`, `.gif`
- **Audio:** `.wav`, `.mp3`, `.ogg`
- **Video:** `.mp4`, `.mov`
- **Binaries:** `.bin`, `.exe`, `.dll`, `.so`, `.dylib`, `.msi`

### Repository Constraints
- **Maximum File Size:** The CI pipeline enforces a maximum file size of **10MB** for files not tracked by Git LFS.
- **LFS Usage:** Any file larger than 10MB MUST be tracked via Git LFS or reduced in size before committing.

## Future Improvements

Potential enhancements for the asset management system:
1. Asset preview thumbnails
2. Batch asset operations
3. Asset categorization and tagging
4. Version control for assets
5. Asset compression and optimization
