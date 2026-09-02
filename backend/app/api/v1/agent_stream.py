import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from langgraph.types import Command
from app.api.v1.events import provisioning_engine

router = APIRouter(tags=["stream"])

@router.websocket("/events/{event_id}/agent-stream")
async def websocket_agent_stream(websocket: WebSocket, event_id: str):
    await websocket.accept()
    thread_id = f"ws_thread_{event_id}"
    config = {"configurable": {"thread_id": thread_id}}

    try:
        # Send initial connected status
        await websocket.send_text(json.dumps({
            "type": "CONNECTION_ESTABLISHED",
            "event_id": event_id,
            "thread_id": thread_id
        }))

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            msg_type = message.get("type")

            if msg_type == "START_PROVISIONING":
                raw_brief = message.get("raw_brief_text", "")
                tenant_id = message.get("tenant_id", "00000000-0000-0000-0000-000000000001")

                # Stream initial state
                await websocket.send_text(json.dumps({
                    "type": "NODE_EXECUTION_STATE",
                    "node_name": "parser",
                    "status": "RUNNING"
                }))
                await asyncio.sleep(0.05)

                await websocket.send_text(json.dumps({
                    "type": "LLM_TOKEN_STREAM",
                    "delta": "Parsing event parameters: tracks, rooms, and schedule bounds...\n"
                }))

                # Invoke graph up to interrupt
                initial_input = {
                    "tenant_id": tenant_id,
                    "event_id": event_id,
                    "raw_brief_text": raw_brief,
                    "planning_iteration": 0,
                    "detected_conflicts": [],
                    "executed_steps": []
                }
                await provisioning_engine.ainvoke(initial_input, config=config)

                snapshot = provisioning_engine.get_state(config)
                if snapshot.tasks and snapshot.tasks[0].interrupts:
                    interrupt_val = snapshot.tasks[0].interrupts[0].value
                    await websocket.send_text(json.dumps({
                        "type": "HITL_INTERRUPT_REQUIRED",
                        "payload": interrupt_val
                    }))

            elif msg_type == "HITL_INTERRUPT_RESPONSE":
                decision = message.get("decision", "APPROVED")
                feedback = message.get("rejection_feedback")

                await websocket.send_text(json.dumps({
                    "type": "NODE_EXECUTION_STATE",
                    "node_name": "workers",
                    "status": "RUNNING"
                }))

                resumed = await provisioning_engine.ainvoke(
                    Command(resume={"decision": decision, "feedback": feedback}),
                    config=config
                )

                await websocket.send_text(json.dumps({
                    "type": "RUN_COMPLETED",
                    "event_id": resumed.get("event_id"),
                    "executed_steps": resumed.get("executed_steps", [])
                }))

    except WebSocketDisconnect:
        pass
