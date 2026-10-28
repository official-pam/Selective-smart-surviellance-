$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$dashboardPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $dashboardPython)) {
    $dashboardPython = Join-Path $PSScriptRoot '../uniface-face-recognition/.venv/Scripts/python.exe'
}
& $dashboardPython -m streamlit run dashboard.py --server.address 127.0.0.1 --server.port 8502 --server.headless true
