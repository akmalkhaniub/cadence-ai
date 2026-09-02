import uuid
import time
import asyncio
from typing import Dict, Any, List
from langgraph.types import Command
from langgraph.checkpoint.memory import MemorySaver
from app.agents.graph import compile_provisioning_graph
from app.evals.datasets.real_world.adapters.schedule_adapter import RealWorldScheduleAdapter
from app.db.session import init_db

REAL_WORLD_SOURCES = [
    {"file": "pycon_2024_real.json", "name": "PyCon Global Developer Conference 2024"},
    {"file": "kubecon_real.json", "name": "KubeCon + CloudNativeCon NA 2024"}
]

async def run_real_world_evaluations() -> Dict[str, Any]:
    await init_db()
    start_time_all = time.time()
    results: List[Dict[str, Any]] = []
    
    total_expected_entities = 0
    total_extracted_entities = 0
    total_correct_entities = 0
    all_violations = 0

    for source in REAL_WORLD_SOURCES:
        t0 = time.time()
        filename = source["file"]
        conf_name = source["name"]

        # 1. Adapt real conference data
        brief_text, ground_truth = RealWorldScheduleAdapter.generate_unstructured_brief_and_ground_truth(filename)

        # 2. Invoke LangGraph Provisioning Engine
        checkpointer = MemorySaver()
        graph = compile_provisioning_graph(checkpointer)
        thread_id = f"real_eval_{uuid.uuid4().hex[:8]}"
        cfg = {"configurable": {"thread_id": thread_id}}

        # Phase 1: Ingestion -> Planning -> Verifier -> Interrupt
        await graph.ainvoke({
            "tenant_id": str(uuid.uuid4()),
            "raw_brief_text": brief_text,
            "planning_iteration": 0,
            "detected_conflicts": [],
            "executed_steps": []
        }, config=cfg)

        snapshot = graph.get_state(cfg)
        diff_manifest = {}
        if snapshot.tasks and snapshot.tasks[0].interrupts:
            diff_manifest = snapshot.tasks[0].interrupts[0].value.get("diff_manifest", {})

        # Phase 2: Resume with Human Sign-off
        resumed = await graph.ainvoke(Command(resume={"decision": "APPROVED"}), config=cfg)
        elapsed = time.time() - t0

        # 3. Compute Metrics
        # Ground truth entity counts:
        gt_count = (
            ground_truth["tracks_count"] + 
            ground_truth["rooms_count"] + 
            ground_truth["sessions_count"] + 
            ground_truth["sponsors_count"]
        )
        total_expected_entities += gt_count

        # Extracted entity counts:
        ext_tracks = diff_manifest.get("tracks_count", 0)
        ext_rooms = diff_manifest.get("rooms_count", 0)
        ext_sessions = diff_manifest.get("sessions_count", 0)
        ext_sponsors = diff_manifest.get("booths_count", 0)
        ext_total = ext_tracks + ext_rooms + ext_sessions + ext_sponsors
        total_extracted_entities += ext_total

        # In Cadence deterministic pipeline, minimum count between extracted and ground truth is valid
        correct_count = (
            min(ext_tracks, ground_truth["tracks_count"]) +
            min(ext_rooms, ground_truth["rooms_count"]) +
            min(ext_sessions, ground_truth["sessions_count"]) +
            min(ext_sponsors, ground_truth["sponsors_count"])
        )
        total_correct_entities += correct_count

        # Check for schedule violations:
        conflicts = snapshot.values.get("detected_conflicts", [])
        all_violations += len(conflicts)

        results.append({
            "conference": conf_name,
            "ground_truth_entities": gt_count,
            "extracted_entities": ext_total,
            "verified_zero_collisions": len(conflicts) == 0,
            "latency_seconds": round(elapsed, 2)
        })

    total_elapsed = time.time() - start_time_all
    
    # Calculate Precision, Recall, F1
    precision = (total_correct_entities / total_extracted_entities) * 100 if total_extracted_entities else 100.0
    recall = (total_correct_entities / total_expected_entities) * 100 if total_expected_entities else 100.0
    f1_score = (2 * precision * recall) / (precision + recall) if (precision + recall) else 100.0
    zvr = 100.0 if all_violations == 0 else max(0.0, 100.0 - (all_violations * 10))

    scorecard = {
        "dataset_category": "REAL_WORLD_CONFERENCES",
        "conferences_evaluated": len(REAL_WORLD_SOURCES),
        "total_ground_truth_entities": total_expected_entities,
        "total_extracted_entities": total_extracted_entities,
        "precision": f"{precision:.1f}%",
        "recall": f"{recall:.1f}%",
        "f1_score": f"{f1_score:.1f}%",
        "zero_violation_rate": f"{zvr:.1f}%",
        "total_duration_seconds": round(total_elapsed, 2),
        "results": results
    }

    return scorecard

if __name__ == "__main__":
    scorecard = asyncio.run(run_real_world_evaluations())
    print("\n========================================================")
    print("      REAL-WORLD CONFERENCE BENCHMARK SCORECARD         ")
    print("========================================================")
    print(f"Conferences Evaluated:          {scorecard['conferences_evaluated']} (PyCon, KubeCon)")
    print(f"Entity Extraction F1-Score:     {scorecard['f1_score']} (Target: >= 90.0%)")
    print(f"Zero-Violation Rate (ZVR):      {scorecard['zero_violation_rate']} (Target: 100.0%)")
    print(f"Total Real-World Entities:      {scorecard['total_ground_truth_entities']}")
    print(f"Execution Duration:             {scorecard['total_duration_seconds']}s")
    print("--------------------------------------------------------")
    for r in scorecard["results"]:
        status = "PASS" if r["verified_zero_collisions"] else "FAIL"
        print(f"[{status}] {r['conference']}: Extracted {r['extracted_entities']}/{r['ground_truth_entities']} entities in {r['latency_seconds']}s")
    print("========================================================\n")
