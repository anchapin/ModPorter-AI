"""
Version Information API endpoints.
"""

from fastapi import APIRouter, status
from pydantic import BaseModel

from services.minecraft_version_tracker import version_tracker
from services.minecraft_release_monitor import release_monitor

router = APIRouter(prefix="/info", tags=["info"])


class VersionInfo(BaseModel):
    supported_java_range: str
    java_min_version: str
    java_max_version: str
    bedrock_target_version: str
    display_string: str
    last_updated: str
    update_source: str
    notes: str | None


class ReleaseMonitorStatus(BaseModel):
    last_java_check: str | None
    last_bedrock_check: str | None
    current_java_version: str
    current_bedrock_version: str
    check_interval_hours: int


@router.get("/versions", response_model=VersionInfo, status_code=status.HTTP_200_OK)
async def get_version_info():
    """
    Get current Minecraft version support information.

    Returns the supported Java Edition version range and Bedrock Edition target version
    for PortKit conversions. Display format: "Java 1.18-1.21 → Bedrock 1.21.0"
    """
    info = version_tracker.get_version_info()
    return VersionInfo(
        supported_java_range=info["java_range"],
        java_min_version=info["java_min"],
        java_max_version=info["java_max"],
        bedrock_target_version=info["bedrock_target"],
        display_string=info["display_string"],
        last_updated=info["last_updated"],
        update_source=info["update_source"],
        notes=info["notes"]
    )


@router.get("/versions/monitor-status", response_model=ReleaseMonitorStatus, status_code=status.HTTP_200_OK)
async def get_monitor_status():
    """
    Get the status of the Minecraft release monitor.

    Returns last check timestamps and current tracked versions.
    """
    return ReleaseMonitorStatus(**release_monitor.get_status())


@router.post("/versions/check-updates", status_code=status.HTTP_200_OK)
async def check_for_updates():
    """
    Manually trigger a check for new Minecraft releases.

    Returns update availability status for Java and Bedrock editions.
    """
    result = await release_monitor.check_for_updates()
    return result