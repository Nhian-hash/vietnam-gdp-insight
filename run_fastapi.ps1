$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

Write-Host "V-MEST"
Write-Host "Dashboard: http://127.0.0.1:8000/"
Write-Host "API docs:  http://127.0.0.1:8000/docs"
Write-Host "Stop the server with Ctrl+C."

python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
