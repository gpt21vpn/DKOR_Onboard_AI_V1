$ErrorActionPreference = "Stop"
if (Test-Path .\.venv\Scripts\Activate.ps1) { & .\.venv\Scripts\Activate.ps1 }
python scripts\validate_kb.py
python -m pytest -q tests
