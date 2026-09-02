import json
import os
from typing import Dict, Any, Tuple

class RealWorldScheduleAdapter:
    @staticmethod
    def load_conference_source(source_filename: str) -> Dict[str, Any]:
        curr_dir = os.path.dirname(os.path.abspath(__file__))
        source_path = os.path.join(curr_dir, "..", "sources", source_filename)
        with open(source_path, "r", encoding="utf-8") as f:
            return json.load(f)

    @classmethod
    def generate_unstructured_brief_and_ground_truth(cls, source_filename: str) -> Tuple[str, Dict[str, Any]]:
        """
        Converts a standardized real conference schema into:
        1. A realistic unstructured event brief (text) simulating an organizer's CFP output.
        2. A structured ground truth object for quantitative precision/recall scoring.
        """
        data = cls.load_conference_source(source_filename)

        lines = [
            f"title: {data['title']}",
            f"format: {data['format']}",
            f"timezone: {data.get('timezone', 'UTC')}",
            "",
            "Tracks:"
        ]
        for t in data.get("tracks", []):
            lines.append(f"- {t['name']} (Color: {t.get('color_hex', '#3B82F6')})")

        lines.append("\nVenues & Broadcast Rooms:")
        for r in data.get("rooms", []):
            lines.append(f"- {r['name']} (Capacity: {r.get('capacity', 200)})")

        lines.append("\nScheduled Agenda & Presentations:")
        for s in data.get("sessions", []):
            spk = s.get("speaker", {})
            lines.append(
                f"- \"{s['title']}\" in {s['room']} on {s['track']}. "
                f"Speaker: {spk.get('name', 'TBA')} ({spk.get('email', 'speaker@conf.org')}), {spk.get('company', '')}. "
                f"Duration: {s.get('duration_minutes', 45)} mins."
            )

        lines.append("\nSponsors & Exhibitor Packages:")
        for sp in data.get("sponsors", []):
            lines.append(f"- {sp['name']} ({sp['tier']} Tier, Template: {sp.get('booth_template', 'standard_booth_v1')})")

        unstructured_brief = "\n".join(lines)

        ground_truth = {
            "title": data["title"],
            "tracks_count": len(data.get("tracks", [])),
            "rooms_count": len(data.get("rooms", [])),
            "sessions_count": len(data.get("sessions", [])),
            "sponsors_count": len(data.get("sponsors", [])),
            "tracks": [t["name"] for t in data.get("tracks", [])],
            "rooms": [r["name"] for r in data.get("rooms", [])],
            "sessions": [s["title"] for s in data.get("sessions", [])],
            "speakers": [s["speaker"]["name"] for s in data.get("sessions", []) if "speaker" in s]
        }

        return unstructured_brief, ground_truth
