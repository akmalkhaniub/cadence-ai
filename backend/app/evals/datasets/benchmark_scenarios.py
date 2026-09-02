from typing import List, Dict, Any

BENCHMARK_SCENARIOS: List[Dict[str, Any]] = [
    {
        "id": "BENCH-STD-01",
        "name": "3-Day Global Multi-Track Virtual Summit",
        "category": "STANDARD",
        "input_brief": "title: Global AI Summit 2026\nTracks: Main Stage, Breakout Track\nRooms: Hall 1, Room B\nKeynote at 09:00 AM on Main Stage by Dr. Sarah Connor\nBreakout at 10:30 AM by Alex Murphy\nSponsors: OmniCorp (Platinum), Cyberdyne (Gold)",
        "expected_sessions_count": 2,
        "expected_tracks_count": 2,
        "has_inherent_conflict": False
    },
    {
        "id": "BENCH-STD-02",
        "name": "Hybrid Dev Conference + Hackathon",
        "category": "STANDARD",
        "input_brief": "title: Hackathon & DevFest 2026\nTracks: Hackathon Arena, Workshops\nRooms: Stage 1, Lab 2\nWorkshop at 10:00 AM by Lead Hacker\nKeynote at 11:30 AM by Elena Rostova\nSponsors: CloudScale Systems (Platinum)",
        "expected_sessions_count": 2,
        "expected_tracks_count": 2,
        "has_inherent_conflict": False
    },
    {
        "id": "BENCH-ADV-02",
        "name": "Speaker Double-Booking Conflict in Brief",
        "category": "ADVERSARIAL",
        "input_brief": "title: Conflicting Summit 2026\nTracks: Track 1, Track 2\nRooms: Room A, Room B\nTalk 1 at 10:00 AM by Dr. Samantha Reed in Room A\nTalk 2 at 10:15 AM by Dr. Samantha Reed in Room B",
        "expected_sessions_count": 2,
        "has_inherent_conflict": True,
        "conflict_type": "SPEAKER_COLLISION"
    },
    {
        "id": "BENCH-CHA-01",
        "name": "Mid-Batch Failure & Saga Compensating Rollback",
        "category": "CHAOS",
        "simulate_rollback": True,
        "expected_rollback_parity": 1.0
    },
    {
        "id": "BENCH-LIV-01",
        "name": "Live Speaker Absence 15m Prior to Showtime",
        "category": "LIVE_OPS",
        "incident_type": "SPEAKER_NO_SHOW",
        "max_triage_latency_seconds": 2.5
    }
]
