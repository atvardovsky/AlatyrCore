$ErrorActionPreference = "Stop"

$ScriptPath = Join-Path $PSScriptRoot "validate_target_adapter.py"

if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 $ScriptPath @args
    exit $LASTEXITCODE
}

if (Get-Command python -ErrorAction SilentlyContinue) {
    & python $ScriptPath @args
    exit $LASTEXITCODE
}

Write-Error "Python 3 was not found. Install Python 3 or run the helper with an explicit Python path."
exit 1
