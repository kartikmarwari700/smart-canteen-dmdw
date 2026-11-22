# Runs the full pipeline. Usage: .\run_all.ps1
$ErrorActionPreference = "Stop"
function Step($script) {
    Write-Host "==> $script"
    py -3.11 $script
    if ($LASTEXITCODE -ne 0) { throw "$script failed (exit code $LASTEXITCODE)" }
}
Step "src/generate_data.py"
Step "src/real_data.py"
Step "src/etl.py"
Step "src/olap.py"
Step "src/mining.py"
Write-Host "Done. Start dashboard with:  py -3.11 -m streamlit run app/dashboard.py"
