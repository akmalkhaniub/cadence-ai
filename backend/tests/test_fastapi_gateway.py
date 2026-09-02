import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.session import init_db

@pytest.fixture(autouse=True)
async def setup_database():
    await init_db()

@pytest.mark.asyncio
async def test_gateway_health_checks():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res_live = await client.get("/healthz")
        assert res_live.status_code == 200
        assert res_live.json()["status"] == "HEALTHY"

        res_ready = await client.get("/readyz")
        assert res_ready.status_code == 200
        assert res_ready.json()["status"] == "READY"

@pytest.mark.asyncio
async def test_rest_provisioning_and_hitl_lifecycle():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Start Provisioning
        prov_res = await client.post(
            "/api/v1/events/provision",
            json={
                "tenant_id": str(uuid.uuid4()),
                "raw_brief_text": "title: FastApi Test Summit\n3 tracks, keynote on Main Stage."
            }
        )
        assert prov_res.status_code == 200
        data = prov_res.json()
        thread_id = data["thread_id"]
        assert data["status"] == "INTERRUPTED"
        assert data["hitl_payload"]["diff_manifest"]["sessions_count"] == 2

        # 2. Inspect Thread State
        state_res = await client.get(f"/api/v1/events/threads/{thread_id}/state")
        assert state_res.status_code == 200
        state_data = state_res.json()
        assert state_data["is_interrupted"] is True

        # 3. Resume with Approval
        resume_res = await client.post(
            f"/api/v1/events/threads/{thread_id}/resume",
            json={"decision": "APPROVED"}
        )
        assert resume_res.status_code == 200
        resumed_data = resume_res.json()
        assert resumed_data["status"] == "COMPLETED"
        event_id = resumed_data["event_id"]
        assert event_id is not None

        # 4. Fetch Provisioned Manifest
        manifest_res = await client.get(f"/api/v1/events/{event_id}/manifest")
        assert manifest_res.status_code == 200
        manifest = manifest_res.json()
        assert manifest["title"] == "FastApi Test Summit"
        assert len(manifest["tracks"]) == 2
        assert len(manifest["sessions"]) == 2

@pytest.mark.asyncio
async def test_multipart_brief_upload():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        fake_pdf_content = b"title: Multipart Upload Conference\nTwo stages and sponsors."
        files = {"file": ("brief.txt", fake_pdf_content, "text/plain")}
        
        upload_res = await client.post(
            "/api/v1/events/brief/upload",
            files=files
        )
        assert upload_res.status_code == 200
        data = upload_res.json()
        assert data["status"] == "INTERRUPTED"
        assert data["hitl_payload"] is not None
