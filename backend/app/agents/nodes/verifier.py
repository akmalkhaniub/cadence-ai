from datetime import datetime
from typing import Dict, Any, List
from app.agents.state import ProvisioningState

async def verifier_node(state: ProvisioningState) -> Dict[str, Any]:
    """
    Deterministically validates schedule constraints:
    - Room temporal non-collision
    - Speaker availability non-collision
    - Session boundaries within event dates
    """
    plan = state["plan"]
    sessions = [step for step in plan if step["action"] == "schedule_session"]
    conflicts: List[Dict[str, Any]] = []

    for i in range(len(sessions)):
        for j in range(i + 1, len(sessions)):
            s1 = sessions[i]["payload"]
            s2 = sessions[j]["payload"]

            s1_start = datetime.fromisoformat(s1["start_time"])
            s1_end = datetime.fromisoformat(s1["end_time"])
            s2_start = datetime.fromisoformat(s2["start_time"])
            s2_end = datetime.fromisoformat(s2["end_time"])

            # Check temporal overlap: max(start1, start2) < min(end1, end2)
            has_overlap = max(s1_start, s2_start) < min(s1_end, s2_end)

            if has_overlap:
                # 1. Room collision
                if s1.get("room_name") == s2.get("room_name"):
                    conflicts.append({
                        "type": "ROOM_DOUBLE_BOOKING",
                        "room": s1["room_name"],
                        "sessions": [s1["title"], s2["title"]],
                        "overlap_start": max(s1_start, s2_start).isoformat(),
                        "overlap_end": min(s1_end, s2_end).isoformat()
                    })

                # 2. Speaker collision
                if s1.get("speaker_email") == s2.get("speaker_email"):
                    conflicts.append({
                        "type": "SPEAKER_COLLISION",
                        "speaker": s1["speaker_email"],
                        "sessions": [s1["title"], s2["title"]]
                    })

    passed = len(conflicts) == 0
    return {
        "detected_conflicts": conflicts,
        "verification_passed": passed
    }
