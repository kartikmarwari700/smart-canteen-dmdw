# Runs the full pipeline. Usage: .\run_all.ps1
$ErrorActionPreference = "Stop"
py -3.11 src/generate_data.py
py -3.11 src/real_data.py
py -3.11 src/etl.py
py -3.11 src/olap.py | Out-Null
py -3.11 src/mining.py
Write-Host "Done. Start dashboard with:  py -3.11 -m streamlit run app/dashboard.py"
