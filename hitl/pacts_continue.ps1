# PACTS HITL Continue Script (PowerShell)
# Double-click to signal HITL continue

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Definition
$continueFile = Join-Path $scriptPath "continue.ok"

# Create empty continue.ok file
New-Item -Path $continueFile -ItemType File -Force | Out-Null

Write-Host "✅ HITL continue signal sent!" -ForegroundColor Green
Write-Host "File created: $continueFile" -ForegroundColor Cyan

# Auto-close after 2 seconds
Start-Sleep -Seconds 2
