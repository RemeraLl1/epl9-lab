[CmdletBinding()]
param([string]$OutputPath)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$configPath = Join-Path $projectRoot 'local\environment.json'
$config = if (Test-Path -LiteralPath $configPath) {
    Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
} else { $null }

$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
$pythonPath = if ($config -and $config.python) { $config.python } elseif ($pythonCommand) { $pythonCommand.Source } else { $null }
$wiresharkCandidates = @(
    (Join-Path $projectRoot 'tools\Wireshark\Wireshark.exe'),
    (Join-Path $projectRoot 'tools\Wireshark\Wireshark\Wireshark.exe'),
    'C:\Program Files\Wireshark\Wireshark.exe'
)
$wiresharkPath = $wiresharkCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
$usbTreePath = Join-Path $projectRoot 'tools\UsbTreeView\UsbTreeView.exe'
$usbPcapService = Get-Service -Name USBPcap -ErrorAction SilentlyContinue
$npcapService = Get-Service -Name npcap -ErrorAction SilentlyContinue
$workspaceCandidates = @(
    'C:\Program Files (x86)\OMDS\OM Workspace\OM Workspace.exe',
    'C:\Program Files\OMDS\OM Workspace\OM Workspace.exe',
    'C:\Program Files (x86)\OLYMPUS\Olympus Workspace\Olympus Workspace.exe'
)
$workspacePath = $workspaceCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
$report = [ordered]@{
    python = $pythonPath
    pythonVersion = if ($pythonPath) { (& $pythonPath --version 2>&1 | Out-String).Trim() } else { $null }
    wireshark = $wiresharkPath
    usbTreeView = if (Test-Path -LiteralPath $usbTreePath) { $usbTreePath } else { $null }
    usbPcapDriver = if ($usbPcapService) { [string]$usbPcapService.Status } else { 'NotInstalled' }
    npcapDriver = if ($npcapService) { [string]$npcapService.Status } else { 'NotInstalled' }
    omWorkspace = $workspacePath
    cameraTesting = 'Pending'
}
$json = $report | ConvertTo-Json
if ($OutputPath) {
    $fullOutputPath = [IO.Path]::GetFullPath($OutputPath)
    if (Test-Path -LiteralPath $fullOutputPath) { throw 'Output already exists; choose a new report path.' }
    [IO.File]::WriteAllText($fullOutputPath, $json + [Environment]::NewLine, [Text.UTF8Encoding]::new($false))
}
$json
