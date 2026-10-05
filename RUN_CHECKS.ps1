$ErrorActionPreference = "Stop"
python scripts/build_kb.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python scripts/validate_kb.py
exit $LASTEXITCODE
