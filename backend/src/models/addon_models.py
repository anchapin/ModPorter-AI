from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from uuid import UUID as PyUUID
import datetime


# Timestamps Mixin
class TimestampsModel(BaseModel):
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


# AddonBehavior
class AddonBehaviorBase(BaseModel):
    data: Dict[str, Any] = Field(default_factory=dict)


class AddonBehaviorCreate(AddonBehaviorBase):
    pass


class AddonBehaviorUpdate(AddonBehaviorBase):
    pass


class AddonBehavior(AddonBehaviorBase, TimestampsModel):
    id: PyUUID
    block_id: PyUUID


# AddonRecipe
class AddonRecipeBase(BaseModel):
    data: Dict[str, Any] = Field(default_factory=dict)


class AddonRecipeCreate(AddonRecipeBase):
    pass


class AddonRecipeUpdate(AddonRecipeBase):
    pass


class AddonRecipe(AddonRecipeBase, TimestampsModel):
    id: PyUUID
    addon_id: PyUUID


# AddonAsset
class AddonAssetBase(BaseModel):
    type: str
    path: str
    original_filename: Optional[str] = None


class AddonAssetCreate(AddonAssetBase):
    pass


class AddonAssetUpdate(AddonAssetBase):
    pass


class AddonAsset(AddonAssetBase, TimestampsModel):
    id: PyUUID
    addon_id: PyUUID


# AddonBlock
class AddonBlockBase(BaseModel):
    identifier: str
    properties: Optional[Dict[str, Any]] = Field(default_factory=dict)


class AddonBlockCreate(AddonBlockBase):
    behavior: Optional[AddonBehaviorCreate] = None


class AddonBlockUpdate(AddonBlockBase):
    behavior: Optional[AddonBehaviorUpdate] = None  # Allow updating behavior
    # If behavior is None, it means no change. If behavior is an empty dict or some other signal, it could mean remove.
    # For simplicity, we'll assume providing behavior means updating/creating it.


class AddonBlock(AddonBlockBase, TimestampsModel):
    id: PyUUID
    addon_id: PyUUID
    behavior: Optional[AddonBehavior] = None


# Addon
class AddonBase(BaseModel):
    name: str
    description: Optional[str] = None
    user_id: str  # Assuming user_id is a string for now


class AddonCreate(AddonBase):
    blocks: List[AddonBlockCreate] = Field(default_factory=list)
    assets: List[AddonAssetCreate] = Field(default_factory=list)
    recipes: List[AddonRecipeCreate] = Field(default_factory=list)


class AddonUpdate(AddonBase):  # Used for updating top-level addon fields
    name: Optional[str] = None
    description: Optional[str] = None
    user_id: Optional[str] = None  # Or not allow user_id update? For now, keep it.
    # Sub-components (blocks, assets, recipes) will be handled by AddonDataUpload


class Addon(AddonBase, TimestampsModel):
    id: PyUUID


# Comprehensive model for GET response /api/v1/addons/{addon_id}
class AddonDetails(Addon):
    blocks: List[AddonBlock] = Field(default_factory=list)
    assets: List[AddonAsset] = Field(default_factory=list)
    recipes: List[AddonRecipe] = Field(default_factory=list)


# Comprehensive model for PUT request body /api/v1/addons/{addon_id}
# This model describes the full state of the addon to be persisted.
# Existing sub-items not present in these lists might be removed or handled as per upsert logic.
class AddonDataUpload(AddonBase):  # Reuses AddonBase for top-level fields
    name: str  # Make name required for an upload
    user_id: str  # Make user_id required for an upload

    blocks: List[AddonBlockCreate] = Field(default_factory=list)
    assets: List[AddonAssetCreate] = Field(default_factory=list)
    recipes: List[AddonRecipeCreate] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
    # Example for PUT data (client doesn't send IDs for new items)
    # {
    #   "name": "My Awesome Addon",
    #   "description": "The best addon ever",
    #   "user_id": "user123",
    #   "blocks": [
    #     {
    #       "identifier": "custom:magic_block",
    #       "properties": {"luminance": 15},
    #       "behavior": {"data": {"on_interact": "explode"}}
    #     }
    #   ],
    #   "assets": [{"type": "texture", "path": "textures/blocks/magic_block.png"}],
    #   "recipes": [{"data": {"ingredients": ["stick", "gold"], "output": "magic_wand"}}]
    # }


# Model for just returning the Addon ID and status, useful for create/update operations
class AddonResponse(BaseModel):
    id: PyUUID
    message: str

    model_config = ConfigDict(from_attributes=True)
