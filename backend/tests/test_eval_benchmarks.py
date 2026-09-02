import pytest
from app.evals.runner import run_evaluation_suite

@pytest.mark.asyncio
async def test_evaluation_benchmark_suite():
    scorecard = await run_evaluation_suite("ALL")
    
    # Assertions on core SLAs
    assert float(scorecard["task_success_rate"].replace("%", "")) >= 95.0, "Task Success Rate SLA breached!"
    assert scorecard["tool_hallucination_rate"] == "0.00%", "Tool Hallucination SLA breached!"
    assert scorecard["rollback_parity_checksum"] == "100.0%", "Rollback Parity Checksum SLA breached!"
    assert scorecard["total_scenarios_evaluated"] >= 5

    # Ensure every single scenario passed
    for res in scorecard["results"]:
        assert res["status"] == "PASS", f"Scenario {res['id']} failed!"
