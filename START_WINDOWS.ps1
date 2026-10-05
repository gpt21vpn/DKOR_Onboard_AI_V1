$ErrorActionPreference = "Stop"

Write-Host "DKOR Onboard V1 - local start" -ForegroundColor Cyan

if (!(Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host ".env created from .env.example" -ForegroundColor Yellow
}

if (!(Test-Path .venv)) {
    python -m venv .venv
}

& .\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r .\backend\requirements.txt

Start-Process powershell -ArgumentList '-NoExit','-Command',"cd '$PWD\frontend'; npm install; npm run dev"

python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
