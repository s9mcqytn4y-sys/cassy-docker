[CmdletBinding()]
param(
    [ValidateSet("Dev", "Demo", "Prod", "VpsGateway")]
    [string]$Stack = "Dev",
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ComposeArgs = @("ps")
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$DockerRoot = Split-Path -Parent $PSScriptRoot
$ComposeMap = @{
    "Dev"        = Join-Path $DockerRoot "Core\DockerComposeDev.yml"
    "Demo"       = Join-Path $DockerRoot "Core\DockerComposeDemo.yml"
    "Prod"       = Join-Path $DockerRoot "Core\DockerComposeProd.yml"
    "VpsGateway" = Join-Path $DockerRoot "VpsGateway\DockerComposeVpsGateway.yml"
}

$ComposeFile = $ComposeMap[$Stack]
if (-not (Test-Path $ComposeFile)) {
    throw "Compose file not found: $ComposeFile"
}

& docker compose -f $ComposeFile @ComposeArgs
exit $LASTEXITCODE
