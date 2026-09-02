import re
from datetime import datetime, timedelta
from typing import Dict, Any, List
from app.agents.state import ProvisioningState

async def parse_brief_node(state: ProvisioningState) -> Dict[str, Any]:
    """
    Parses unstructured text brief into structured domain definitions.
    Dynamically extracts tracks, rooms, sessions, and sponsor tiers.
    """
    text = state.get("raw_brief_text", "")
    now = datetime.utcnow()
    event_start = now + timedelta(days=14)
    event_end = event_start + timedelta(days=3)

    # 1. Title Extraction
    title = "Annual Tech & AI Conference"
    match_title = re.search(r"title:\s*([^\n\r]+)", text, re.IGNORECASE)
    if match_title:
        title = match_title.group(1).strip()
    slug = re.sub(r"[^a-z0-9-]", "", title.lower().replace(" ", "-"))

    # 2. Dynamic Tracks Extraction
    tracks: List[Dict[str, Any]] = []
    tracks_section = re.search(r"Tracks:\s*\n((?:\s*-[^\n]+\n*)+)", text, re.IGNORECASE)
    if tracks_section:
        for line in tracks_section.group(1).strip().split("\n"):
            m = re.search(r"-\s*([^(]+?)(?:\s*\(Color:\s*(#[0-9A-Fa-f]{6})\))?$", line.strip())
            if m:
                t_name = m.group(1).strip()
                t_color = m.group(2) or "#3B82F6"
                if t_name:
                    tracks.append({"name": t_name, "color_hex": t_color})

    # 3. Dynamic Rooms Extraction
    rooms: List[Dict[str, Any]] = []
    rooms_section = re.search(r"(?:Venues|Rooms|Venues & Broadcast Rooms):\s*\n((?:\s*-[^\n]+\n*)+)", text, re.IGNORECASE)
    if rooms_section:
        for line in rooms_section.group(1).strip().split("\n"):
            m = re.search(r"-\s*([^(]+?)(?:\s*\(Capacity:\s*(\d+)\))?$", line.strip())
            if m:
                r_name = m.group(1).strip()
                cap = int(m.group(2)) if m.group(2) else 250
                if r_name:
                    rooms.append({"name": r_name, "capacity": cap})

    # 4. Dynamic Sessions Extraction
    sessions: List[Dict[str, Any]] = []
    sessions_section = re.search(r"(?:Scheduled Agenda|Agenda|Sessions|Scheduled Agenda & Presentations):\s*\n((?:\s*-[^\n]+\n*)+)", text, re.IGNORECASE)
    if sessions_section:
        curr_session_time = event_start + timedelta(hours=9)
        for line in sessions_section.group(1).strip().split("\n"):
            m_title = re.search(r'-\s*"([^"]+)"', line)
            if not m_title:
                continue

            s_title = m_title.group(1).strip()
            m_room = re.search(r'\bin\s+(.+?)\s+on\s+', line)
            m_track = re.search(r'\bon\s+(.+?)\.\s*Speaker:', line)
            m_spk = re.search(r'Speaker:\s*([^(]+?)\s*(?:\(([^)]+)\))?', line)
            m_dur = re.search(r'Duration:\s*(\d+)\s*mins', line)

            s_room = m_room.group(1).strip() if m_room else (rooms[0]["name"] if rooms else "Main Hall")
            s_track = m_track.group(1).strip() if m_track else (tracks[0]["name"] if tracks else "General")
            s_spk_name = m_spk.group(1).strip() if m_spk else "Keynote Speaker"
            s_spk_email = m_spk.group(2).strip() if (m_spk and m_spk.group(2)) else "speaker@conf.org"
            s_dur = int(m_dur.group(1)) if m_dur else 45

            sessions.append({
                "title": s_title,
                "track_name": s_track,
                "room_name": s_room,
                "start_time": curr_session_time.isoformat(),
                "duration_minutes": s_dur,
                "speaker_name": s_spk_name,
                "speaker_email": s_spk_email
            })
            curr_session_time += timedelta(minutes=s_dur + 15)

    # 5. Dynamic Sponsors Extraction
    sponsors: List[Dict[str, Any]] = []
    sponsors_section = re.search(r"(?:Sponsors|Sponsors & Exhibitor Packages):\s*\n((?:\s*-[^\n]+\n*)+)", text, re.IGNORECASE)
    if sponsors_section:
        for line in sponsors_section.group(1).strip().split("\n"):
            m = re.search(r"-\s*([^(]+?)\s*\((TITLE|PLATINUM|GOLD|SILVER|BRONZE)", line.strip(), re.IGNORECASE)
            if m:
                sp_name = m.group(1).strip()
                sp_tier = m.group(2).upper()
                sponsors.append({"name": sp_name, "tier": sp_tier})

    # Fallbacks for synthetic/minimal inputs
    if not tracks:
        tracks = [
            {"name": "Main Stage", "color_hex": "#2563EB"},
            {"name": "Breakout Track", "color_hex": "#10B981"}
        ]
    if not rooms:
        rooms = [
            {"name": "Hall 1", "capacity": 500},
            {"name": "Room B", "capacity": 100}
        ]
    if not sessions:
        sessions = [
            {
                "title": "Opening Keynote: State of AI",
                "track_name": tracks[0]["name"],
                "room_name": rooms[0]["name"],
                "start_time": (event_start + timedelta(hours=9)).isoformat(),
                "duration_minutes": 60,
                "speaker_name": "Dr. Sarah Connor",
                "speaker_email": "sarah.connor@ai-summit.org"
            },
            {
                "title": "Deep Dive: Autonomous Agents",
                "track_name": tracks[1]["name"] if len(tracks) > 1 else tracks[0]["name"],
                "room_name": rooms[1]["name"] if len(rooms) > 1 else rooms[0]["name"],
                "start_time": (event_start + timedelta(hours=10, minutes=30)).isoformat(),
                "duration_minutes": 45,
                "speaker_name": "Alex Murphy",
                "speaker_email": "alex.murphy@omni-corp.com"
            }
        ]
    if not sponsors:
        sponsors = [
            {"name": "OmniCorp Systems", "tier": "PLATINUM"},
            {"name": "Cyberdyne Labs", "tier": "GOLD"}
        ]

    extracted = {
        "title": title,
        "slug": slug,
        "start_time": event_start.isoformat(),
        "end_time": event_end.isoformat(),
        "tracks": tracks,
        "rooms": rooms,
        "sessions": sessions,
        "sponsors": sponsors
    }

    return {
        "extracted_data": extracted,
        "planning_iteration": state.get("planning_iteration", 0) + 1
    }
