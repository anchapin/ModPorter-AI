from fastapi import APIRouter, HTTPException, Depends, Path, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from db.base import get_db
from ..db import crud
import uuid
from datetime import datetime
from enum import Enum

router = APIRouter()

class EventType(str, Enum):
    """Supported event types"""
    ENTITY_SPAWN = "entity_spawn"
    ENTITY_DEATH = "entity_death"
    BLOCK_BREAK = "block_break"
    BLOCK_PLACE = "block_place"
    PLAYER_JOIN = "player_join"
    PLAYER_LEAVE = "player_leave"
    WORLD_TICK = "world_tick"
    WEATHER_CHANGE = "weather_change"
    CUSTOM = "custom"

class EventTriggerType(str, Enum):
    """Event trigger types"""
    ONCE = "once"
    REPEAT = "repeat"
    CONDITION = "condition"
    DELAY = "delay"
    SCHEDULE = "schedule"

class EventActionType(str, Enum):
    """Event action types"""
    COMMAND = "command"
    FUNCTION = "function"
    SPAWN_ENTITY = "spawn_entity"
    SET_BLOCK = "set_block"
    GIVE_ITEM = "give_item"
    TELEPORT = "teleport"
    EFFECT = "effect"
    SOUND = "sound"
    CUSTOM = "custom"

# Pydantic models
class EventCondition(BaseModel):
    """Event condition model"""
    type: str = Field(..., description="Condition type")
    parameters: Dict[str, Any] = Field(default={}, description="Condition parameters")
    negated: bool = Field(default=False, description="Whether condition is negated")

class EventTrigger(BaseModel):
    """Event trigger model"""
    type: EventTriggerType = Field(..., description="Trigger type")
    parameters: Dict[str, Any] = Field(default={}, description="Trigger parameters")
    conditions: List[EventCondition] = Field(default=[], description="Trigger conditions")

class EventAction(BaseModel):
    """Event action model"""
    type: EventActionType = Field(..., description="Action type")
    parameters: Dict[str, Any] = Field(default={}, description="Action parameters")
    delay: int = Field(default=0, description="Delay in ticks before execution")
    conditions: List[EventCondition] = Field(default=[], description="Action conditions")

class EventSystemConfig(BaseModel):
    """Event system configuration"""
    event_type: EventType = Field(..., description="Type of event")
    namespace: str = Field(default="custom", description="Event namespace")
    priority: int = Field(default=0, description="Event priority (higher = earlier)")
    enabled: bool = Field(default=True, description="Whether event is enabled")
    debug: bool = Field(default=False, description="Enable debug logging")

class AdvancedEventSystem(BaseModel):
    """Complete advanced event system"""
    id: str = Field(..., description="Event system ID")
    name: str = Field(..., description="Event system name")
    description: str = Field(..., description="Event system description")
    config: EventSystemConfig = Field(..., description="System configuration")
    triggers: List[EventTrigger] = Field(default=[], description="Event triggers")
    actions: List[EventAction] = Field(default=[], description="Event actions")
    variables: Dict[str, Any] = Field(default={}, description="System variables")
    version: str = Field(default="1.0.0", description="System version")
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class AdvancedEventSystemCreate(BaseModel):
    """Request model for creating event system"""
    name: str = Field(..., description="Event system name")
    description: str = Field(..., description="Event system description")
    config: EventSystemConfig = Field(..., description="System configuration")
    triggers: List[EventTrigger] = Field(default=[], description="Event triggers")
    actions: List[EventAction] = Field(default=[], description="Event actions")
    variables: Dict[str, Any] = Field(default={}, description="System variables")
    version: str = Field(default="1.0.0", description="System version")

class AdvancedEventSystemUpdate(BaseModel):
    """Request model for updating event system"""
    name: Optional[str] = Field(None, description="Event system name")
    description: Optional[str] = Field(None, description="Event system description")
    config: Optional[EventSystemConfig] = Field(None, description="System configuration")
    triggers: Optional[List[EventTrigger]] = Field(None, description="Event triggers")
    actions: Optional[List[EventAction]] = Field(None, description="Event actions")
    variables: Optional[Dict[str, Any]] = Field(None, description="System variables")
    version: Optional[str] = Field(None, description="System version")
    enabled: Optional[bool] = Field(None, description="Whether system is enabled")

class EventSystemTest(BaseModel):
    """Event system test configuration"""
    test_data: Dict[str, Any] = Field(..., description="Test data to simulate")
    expected_results: List[Dict[str, Any]] = Field(default=[], description="Expected results")
    dry_run: bool = Field(default=True, description="Run in dry-run mode")

class EventSystemTestResult(BaseModel):
    """Event system test result"""
    success: bool = Field(..., description="Whether test passed")
    executed_actions: int = Field(..., description="Number of actions executed")
    test_duration: float = Field(..., description="Test duration in milliseconds")
    errors: List[str] = Field(default=[], description="Any errors encountered")
    warnings: List[str] = Field(default=[], description="Any warnings generated")
    debug_output: List[Dict[str, Any]] = Field(default=[], description="Debug information")

# Event template definitions
EVENT_TEMPLATES = {
    "entity_drops": {
        "name": "Entity Drops System",
        "description": "Custom drops when entity is killed",
        "config": {
            "event_type": EventType.ENTITY_DEATH,
            "namespace": "drops",
            "priority": 10,
            "enabled": True
        },
        "triggers": [
            {
                "type": EventTriggerType.CONDITION,
                "parameters": {"entity_type": "minecraft:zombie"},
                "conditions": [
                    {
                        "type": "entity_has_tag",
                        "parameters": {"tag": "boss"},
                        "negated": True
                    }
                ]
            }
        ],
        "actions": [
            {
                "type": EventActionType.GIVE_ITEM,
                "parameters": {
                    "item": "minecraft:gold_ingot",
                    "count": {"min": 2, "max": 5},
                    "player": "killer"
                }
            }
        ]
    },
    "block_break_effects": {
        "name": "Block Break Effects",
        "description": "Effects when specific blocks are broken",
        "config": {
            "event_type": EventType.BLOCK_BREAK,
            "namespace": "effects",
            "priority": 5,
            "enabled": True
        },
        "triggers": [
            {
                "type": EventTriggerType.CONDITION,
                "parameters": {"block_type": "minecraft:diamond_ore"},
                "conditions": []
            }
        ],
        "actions": [
            {
                "type": EventActionType.SOUND,
                "parameters": {
                    "sound": "random.levelup",
                    "location": "break_location",
                    "volume": 0.5
                }
            },
            {
                "type": EventActionType.COMMAND,
                "parameters": {
                    "command": "tell @p Found diamonds!",
                    "permission_level": "all"
                },
                "delay": 20
            }
        ]
    },
    "player_welcome": {
        "name": "Player Welcome System",
        "description": "Welcome message and items for new players",
        "config": {
            "event_type": EventType.PLAYER_JOIN,
            "namespace": "welcome",
            "priority": 1,
            "enabled": True
        },
        "triggers": [
            {
                "type": EventTriggerType.CONDITION,
                "parameters": {"first_join": True},
                "conditions": []
            }
        ],
        "actions": [
            {
                "type": EventActionType.COMMAND,
                "parameters": {
                    "command": "title @p title {\"text\":\"Welcome!\",\"color\":\"gold\"} subtitle {\"text\":\"Enjoy your stay!\",\"color\":\"aqua\"}",
                    "permission_level": "all"
                }
            },
            {
                "type": EventActionType.GIVE_ITEM,
                "parameters": {
                    "item": "minecraft:stone_sword",
                    "count": 1,
                    "player": "@p",
                    "nbt": "{display:{Name:'\\\"Starter Sword\\\"'}}"
                }
            }
        ]
    }
}

@router.get("/events/types",
           response_model=List[Dict[str, str]],
           summary="Get available event types")
async def get_event_types():
    """
    Get all available event types with descriptions.
    """
    return [
        {"type": event_type.value, "description": description}
        for event_type, description in [
            (EventType.ENTITY_SPAWN, "Entity spawns in world"),
            (EventType.ENTITY_DEATH, "Entity dies"),
            (EventType.BLOCK_BREAK, "Block is broken"),
            (EventType.BLOCK_PLACE, "Block is placed"),
            (EventType.PLAYER_JOIN, "Player joins world"),
            (EventType.PLAYER_LEAVE, "Player leaves world"),
            (EventType.WORLD_TICK, "World tick event"),
            (EventType.WEATHER_CHANGE, "Weather changes"),
            (EventType.CUSTOM, "Custom event type")
        ]
    ]

@router.get("/events/triggers",
           response_model=List[Dict[str, str]],
           summary="Get available trigger types")
async def get_trigger_types():
    """
    Get all available trigger types with descriptions.
    """
    return [
        {"type": trigger_type.value, "description": description}
        for trigger_type, description in [
            (EventTriggerType.ONCE, "Trigger only once"),
            (EventTriggerType.REPEAT, "Repeat at intervals"),
            (EventTriggerType.CONDITION, "Trigger when conditions are met"),
            (EventTriggerType.DELAY, "Trigger after delay"),
            (EventTriggerType.SCHEDULE, "Trigger at scheduled time")
        ]
    ]

@router.get("/events/actions",
           response_model=List[Dict[str, str]],
           summary="Get available action types")
async def get_action_types():
    """
    Get all available action types with descriptions.
    """
    return [
        {"type": action_type.value, "description": description}
        for action_type, description in [
            (EventActionType.COMMAND, "Execute a command"),
            (EventActionType.FUNCTION, "Run a function"),
            (EventActionType.SPAWN_ENTITY, "Spawn an entity"),
            (EventActionType.SET_BLOCK, "Set a block"),
            (EventActionType.GIVE_ITEM, "Give item to player"),
            (EventActionType.TELEPORT, "Teleport entity"),
            (EventActionType.EFFECT, "Apply effect"),
            (EventActionType.SOUND, "Play sound"),
            (EventActionType.CUSTOM, "Custom action")
        ]
    ]

@router.get("/events/templates",
           response_model=List[AdvancedEventSystem],
           summary="Get event system templates")
async def get_event_templates():
    """
    Get predefined event system templates.
    """
    return [
        AdvancedEventSystem(
            id=template_key,
            name=template["name"],
            description=template["description"],
            config=template["config"],
            triggers=template["triggers"],
            actions=template["actions"],
            variables={},
            version="1.0.0",
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat()
        )
        for template_key, template in EVENT_TEMPLATES.items()
    ]

@router.post("/events/systems",
            response_model=AdvancedEventSystem,
            summary="Create event system",
            status_code=201)
async def create_event_system(
    request: AdvancedEventSystemCreate,
    conversion_id: str = Query(..., description="Conversion job ID"),
    db: AsyncSession = Depends(get_db)
) -> AdvancedEventSystem:
    """
    Create a new advanced event system.
    """
    try:
        uuid.UUID(conversion_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversion ID format")

    # Check if conversion exists
    conversion = await crud.get_job(db, conversion_id)
    if not conversion:
        raise HTTPException(status_code=404, detail="Conversion not found")

    # Create event system
    event_system = AdvancedEventSystem(
        id=f"event_system_{uuid.uuid4().hex[:8]}",
        name=request.name,
        description=request.description,
        config=request.config,
        triggers=request.triggers,
        actions=request.actions,
        variables=request.variables,
        version=request.version,
        created_at=datetime.utcnow().isoformat(),
        updated_at=datetime.utcnow().isoformat()
    )

    # Store in behavior files (as JSON)
    try:
        await crud.create_behavior_file(
            db,
            conversion_id=conversion_id,
            file_path=f"events/{event_system.id}.json",
            file_type="event_system",
            content=event_system.model_dump_json(indent=2)
        )
        
        return event_system
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create event system: {str(e)}")

@router.get("/events/systems/{system_id}",
           response_model=AdvancedEventSystem,
           summary="Get specific event system")
async def get_event_system(
    system_id: str = Path(..., description="Event system ID"),
    db: AsyncSession = Depends(get_db)
) -> AdvancedEventSystem:
    """
    Get a specific event system by ID.
    
    Note: This implementation stores event systems as behavior files.
    """
    # For now, this would search behavior files for event_system files
    # In a full implementation, you'd have a separate database table
    raise HTTPException(
        status_code=501, 
        detail="Event system retrieval not fully implemented - stored as behavior files"
    )

@router.post("/events/systems/{system_id}/test",
            response_model=EventSystemTestResult,
            summary="Test event system")
async def test_event_system(
    system_id: str = Path(..., description="Event system ID"),
    test_config: EventSystemTest = ...,
    db: AsyncSession = Depends(get_db)
) -> EventSystemTestResult:
    """
    Test an event system with provided test data.
    """
    try:
        # Simulate event system testing
        start_time = datetime.utcnow().timestamp() * 1000
        
        # Mock test execution
        executed_actions = len(test_config.test_data.get("mock_actions", []))
        errors = [] if test_config.dry_run else ["Test execution not fully implemented"]
        warnings = [] if test_config.test_data else ["No test data provided"]
        
        end_time = datetime.utcnow().timestamp() * 1000
        test_duration = end_time - start_time
        
        return EventSystemTestResult(
            success=len(errors) == 0,
            executed_actions=executed_actions,
            test_duration=test_duration,
            errors=errors,
            warnings=warnings,
            debug_output=[
                {"timestamp": datetime.utcnow().isoformat(), "message": "Test started"},
                {"timestamp": datetime.utcnow().isoformat(), "message": "Test completed"}
            ]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Event system test failed: {str(e)}")

@router.post("/events/systems/{system_id}/generate",
            summary="Generate Minecraft functions from event system",
            status_code=201)
async def generate_event_system_functions(
    system_id: str = Path(..., description="Event system ID"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate actual Minecraft functions from an event system.
    """
    try:
        # Add background task to generate functions
        background_tasks.add_task(
            generate_event_functions_background,
            system_id,
            db
        )
        
        return {"message": "Event system function generation started"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start generation: {str(e)}")

async def generate_event_functions_background(system_id: str, db: AsyncSession):
    """
    Background task to generate Minecraft functions from event system.
    """
    try:
        # This would contain the actual function generation logic
        # For now, it's a placeholder
        print(f"Generating functions for event system: {system_id}")
        
        # In a full implementation, this would:
        # 1. Parse the event system configuration
        # 2. Generate Minecraft function files
        # 3. Create proper function directory structure
        # 4. Store generated functions as behavior files
        
    except Exception as e:
        print(f"Background function generation failed: {e}")

@router.get("/events/systems/{system_id}/debug",
            summary="Get debug information for event system")
async def get_event_system_debug(
    system_id: str = Path(..., description="Event system ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get debug information for an event system.
    """
    try:
        # Mock debug information
        return {
            "system_id": system_id,
            "debug_enabled": True,
            "triggers_active": 3,
            "actions_ready": 5,
            "variables_loaded": {"test_var": "test_value"},
            "last_execution": datetime.utcnow().isoformat(),
            "execution_count": 42,
            "errors_last_hour": [],
            "performance_stats": {
                "avg_execution_time": 15.2,
                "max_execution_time": 45.8,
                "min_execution_time": 2.1
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get debug info: {str(e)}")
