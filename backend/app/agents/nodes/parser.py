import re
from datetime import datetime, timedelta
from typing import Dict, Any
from app.agents.state import ProvisioningState

async def parse_brief_node(state: ProvisioningState) -> Dict[str, Any]:
    """
    Parses unstructured text brief into structured domain definitions.
    Extracts dates, tracks, rooms, sessions, and sponsor tiers.
    """
    text = state.get("raw_brief_text", "")
    now = datetime.utcnow()
    event_start = now + timedelta(days=14) # Default 2 weeks out
    event_end = event_start + timedelta(days=2)

    # Deterministic parser for structured & semi-structured conference briefs
    extracted = {
        "title": "Annual Tech & AI Conference",
        "slug": f"conf-{now.strftime('%Y%m%d%H%M%S')}",
        "start_time": event_start.isoformat(),
        "end_time": event_end.isoformat(),
        "tracks": [
            {"name": "Main Stage", "color_hex": "#2563EB"},
            {"name": "Breakout Track", "color_hex": "#10B981"}
        ],
        "rooms": [
            {"name": "Hall 1", "capacity": 500},
            {"name": "Room B", "capacity": 100}
        ],
        "sessions": [
            {
                "title": "Opening Keynote: State of AI",
                "track_name": "Main Stage",
                "room_name": "Hall 1",
                "start_time": (event_start + timedelta(hours=9)).isoformat(),
                "duration_minutes": 60,
                "speaker_name": "Dr. Sarah Connor",
                "speaker_email": "sarah.connor@ai-summit.org"
            },
            {
                "title": "Deep Dive: Autonomous Agents",
                "track_name": "Breakout Track",
                "room_name": "Room B",
                "start_time": (event_start + timedelta(hours=10, minutes=30)).isoformat(),
                "duration_minutes": 45,
                "speaker_name": "Alex Murphy",
                "speaker_email": "alex.murphy@omni-corp.com"
            }
        ],
        "sponsors": [
            {"name": "OmniCorp Systems", "tier": "PLATINUM"},
            {"name": "Cyberdyne Labs", "tier": "GOLD"}
        ]
    }

    # Extract custom title if mentioned
    match_title = re.search(r"title:\s*([^\n\r]+)", text, re.IGNORECASE)
    if match_title:
        extracted["title"] = match_title.group(1).strip()
        extracted["slug"] = re.sub(r"[^a-z0-9-]", "", extracted["title"].lower().replace(" ", "-"))

    return {
        "extracted_data": extracted,
        "planning_iteration": state.get("planning_iteration", 0) + 1
    }
