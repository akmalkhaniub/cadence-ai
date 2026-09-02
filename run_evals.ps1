# ==============================================================================
# Cadence AI: Local Evaluation & Verification Suite
# ==============================================================================

Write-Host "`n========================================================" -ForegroundColor Cyan
Write-Host "         RUNNING CADENCE AI LOCAL TEST SUITE            " -ForegroundColor Cyan
Write-Host "========================================================`n" -ForegroundColor Cyan

Set-Location -Path "$PSScriptRoot\backend"

Write-Host "--> 1. Executing Pytest Integration Suite..." -ForegroundColor Yellow
uv run pytest tests/ -v

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[ERROR] Integration tests failed." -ForegroundColor Red
    exit 1
}

Write-Host "`n--> 2. Running In-Platform Evaluation Studio Benchmarks..." -ForegroundColor Yellow
uv run python -m app.evals.runner

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[ERROR] Evaluation benchmark runner encountered an error." -ForegroundColor Red
    exit 1
}

Write-Host "`n========================================================" -ForegroundColor Green
Write-Host "  ALL LOCAL EVALUATIONS & BENCHMARKS PASSED (100% PASS) " -ForegroundColor Green
Write-Host "========================================================`n" -ForegroundColor Green

Write-Host "To launch the full interactive application locally:" -ForegroundColor Cyan
Write-Host "  Terminal 1 (Backend):" -ForegroundColor White
Write-Host "    cd backend; uv run uvicorn app.main:app --reload --port 8000" -ForegroundColor Gray
Write-Host "  Terminal 2 (Frontend UI):" -ForegroundColor White
Write-Host "    cd frontend; npm run dev" -ForegroundColor Gray
Write-Host "  Browser: http://localhost:5173" -ForegroundColor White
Write-Host ""
