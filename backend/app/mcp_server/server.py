import json
from mcp.server.fastmcp import FastMCP
from app.db.session import AsyncSessionLocal
from app.mcp_server.schemas import (
    CreateEventInput, CreateTrackInput, CreateRoomInput,
    ScheduleSessionInput, DetectConflictsInput, ProvisionBoothInput,
    RollbackTransactionInput
)
from app.mcp_server.service import MCPService

# Initialize FastMCP Server
mcp = FastMCP("cadence-event-operations-mcp")

@mcp.tool(name="events_create_event", description="Initialize a new event entity with dates, format, and branding.")
async def create_event(data: CreateEventInput) -> str:
    async with AsyncSessionLocal() as db:
        res = await MCPService.create_event(db, data)
        return json.dumps(res)

@mcp.tool(name="tracks_create_track", description="Create a topical content track within an event.")
async def create_track(data: CreateTrackInput) -> str:
    async with AsyncSessionLocal() as db:
        res = await MCPService.create_track(db, data)
        return json.dumps(res)

@mcp.tool(name="rooms_create_room", description="Register a physical room or virtual broadcast room for an event.")
async def create_room(data: CreateRoomInput) -> str:
    async with AsyncSessionLocal() as db:
        res = await MCPService.create_room(db, data)
        return json.dumps(res)

@mcp.tool(name="sessions_detect_conflicts", description="Pre-flight check for overlapping rooms or double-booked speakers.")
async def detect_conflicts(data: DetectConflictsInput) -> str:
    async with AsyncSessionLocal() as db:
        res = await MCPService.detect_conflicts(db, data)
        return json.dumps(res)

@mcp.tool(name="sessions_schedule_session", description="Schedule a talk, panel, or workshop with room and speaker collision checks.")
async def schedule_session(data: ScheduleSessionInput) -> str:
    async with AsyncSessionLocal() as db:
        res = await MCPService.schedule_session(db, data)
        return json.dumps(res)

@mcp.tool(name="sessions_update_session_media", description="Live incident triage tool: swap session stream or backup video.")
async def update_session_media(session_id: str, asset_url: str) -> str:
    async with AsyncSessionLocal() as db:
        res = await MCPService.update_session_media(db, session_id, asset_url)
        return json.dumps(res)

@mcp.tool(name="booths_provision_booth", description="Provision sponsor exhibitor booth with 3D template and collateral.")
async def provision_booth(data: ProvisionBoothInput) -> str:
    async with AsyncSessionLocal() as db:
        res = await MCPService.provision_booth(db, data)
        return json.dumps(res)

@mcp.tool(name="audit_rollback_transaction", description="Saga pattern compensation tool: revert a previous MCP mutation.")
async def rollback_transaction(data: RollbackTransactionInput) -> str:
    async with AsyncSessionLocal() as db:
        res = await MCPService.rollback_transaction(db, data.tenant_id, data.transaction_id)
        return json.dumps(res)

@mcp.resource("event://{event_id}/manifest")
async def get_event_manifest_resource(event_id: str) -> str:
    async with AsyncSessionLocal() as db:
        res = await MCPService.get_event_manifest(db, event_id)
        return json.dumps(res, indent=2)
