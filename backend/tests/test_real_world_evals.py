import pytest
from app.evals.real_world_runner import run_real_world_evaluations

@pytest.mark.asyncio
async def test_real_world_conference_evaluations():
    scorecard = await run_real_world_evaluations()
    
    # Assertions on real-world SLAs
    assert float(scorecard["f1_score"].replace("%", "")) >= 90.0, "Real-world F1-Score SLA breached!"
    assert scorecard["zero_violation_rate"] == "100.0%", "Real-world Zero Violation Rate breached!"
    assert scorecard["conferences_evaluated"] >= 2

    for r in scorecard["results"]:
        assert r["verified_zero_collisions"] is True
