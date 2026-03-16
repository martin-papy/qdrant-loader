# Run ingest with contextual embeddings, then start MCP server for retrieval.
# Prereqs: OPENAI_API_KEY set; Qdrant running on localhost:6333 (or set QDRANT_URL).
# From repo root: .\packages\qdrant-loader\test_workspace_contextual\run_contextual_test.ps1
#
# Optional (e.g. when using UV and python is not on PATH): set a runner so commands
# are executed as "<runner> <cmd> <args>". No UV or tool names are hardcoded in this script.
#   $env:CONTEXTUAL_TEST_RUNNER = "uv run --project C:\path\to\repo\packages\qdrant-loader"
#   $env:CONTEXTUAL_TEST_MCP_RUNNER = "uv run --project C:\path\to\repo\packages\qdrant-loader-mcp-server"  # optional, defaults to CONTEXTUAL_TEST_RUNNER

$ErrorActionPreference = "Stop"
$WorkspaceDir = $PSScriptRoot
$SampleDataDir = Join-Path $WorkspaceDir "sample_data"

# Use forward slashes for file:// URL (required by localfile connector)
$SampleDataPath = (Resolve-Path $SampleDataDir).Path -replace '\\', '/'
$env:CONTEXTUAL_TEST_DATA_DIR = $SampleDataPath

Write-Host "Workspace: $WorkspaceDir"
Write-Host "Sample data (file://): $SampleDataPath"
if ($env:CONTEXTUAL_TEST_RUNNER) { Write-Host "Runner (loader): $env:CONTEXTUAL_TEST_RUNNER" }
if ($env:CONTEXTUAL_TEST_MCP_RUNNER) { Write-Host "Runner (MCP):   $env:CONTEXTUAL_TEST_MCP_RUNNER" }
Write-Host ""

if (-not $env:OPENAI_API_KEY) {
    Write-Host "Set OPENAI_API_KEY before running (e.g. `$env:OPENAI_API_KEY = 'sk-...')" -ForegroundColor Yellow
    exit 1
}

$RepoRoot = (Get-Item $WorkspaceDir).Parent.Parent.Parent.FullName
$ConfigPath = Join-Path $WorkspaceDir "config.yaml"
$UseRunner = [bool]$env:CONTEXTUAL_TEST_RUNNER
$McpRunner = if ($env:CONTEXTUAL_TEST_MCP_RUNNER) { $env:CONTEXTUAL_TEST_MCP_RUNNER } else { $env:CONTEXTUAL_TEST_RUNNER }

# When no runner: use qdrant-loader/mcp-qdrant-loader if on PATH, else python -m
$QdrantLoaderArgs = if ($UseRunner) { @() } elseif (Get-Command qdrant-loader -ErrorAction SilentlyContinue) {
    @("qdrant-loader") } else { @("python", "-m", "qdrant_loader.main") }
$McpArgs = if ($McpRunner) { @() } elseif (Get-Command mcp-qdrant-loader -ErrorAction SilentlyContinue) {
    @("mcp-qdrant-loader") } else { @("python", "-m", "qdrant_loader_mcp_server") }

function Run-Loader {
    param([string[]]$CmdArgs)
    if ($UseRunner) {
        $quoted = $CmdArgs | ForEach-Object { "`"$_`"" }; Invoke-Expression "$env:CONTEXTUAL_TEST_RUNNER qdrant-loader $($quoted -join ' ')"
    } else {
        & $QdrantLoaderArgs[0] $QdrantLoaderArgs[1..($QdrantLoaderArgs.Length-1)] $CmdArgs
    }
}
function Run-Mcp {
    param([string[]]$CmdArgs)
    if ($McpRunner) {
        $quoted = $CmdArgs | ForEach-Object { "`"$_`"" }; Invoke-Expression "$McpRunner $($quoted -join ' ')"
    } else {
        & $McpArgs[0] $McpArgs[1..($McpArgs.Length-1)] $CmdArgs
    }
}

Push-Location $RepoRoot

try {
    Write-Host "=== 1. Init collection ===" -ForegroundColor Cyan
    Run-Loader @("init", "--config", $ConfigPath, "--force")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host ""
    Write-Host "=== 2. Ingest (contextual_embedding enabled) ===" -ForegroundColor Cyan
    Run-Loader @("ingest", "--config", $ConfigPath, "--force", "--log-level", "INFO")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host ""
    Write-Host "=== 3. Start MCP server (retrieval) ===" -ForegroundColor Cyan
    Write-Host "Set QDRANT_URL if not localhost:6333. Then use Postman or Cursor to call search." -ForegroundColor Gray
    $env:QDRANT_COLLECTION_NAME = "contextual_test_collection"
    Run-Mcp @("--transport", "http", "--port", "8080", "--log-level", "INFO")
} finally {
    Pop-Location
}
