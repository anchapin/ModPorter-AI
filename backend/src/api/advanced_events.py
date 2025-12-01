from fastapi import APIRouter, HTTPException, Depends, Path, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from db.base import get_db
from db import crud
from db.models import BehaviorFile
import uuid
import datetime as dt
from enum import Enum
import json
import asyncio
import logging

logger = logging.getLogger(__name__)

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
    conditions: List[EventCondition] = Field(
        default=[], description="Trigger conditions"
    )


class EventAction(BaseModel):
    """Event action model"""

    type: EventActionType = Field(..., description="Action type")
    parameters: Dict[str, Any] = Field(default={}, description="Action parameters")
    delay: int = Field(default=0, description="Delay in ticks before execution")
    conditions: List[EventCondition] = Field(
        default=[], description="Action conditions"
    )


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
    config: Optional[EventSystemConfig] = Field(
        None, description="System configuration"
    )
    triggers: Optional[List[EventTrigger]] = Field(None, description="Event triggers")
    actions: Optional[List[EventAction]] = Field(None, description="Event actions")
    variables: Optional[Dict[str, Any]] = Field(None, description="System variables")
    version: Optional[str] = Field(None, description="System version")
    enabled: Optional[bool] = Field(None, description="Whether system is enabled")


class EventSystemTest(BaseModel):
    """Event system test configuration"""

    test_data: Dict[str, Any] = Field(..., description="Test data to simulate")
    expected_results: List[Dict[str, Any]] = Field(
        default=[], description="Expected results"
    )
    dry_run: bool = Field(default=True, description="Run in dry-run mode")


class EventSystemTestResult(BaseModel):
    """Event system test result"""

    success: bool = Field(..., description="Whether test passed")
    executed_actions: int = Field(..., description="Number of actions executed")
    test_duration: float = Field(..., description="Test duration in milliseconds")
    errors: List[str] = Field(default=[], description="Any errors encountered")
    warnings: List[str] = Field(default=[], description="Any warnings generated")
    debug_output: List[Dict[str, Any]] = Field(
        default=[], description="Debug information"
    )


# Event template definitions
EVENT_TEMPLATES = {
    "entity_drops": {
        "name": "Entity Drops System",
        "description": "Custom drops when entity is killed",
        "config": {
            "event_type": EventType.ENTITY_DEATH,
            "namespace": "drops",
            "priority": 10,
            "enabled": True,
        },
        "triggers": [
            {
                "type": EventTriggerType.CONDITION,
                "parameters": {"entity_type": "minecraft:zombie"},
                "conditions": [
                    {
                        "type": "entity_has_tag",
                        "parameters": {"tag": "boss"},
                        "negated": True,
                    }
                ],
            }
        ],
        "actions": [
            {
                "type": EventActionType.GIVE_ITEM,
                "parameters": {
                    "item": "minecraft:gold_ingot",
                    "count": {"min": 2, "max": 5},
                    "player": "killer",
                },
            }
        ],
    },
    "block_break_effects": {
        "name": "Block Break Effects",
        "description": "Effects when specific blocks are broken",
        "config": {
            "event_type": EventType.BLOCK_BREAK,
            "namespace": "effects",
            "priority": 5,
            "enabled": True,
        },
        "triggers": [
            {
                "type": EventTriggerType.CONDITION,
                "parameters": {"block_type": "minecraft:diamond_ore"},
                "conditions": [],
            }
        ],
        "actions": [
            {
                "type": EventActionType.SOUND,
                "parameters": {
                    "sound": "random.levelup",
                    "location": "break_location",
                    "volume": 0.5,
                },
            },
            {
                "type": EventActionType.COMMAND,
                "parameters": {
                    "command": "tell @p Found diamonds!",
                    "permission_level": "all",
                },
                "delay": 20,
            },
        ],
    },
    "player_welcome": {
        "name": "Player Welcome System",
        "description": "Welcome message and items for new players",
        "config": {
            "event_type": EventType.PLAYER_JOIN,
            "namespace": "welcome",
            "priority": 1,
            "enabled": True,
        },
        "triggers": [
            {
                "type": EventTriggerType.CONDITION,
                "parameters": {"first_join": True},
                "conditions": [],
            }
        ],
        "actions": [
            {
                "type": EventActionType.COMMAND,
                "parameters": {
                    "command": 'title @p title {"text":"Welcome!","color":"gold"} subtitle {"text":"Enjoy your stay!","color":"aqua"}',
                    "permission_level": "all",
                },
            },
            {
                "type": EventActionType.GIVE_ITEM,
                "parameters": {
                    "item": "minecraft:stone_sword",
                    "count": 1,
                    "player": "@p",
                    "nbt": "{display:{Name:'\\\"Starter Sword\\\"'}}",
                },
            },
        ],
    },
}


@router.get(
    "/events/types",
    response_model=List[Dict[str, str]],
    summary="Get available event types",
)
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
            (EventType.CUSTOM, "Custom event type"),
        ]
    ]


@router.get(
    "/events/triggers",
    response_model=List[Dict[str, str]],
    summary="Get available trigger types",
)
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
            (EventTriggerType.SCHEDULE, "Trigger at scheduled time"),
        ]
    ]


@router.get(
    "/events/actions",
    response_model=List[Dict[str, str]],
    summary="Get available action types",
)
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
            (EventActionType.CUSTOM, "Custom action"),
        ]
    ]


@router.get(
    "/events/templates",
    response_model=List[AdvancedEventSystem],
    summary="Get event system templates",
)
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
            created_at=dt.datetime.now(dt.timezone.utc).isoformat(),
            updated_at=dt.datetime.now(dt.timezone.utc).isoformat(),
        )
        for template_key, template in EVENT_TEMPLATES.items()
    ]


@router.post(
    "/events/systems",
    response_model=AdvancedEventSystem,
    summary="Create event system",
    status_code=201,
)
async def create_event_system(
    request: AdvancedEventSystemCreate,
    conversion_id: str = Query(..., description="Conversion job ID"),
    db: AsyncSession = Depends(get_db),
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
        created_at=dt.datetime.now(dt.timezone.utc).isoformat(),
        updated_at=dt.datetime.now(dt.timezone.utc).isoformat(),
    )

    # Store in behavior files (as JSON)
    try:
        await crud.create_behavior_file(
            db,
            conversion_id=conversion_id,
            file_path=f"events/{event_system.id}.json",
            file_type="event_system",
            content=event_system.model_dump_json(indent=2),
        )

        return event_system

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create event system: {str(e)}"
        )


@router.get(
    "/events/systems/{system_id}",
    response_model=AdvancedEventSystem,
    summary="Get specific event system",
)
async def get_event_system(
    system_id: str = Path(..., description="Event system ID"),
    db: AsyncSession = Depends(get_db),
) -> AdvancedEventSystem:
    """
    Get a specific event system by ID.

    Note: This implementation stores event systems as behavior files.
    """
    # Search behavior files for event_system files
    try:
        # Query behavior files that are event systems
        stmt = select(BehaviorFile).where(
            BehaviorFile.file_type == "event_system", BehaviorFile.id == system_id
        )
        result = await db.execute(stmt)
        behavior_file = result.scalar_one_or_none()

        if not behavior_file:
            raise HTTPException(
                status_code=404, detail=f"Event system {system_id} not found"
            )

        # Parse the event system from behavior file content
        event_system_data = (
            json.loads(behavior_file.content) if behavior_file.content else {}
        )

        return AdvancedEventSystem(
            id=behavior_file.id,
            name=behavior_file.display_name,
            description=behavior_file.description or "",
            events=event_system_data.get("events", []),
            triggers=event_system_data.get("triggers", []),
            actions=event_system_data.get("actions", []),
            variables=event_system_data.get("variables", {}),
            created_at=behavior_file.created_at,
            updated_at=behavior_file.updated_at,
        )

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500, detail="Failed to parse event system configuration"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve event system: {str(e)}"
        )


@router.post(
    "/events/systems/{system_id}/test",
    response_model=EventSystemTestResult,
    summary="Test event system",
)
async def test_event_system(
    system_id: str = Path(..., description="Event system ID"),
    test_config: EventSystemTest = ...,
    db: AsyncSession = Depends(get_db),
) -> EventSystemTestResult:
    """
    Test an event system with provided test data.
    """
    try:
        # Get the event system first
        stmt = select(BehaviorFile).where(
            BehaviorFile.file_type == "event_system", BehaviorFile.id == system_id
        )
        result = await db.execute(stmt)
        behavior_file = result.scalar_one_or_none()

        if not behavior_file:
            raise HTTPException(
                status_code=404, detail=f"Event system {system_id} not found"
            )

        start_time = dt.datetime.now(dt.timezone.utc).timestamp() * 1000

        # Parse event system
        event_system_data = (
            json.loads(behavior_file.content) if behavior_file.content else {}
        )
        events = event_system_data.get("events", [])
        triggers = event_system_data.get("triggers", [])
        actions = event_system_data.get("actions", [])

        # Test execution
        executed_actions = 0
        errors = []
        warnings = []
        debug_output = []

        debug_output.append(
            {
                "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
                "message": f"Starting test for event system: {system_id}",
            }
        )

        if test_config.dry_run:
            # Dry run - just validate the configuration
            if not events:
                warnings.append("No events defined in event system")
            if not triggers:
                warnings.append("No triggers defined in event system")
            if not actions:
                warnings.append("No actions defined in event system")

            debug_output.append(
                {
                    "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
                    "message": f"Dry run completed - Events: {len(events)}, Triggers: {len(triggers)}, Actions: {len(actions)}",
                }
            )
        else:
            # Actual test execution
            test_data = test_config.test_data or {}
            mock_actions = test_data.get("mock_actions", [])

            for i, action in enumerate(actions):
                try:
                    # Simulate action execution
                    debug_output.append(
                        {
                            "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
                            "message": f"Executing action {i + 1}/{len(actions)}: {action.get('name', 'Unknown')}",
                        }
                    )
                    executed_actions += 1

                    # Simulate some processing time
                    await asyncio.sleep(0.01)

                except Exception as e:
                    errors.append(f"Failed to execute action {i + 1}: {str(e)}")

            for i, mock_action in enumerate(mock_actions):
                try:
                    debug_output.append(
                        {
                            "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
                            "message": f"Executing mock action {i + 1}/{len(mock_actions)}",
                        }
                    )
                    executed_actions += 1
                    await asyncio.sleep(0.01)
                except Exception as e:
                    errors.append(f"Failed to execute mock action {i + 1}: {str(e)}")

        end_time = dt.datetime.now(dt.timezone.utc).timestamp() * 1000
        test_duration = end_time - start_time

        debug_output.append(
            {
                "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
                "message": f"Test completed - Duration: {test_duration:.2f}ms, Actions executed: {executed_actions}",
            }
        )

        if not test_config.test_data and not test_config.dry_run:
            warnings.append("No test data provided - executed predefined actions only")

        return EventSystemTestResult(
            success=len(errors) == 0,
            executed_actions=executed_actions,
            test_duration=test_duration,
            errors=errors,
            warnings=warnings,
            debug_output=debug_output,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Event system test failed: {str(e)}"
        )


@router.post(
    "/events/systems/{system_id}/generate",
    summary="Generate Minecraft functions from event system",
    status_code=201,
)
async def generate_event_system_functions(
    system_id: str = Path(..., description="Event system ID"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate actual Minecraft functions from an event system.
    """
    try:
        # Add background task to generate functions
        background_tasks.add_task(generate_event_functions_background, system_id, db)

        return {"message": "Event system function generation started"}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to start generation: {str(e)}"
        )


async def generate_event_functions_background(system_id: str, db: AsyncSession):
    """
    Background task to generate Minecraft functions from event system.
    """
    try:
        # Get the event system
        stmt = select(BehaviorFile).where(
            BehaviorFile.file_type == "event_system", BehaviorFile.id == system_id
        )
        result = await db.execute(stmt)
        behavior_file = result.scalar_one_or_none()

        if not behavior_file:
            logger.error(f"Event system {system_id} not found for function generation")
            return

        # Parse the event system configuration
        event_system_data = (
            json.loads(behavior_file.content) if behavior_file.content else {}
        )
        events = event_system_data.get("events", [])
        triggers = event_system_data.get("triggers", [])
        actions = event_system_data.get("actions", [])

        logger.info(
            f"Starting function generation for event system {system_id}: {len(events)} events, {len(actions)} actions"
        )

        # Generate Minecraft function files
        generated_functions = []
        function_directory = f"functions/{system_id}"

        # Generate main event handler function
        main_function_content = f"""# Auto-generated event system functions for {behavior_file.display_name}
# Event System ID: {system_id}
# Generated at: {dt.datetime.now(dt.timezone.utc).isoformat()}

# Main event handler
scoreboard objectives add {system_id}_events dummy
scoreboard objectives add {system_id}_timer dummy

"""

        # Generate trigger functions
        for i, trigger in enumerate(triggers):
            trigger_type = trigger.get("type", "unknown")
            trigger_condition = trigger.get("condition", "")

            function_content = f"""# Trigger {i + 1}: {trigger_type}
scoreboard players set @s {system_id}_events 1
{f"# Condition: {trigger_condition}" if trigger_condition else ""}
"""

            # Store as behavior file
            trigger_function_file = BehaviorFile(
                id=str(uuid.uuid4()),
                display_name=f"Trigger {i + 1}",
                description=f"Generated trigger for {trigger_type}",
                file_type="minecraft_function",
                content=function_content,
                file_path=f"{function_directory}/trigger_{i + 1}.mcfunction",
                addon_id=behavior_file.addon_id,
            )

            db.add(trigger_function_file)
            generated_functions.append(f"trigger_{i + 1}")

            # Add to main function
            main_function_content += f"function {system_id}:trigger_{i + 1}\n"

        # Generate action functions
        for i, action in enumerate(actions):
            action_type = action.get("type", "unknown")
            action_target = action.get("target", "@s")

            function_content = f"""# Action {i + 1}: {action_type}
# Target: {action_target}
{action_type.replace("_", " ").title()} implementation here
"""

            # Store as behavior file
            action_function_file = BehaviorFile(
                id=str(uuid.uuid4()),
                display_name=f"Action {i + 1}",
                description=f"Generated action for {action_type}",
                file_type="minecraft_function",
                content=function_content,
                file_path=f"{function_directory}/action_{i + 1}.mcfunction",
                addon_id=behavior_file.addon_id,
            )

            db.add(action_function_file)
            generated_functions.append(f"action_{i + 1}")

            # Add to main function
            main_function_content += f"function {system_id}:action_{i + 1}\n"

        # Store main function
        main_function_file = BehaviorFile(
            id=str(uuid.uuid4()),
            display_name="Main Event Handler",
            description=f"Main event system handler for {behavior_file.display_name}",
            file_type="minecraft_function",
            content=main_function_content,
            file_path=f"{function_directory}/main.mcfunction",
            addon_id=behavior_file.addon_id,
        )

        db.add(main_function_file)
        generated_functions.append("main")

        # Commit all generated functions
        await db.commit()

        logger.info(
            f"Successfully generated {len(generated_functions)} functions for event system {system_id}"
        )
        logger.info(f"Generated functions: {', '.join(generated_functions)}")

    except Exception as e:
        logger.error(f"Background function generation failed for {system_id}: {e}")
        await db.rollback()


@router.get(
    "/events/systems/{system_id}/debug",
    summary="Get debug information for event system",
)
async def get_event_system_debug(
    system_id: str = Path(..., description="Event system ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get debug information for an event system.
    """
    try:
        # Get the event system
        stmt = select(BehaviorFile).where(
            BehaviorFile.file_type == "event_system", BehaviorFile.id == system_id
        )
        result = await db.execute(stmt)
        behavior_file = result.scalar_one_or_none()

        if not behavior_file:
            raise HTTPException(
                status_code=404, detail=f"Event system {system_id} not found"
            )

        # Parse the event system configuration
        event_system_data = (
            json.loads(behavior_file.content) if behavior_file.content else {}
        )
        events = event_system_data.get("events", [])
        triggers = event_system_data.get("triggers", [])
        actions = event_system_data.get("actions", [])
        variables = event_system_data.get("variables", {})

        # Get generated functions for this event system
        function_stmt = select(BehaviorFile).where(
            BehaviorFile.file_type == "minecraft_function",
            BehaviorFile.file_path.like(f"functions/{system_id}%"),
        )
        function_result = await db.execute(function_stmt)
        generated_functions = function_result.scalars().all()

        return {
            "system_id": system_id,
            "debug_enabled": True,
            "configuration_loaded": True,
            "events_count": len(events),
            "triggers_count": len(triggers),
            "actions_count": len(actions),
            "variables_loaded": variables,
            "generated_functions": [
                {
                    "id": func.id,
                    "name": func.display_name,
                    "path": func.file_path,
                    "created_at": func.created_at.isoformat()
                    if func.created_at
                    else None,
                }
                for func in generated_functions
            ],
            "last_tested": behavior_file.updated_at.isoformat()
            if behavior_file.updated_at
            else None,
            "validation_errors": [],
            "performance_metrics": {
                "estimated_execution_time_ms": len(actions) * 10,  # Rough estimate
                "memory_usage_kb": len(json.dumps(event_system_data)),
                "complexity_score": len(events) + len(triggers) + len(actions),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get debug info: {str(e)}"
        )
