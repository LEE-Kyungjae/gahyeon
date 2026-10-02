param(
    [Parameter(Mandatory = $true)][string]$Executable,
    [Parameter(Mandatory = $true)][string]$Screenshot,
    [Parameter(Mandatory = $true)][string]$Manifest,
    [string]$CoreApiUrl = "http://127.0.0.1:8080/api",
    [string]$ClientToken = "",
    [string]$UserDataDir = ""
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) {
    throw "Gahyeon executable is missing: $Executable"
}
foreach ($Target in @($Screenshot, $Manifest)) {
    if (Test-Path -LiteralPath $Target) { throw "refusing to overwrite evidence: $Target" }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Target) | Out-Null
}

$env:GAHYEON_DESKTOP_WINDOW_PRESET = "character"
$env:GAHYEON_DESKTOP_ALWAYS_ON_TOP = "true"
$env:GAHYEON_DESKTOP_CLICK_THROUGH = "false"
$env:GAHYEON_CORE_API_URL = $CoreApiUrl
$ClientToken = if ($ClientToken) { $ClientToken } else { $env:GAHYEON_CLIENT_TOKEN }
$env:GAHYEON_CLIENT_TOKEN = $ClientToken
$Started = Get-Date
$Arguments = @()
if ($UserDataDir) {
    New-Item -ItemType Directory -Force -Path $UserDataDir | Out-Null
    $Arguments += "--user-data-dir=$UserDataDir"
}
$Process = Start-Process -FilePath $Executable -ArgumentList $Arguments -PassThru
$Deadline = (Get-Date).AddSeconds(30)
do {
    Start-Sleep -Milliseconds 500
    $Process.Refresh()
} while ($Process.MainWindowHandle -eq [IntPtr]::Zero -and (Get-Date) -lt $Deadline)
if ($Process.MainWindowHandle -eq [IntPtr]::Zero) { throw "Gahyeon did not expose a native window" }

Start-Sleep -Seconds 6
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms
$Bounds = [System.Windows.Forms.SystemInformation]::VirtualScreen
$Bitmap = New-Object System.Drawing.Bitmap($Bounds.Width, $Bounds.Height)
$Graphics = [System.Drawing.Graphics]::FromImage($Bitmap)
try {
    $Graphics.CopyFromScreen($Bounds.Left, $Bounds.Top, 0, 0, $Bitmap.Size)
    $Bitmap.Save($Screenshot, [System.Drawing.Imaging.ImageFormat]::Png)
} finally {
    $Graphics.Dispose()
    $Bitmap.Dispose()
}

$Process.Refresh()
$Evidence = [ordered]@{
    schemaVersion = 1
    status = "passed"
    characterBlueprint = "/Game/Gahyeon/CharacterPipeline/v088/AssembledMedium/Skotukeda_WardrobeGroomQA_v088/BP_Skotukeda_WardrobeGroomQA_v088"
    presentation = "pre-rendered-alpha-media-poc"
    liveUnrealStreaming = $false
    coreApiUrl = $CoreApiUrl
    processId = $Process.Id
    executable = $Process.Path
    nativeWindowObserved = $Process.MainWindowHandle -ne [IntPtr]::Zero
    processStartedAt = $Started.ToString("o")
    screenshot = $Screenshot
    screenshotSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $Screenshot).Hash.ToLowerInvariant()
    screenshotWidth = $Bounds.Width
    screenshotHeight = $Bounds.Height
    leftRunningForReview = -not $Process.HasExited
}
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($Manifest, ($Evidence | ConvertTo-Json -Depth 5) + [Environment]::NewLine, $Utf8NoBom)
$Evidence | ConvertTo-Json -Depth 5
