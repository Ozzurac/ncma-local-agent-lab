param(
  [string]$Endpoint = "http://127.0.0.1:18991/v1/chat/completions",
  [string]$ModelAlias = "ncma-gptoss",
  [int]$MaxRounds = 18,
  [switch]$Resume,
  [switch]$AllowRemoteEndpoint
)
$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$uri = [Uri]$Endpoint
if ($uri.Scheme -notin @("http", "https")) {
  throw "Only HTTP(S) chat endpoints are supported."
}
if (-not $AllowRemoteEndpoint -and $uri.Host -notin @("127.0.0.1", "localhost", "::1")) {
  throw "Remote inference requires explicit -AllowRemoteEndpoint and a separately authenticated transport."
}
if ($MaxRounds -lt 1 -or $MaxRounds -gt 60) {
  throw "MaxRounds must be between 1 and 60."
}
$env:PYTHONPATH = (Join-Path $repo "src")
$env:NCMA_MODEL_API = $Endpoint
$env:NCMA_MODEL_ALIAS = $ModelAlias
$env:NCMA_RUN_DIR = (Join-Path $repo "runs/g4h")
$pyargs = @("-m", "ncma_lab.g4_hybrid", "--max-rounds", [string]$MaxRounds)
if ($Resume) { $pyargs += "--resume" }
Push-Location $repo
try {
  python @pyargs
  if ($LASTEXITCODE -notin @(0, 10)) {
    throw "G4H runner stopped with error code $LASTEXITCODE"
  }
  if ($LASTEXITCODE -eq 10) {
    Write-Output "Checkpoint saved. After reviewing the progress, run again with -Resume."
  }
} finally {
  Pop-Location
}
