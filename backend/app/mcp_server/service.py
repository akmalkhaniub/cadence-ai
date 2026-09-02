import uuid
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import (
    Event, Track, Room, Session, SessionSpeaker, Speaker, Sponsor, Booth, 
    AgentTransactionJournal, EventStatus, SessionStatus, SpeakerRole
)
from app.mcp_server.schemas import (
    CreateEventInput, CreateTrackInput, CreateRoomInput, 
    ScheduleSessionInput, DetectConflictsInput, ProvisionBoothInput
)

class MCPService:
    @staticmethod
    async def get_cached_idempotent_result(db: AsyncSession, idempotency_key: str) -> Optional[Dict[str, Any]]:
        stmt = select(AgentTransactionJournal).where(AgentTransactionJournal.idempotency_key == idempotency_key)
        res = await db.execute(stmt)
        record = res.scalar_one_or_none()
        if record:
            return {
                "idempotent_replay": True,
                "transaction_id": record.id,
                "target_id": record.target_id,
                "operation": record.operation,
                "forward_payload": record.forward_payload
            }
        return None

    @classmethod
    async def create_event(cls, db: AsyncSession, data: CreateEventInput) -> Dict[str, Any]:
        cached = await cls.get_cached_idempotent_result(db, data.idempotency_key)
        if cached:
            return cached

        event = Event(
            tenant_id=data.tenant_id,
            title=data.title,
            slug=data.slug,
            description=data.description,
            format=data.format,
            status=EventStatus.DRAFT,
            timezone=data.timezone,
            start_time=data.start_time,
            end_time=data.end_time,
            branding=data.branding
        )
        db.add(event)
        await db.flush()

        journal = AgentTransactionJournal(
            tenant_id=data.tenant_id,
            agent_run_id="mcp_direct",
            idempotency_key=data.idempotency_key,
            tool_name="events.create_event",
            target_table="events",
            target_id=event.id,
            operation="INSERT",
            forward_payload={"event_id": event.id, "title": event.title, "slug": event.slug},
            compensating_patch={"tool_name": "events.delete_event", "event_id": event.id}
        )
        db.add(journal)
        await db.commit()

        return {
            "status": "SUCCESS",
            "event_id": event.id,
            "transaction_id": journal.id
        }

    @classmethod
    async def create_track(cls, db: AsyncSession, data: CreateTrackInput) -> Dict[str, Any]:
        cached = await cls.get_cached_idempotent_result(db, data.idempotency_key)
        if cached:
            return cached

        track = Track(
            tenant_id=data.tenant_id,
            event_id=data.event_id,
            name=data.name,
            color_hex=data.color_hex,
            display_order=data.display_order
        )
        db.add(track)
        await db.flush()

        journal = AgentTransactionJournal(
            tenant_id=data.tenant_id,
            agent_run_id="mcp_direct",
            idempotency_key=data.idempotency_key,
            tool_name="tracks.create_track",
            target_table="tracks",
            target_id=track.id,
            operation="INSERT",
            forward_payload={"track_id": track.id, "name": track.name},
            compensating_patch={"tool_name": "tracks.delete_track", "track_id": track.id}
        )
        db.add(journal)
        await db.commit()

        return {
            "status": "SUCCESS",
            "track_id": track.id,
            "transaction_id": journal.id
        }

    @classmethod
    async def create_room(cls, db: AsyncSession, data: CreateRoomInput) -> Dict[str, Any]:
        cached = await cls.get_cached_idempotent_result(db, data.idempotency_key)
        if cached:
            return cached

        room = Room(
            tenant_id=data.tenant_id,
            event_id=data.event_id,
            name=data.name,
            physical_capacity=data.physical_capacity,
            is_virtual=data.is_virtual,
            stream_provider=data.stream_provider,
            primary_stream_url=data.primary_stream_url,
            backup_stream_url=data.backup_stream_url
        )
        db.add(room)
        await db.flush()

        journal = AgentTransactionJournal(
            tenant_id=data.tenant_id,
            agent_run_id="mcp_direct",
            idempotency_key=data.idempotency_key,
            tool_name="rooms.create_room",
            target_table="rooms",
            target_id=room.id,
            operation="INSERT",
            forward_payload={"room_id": room.id, "name": room.name},
            compensating_patch={"tool_name": "rooms.delete_room", "room_id": room.id}
        )
        db.add(journal)
        await db.commit()

        return {
            "status": "SUCCESS",
            "room_id": room.id,
            "transaction_id": journal.id
        }

    @classmethod
    async def detect_conflicts(cls, db: AsyncSession, data: DetectConflictsInput) -> Dict[str, Any]:
        """Pre-flight conflict simulation tool."""
        conflicts = []

        # 1. Room collision check
        if data.room_id:
            query = select(Session).where(
                Session.event_id == data.event_id,
                Session.room_id == data.room_id,
                Session.status.notin_([SessionStatus.CANCELLED, SessionStatus.DRAFT]),
                or_(
                    and_(Session.start_time <= data.start_time, Session.end_time > data.start_time),
                    and_(Session.start_time < data.end_time, Session.end_time >= data.end_time),
                    and_(Session.start_time >= data.start_time, Session.end_time <= data.end_time)
                )
            )
            if data.exclude_session_id:
                query = query.where(Session.id != data.exclude_session_id)
            
            res = await db.execute(query)
            colliding_sessions = res.scalars().all()
            for s in colliding_sessions:
                conflicts.append({
                    "conflict_type": "ROOM_DOUBLE_BOOKING",
                    "room_id": data.room_id,
                    "conflicting_session_id": s.id,
                    "conflicting_title": s.title,
                    "start_time": s.start_time.isoformat(),
                    "end_time": s.end_time.isoformat()
                })

        # 2. Speaker collision check
        if data.speaker_ids:
            speaker_query = (
                select(Session)
                .join(SessionSpeaker, Session.id == SessionSpeaker.session_id)
                .where(
                    Session.event_id == data.event_id,
                    SessionSpeaker.speaker_id.in_(data.speaker_ids),
                    Session.status.notin_([SessionStatus.CANCELLED, SessionStatus.DRAFT]),
                    or_(
                        and_(Session.start_time <= data.start_time, Session.end_time > data.start_time),
                        and_(Session.start_time < data.end_time, Session.end_time >= data.end_time),
                        and_(Session.start_time >= data.start_time, Session.end_time <= data.end_time)
                    )
                )
            )
            if data.exclude_session_id:
                speaker_query = speaker_query.where(Session.id != data.exclude_session_id)

            spk_res = await db.execute(speaker_query)
            spk_colliding = spk_res.scalars().all()
            for s in spk_colliding:
                conflicts.append({
                    "conflict_type": "SPEAKER_COLLISION",
                    "conflicting_session_id": s.id,
                    "conflicting_title": s.title,
                    "start_time": s.start_time.isoformat(),
                    "end_time": s.end_time.isoformat()
                })

        return {
            "has_conflict": len(conflicts) > 0,
            "conflicts": conflicts
        }

    @classmethod
    async def schedule_session(cls, db: AsyncSession, data: ScheduleSessionInput) -> Dict[str, Any]:
        cached = await cls.get_cached_idempotent_result(db, data.idempotency_key)
        if cached:
            return cached

        # Check conflicts first
        conflict_check = await cls.detect_conflicts(
            db, 
            DetectConflictsInput(
                event_id=data.event_id,
                room_id=data.room_id,
                start_time=data.start_time,
                end_time=data.end_time,
                speaker_ids=data.speaker_ids
            )
        )
        if conflict_check["has_conflict"]:
            return {
                "status": "ERROR_CONFLICT",
                "message": "Cannot schedule session due to resource collisions.",
                "conflicts": conflict_check["conflicts"]
            }

        duration_minutes = int((data.end_time - data.start_time).total_seconds() / 60)
        session_obj = Session(
            tenant_id=data.tenant_id,
            event_id=data.event_id,
            track_id=data.track_id,
            room_id=data.room_id,
            title=data.title,
            abstract=data.abstract,
            format=data.format,
            status=SessionStatus.SCHEDULED,
            start_time=data.start_time,
            end_time=data.end_time,
            duration_minutes=duration_minutes,
            max_attendees=data.max_attendees,
            prerecorded_asset_url=data.prerecorded_asset_url
        )
        db.add(session_obj)
        await db.flush()

        # Bind speakers
        for spk_id in data.speaker_ids:
            assoc = SessionSpeaker(
                session_id=session_obj.id,
                speaker_id=spk_id,
                role=SpeakerRole.KEYNOTE_SPEAKER
            )
            db.add(assoc)

        journal = AgentTransactionJournal(
            tenant_id=data.tenant_id,
            agent_run_id="mcp_direct",
            idempotency_key=data.idempotency_key,
            tool_name="sessions.schedule_session",
            target_table="sessions",
            target_id=session_obj.id,
            operation="INSERT",
            forward_payload={"session_id": session_obj.id, "title": session_obj.title},
            compensating_patch={"tool_name": "sessions.delete_session", "session_id": session_obj.id}
        )
        db.add(journal)
        await db.commit()

        return {
            "status": "SUCCESS",
            "session_id": session_obj.id,
            "duration_minutes": duration_minutes,
            "transaction_id": journal.id
        }

    @classmethod
    async def update_session_media(cls, db: AsyncSession, session_id: str, asset_url: str) -> Dict[str, Any]:
        """Live incident triage tool: swap session stream/video."""
        stmt = select(Session).where(Session.id == session_id)
        res = await db.execute(stmt)
        session_obj = res.scalar_one_or_none()
        if not session_obj:
            return {"status": "ERROR_NOT_FOUND", "message": f"Session {session_id} not found."}

        old_asset = session_obj.prerecorded_asset_url
        session_obj.prerecorded_asset_url = asset_url
        session_obj.status = SessionStatus.BACKSTAGE_READY
        
        journal = AgentTransactionJournal(
            tenant_id=session_obj.tenant_id,
            agent_run_id="mcp_live_triage",
            idempotency_key=str(uuid.uuid4()),
            tool_name="sessions.update_session_media",
            target_table="sessions",
            target_id=session_obj.id,
            operation="UPDATE",
            forward_payload={"prerecorded_asset_url": asset_url},
            compensating_patch={"tool_name": "sessions.update_session_media", "prerecorded_asset_url": old_asset}
        )
        db.add(journal)
        await db.commit()

        return {
            "status": "SUCCESS",
            "session_id": session_obj.id,
            "updated_media_url": asset_url,
            "transaction_id": journal.id
        }

    @classmethod
    async def provision_booth(cls, db: AsyncSession, data: ProvisionBoothInput) -> Dict[str, Any]:
        cached = await cls.get_cached_idempotent_result(db, data.idempotency_key)
        if cached:
            return cached

        sponsor = Sponsor(
            tenant_id=data.tenant_id,
            event_id=data.event_id,
            name=data.sponsor_name,
            tier=data.tier,
            logo_url=data.logo_url,
            website_url=data.website_url
        )
        db.add(sponsor)
        await db.flush()

        booth = Booth(
            tenant_id=data.tenant_id,
            event_id=data.event_id,
            sponsor_id=sponsor.id,
            name=f"{data.sponsor_name} Booth",
            booth_3d_template=data.booth_3d_template,
            branding_assets=data.branding_assets,
            rep_emails=data.rep_emails
        )
        db.add(booth)
        await db.flush()

        journal = AgentTransactionJournal(
            tenant_id=data.tenant_id,
            agent_run_id="mcp_direct",
            idempotency_key=data.idempotency_key,
            tool_name="booths.provision_booth",
            target_table="booths",
            target_id=booth.id,
            operation="INSERT",
            forward_payload={"booth_id": booth.id, "sponsor_id": sponsor.id},
            compensating_patch={"tool_name": "booths.delete_booth", "booth_id": booth.id, "sponsor_id": sponsor.id}
        )
        db.add(journal)
        await db.commit()

        return {
            "status": "SUCCESS",
            "sponsor_id": sponsor.id,
            "booth_id": booth.id,
            "transaction_id": journal.id
        }

    @classmethod
    async def rollback_transaction(cls, db: AsyncSession, tenant_id: str, transaction_id: str) -> Dict[str, Any]:
        """Saga pattern compensating transaction executor."""
        stmt = select(AgentTransactionJournal).where(
            AgentTransactionJournal.id == transaction_id,
            AgentTransactionJournal.tenant_id == tenant_id,
            AgentTransactionJournal.is_reverted == False
        )
        res = await db.execute(stmt)
        record = res.scalar_one_or_none()
        if not record:
            return {"status": "ERROR_NOT_FOUND", "message": "Transaction not found or already reverted."}

        patch = record.compensating_patch
        tool = patch.get("tool_name")

        # Execute inverse compensation
        if tool == "sessions.delete_session":
            s_id = patch["session_id"]
            s_stmt = select(Session).where(Session.id == s_id)
            s_res = await db.execute(s_stmt)
            s_obj = s_res.scalar_one_or_none()
            if s_obj:
                await db.delete(s_obj)

        elif tool == "events.delete_event":
            e_id = patch["event_id"]
            e_stmt = select(Event).where(Event.id == e_id)
            e_res = await db.execute(e_stmt)
            e_obj = e_res.scalar_one_or_none()
            if e_obj:
                await db.delete(e_obj)

        elif tool == "booths.delete_booth":
            b_id = patch["booth_id"]
            sp_id = patch["sponsor_id"]
            b_stmt = select(Booth).where(Booth.id == b_id)
            sp_stmt = select(Sponsor).where(Sponsor.id == sp_id)
            b_obj = (await db.execute(b_stmt)).scalar_one_or_none()
            sp_obj = (await db.execute(sp_stmt)).scalar_one_or_none()
            if b_obj:
                await db.delete(b_obj)
            if sp_obj:
                await db.delete(sp_obj)

        record.is_reverted = True
        await db.commit()

        return {
            "status": "SUCCESS",
            "transaction_id": transaction_id,
            "action_reverted": tool
        }

    @classmethod
    async def get_event_manifest(cls, db: AsyncSession, event_id: str) -> Dict[str, Any]:
        """MCP Resource: event://{id}/manifest"""
        stmt = (
            select(Event)
            .where(Event.id == event_id)
            .options(
                selectinload(Event.tracks),
                selectinload(Event.rooms),
                selectinload(Event.sessions).selectinload(Session.speaker_associations).selectinload(SessionSpeaker.speaker),
                selectinload(Event.sponsors).selectinload(Sponsor.booth),
                selectinload(Event.ticket_tiers)
            )
        )
        res = await db.execute(stmt)
        event = res.scalar_one_or_none()
        if not event:
            return {}

        return {
            "event_id": event.id,
            "title": event.title,
            "format": event.format.value,
            "status": event.status.value,
            "start_time": event.start_time.isoformat(),
            "end_time": event.end_time.isoformat(),
            "tracks": [{"id": t.id, "name": t.name, "color": t.color_hex} for t in event.tracks],
            "rooms": [{"id": r.id, "name": r.name, "capacity": r.physical_capacity} for r in event.rooms],
            "sessions": [
                {
                    "id": s.id,
                    "title": s.title,
                    "track_id": s.track_id,
                    "room_id": s.room_id,
                    "start_time": s.start_time.isoformat(),
                    "end_time": s.end_time.isoformat(),
                    "duration": s.duration_minutes,
                    "speakers": [sa.speaker.full_name for sa in s.speaker_associations]
                }
                for s in event.sessions
            ],
            "sponsors": [
                {
                    "name": sp.name,
                    "tier": sp.tier.value,
                    "booth": sp.booth.name if sp.booth else None
                }
                for sp in event.sponsors
            ]
        }
