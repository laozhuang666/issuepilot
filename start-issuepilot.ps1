$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonPath = Join-Path $projectRoot ".venv\Scripts\python.exe"
$appUrl = "http://127.0.0.1:8000/"
$healthUrl = "http://127.0.0.1:8000/api/health"

Set-Location -LiteralPath $projectRoot

try {
    $health = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 2
    if ($health.status -eq "ok") {
        Write-Host "IssuePilot is already running. Opening the browser..." -ForegroundColor Green
        Start-Process $appUrl
        exit 0
    }
} catch {
    # No existing server is listening, so continue with startup.
}

if (-not (Test-Path -LiteralPath $pythonPath)) {
    Write-Host "Creating the Python environment..." -ForegroundColor Cyan
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3 -m venv .venv
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        & python -m venv .venv
    } else {
        throw "Python 3.11 or newer was not found. Install Python and run this launcher again."
    }
}

& $pythonPath -c "import issuepilot, uvicorn" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing IssuePilot dependencies (first launch only)..." -ForegroundColor Cyan
    & $pythonPath -m pip install -e ".[dev]"
    if ($LASTEXITCODE -ne 0) {
        throw "Dependency installation failed. Check the network connection and try again."
    }
}

if (-not (Test-Path -LiteralPath ".env")) {
    Copy-Item -LiteralPath ".env.example" -Destination ".env"
    Write-Host "Created .env. The local planner works without API keys." -ForegroundColor DarkGray
}

Write-Host "Starting IssuePilot at $appUrl" -ForegroundColor Green
Write-Host "Keep this window open. Press Ctrl+C to stop the service." -ForegroundColor Yellow

$browserJob = Start-Job -ScriptBlock {
    param($targetHealthUrl, $targetAppUrl)
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        try {
            $response = Invoke-RestMethod -Uri $targetHealthUrl -TimeoutSec 1
            if ($response.status -eq "ok") {
                Start-Process $targetAppUrl
                return
            }
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
} -ArgumentList $healthUrl, $appUrl

try {
    & $pythonPath -m uvicorn issuepilot.api:app --host 127.0.0.1 --port 8000
} finally {
    Remove-Job -Job $browserJob -Force -ErrorAction SilentlyContinue
}

