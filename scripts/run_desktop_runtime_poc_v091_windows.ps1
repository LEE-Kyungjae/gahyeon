param(
    [Parameter(Mandatory = $true)][string]$UnrealRoot,
    [string]$EvidenceRoot = "",
    [string]$Python = "python",
    [int]$StartupTimeoutSeconds = 120,
    [switch]$RunRealtimeAcceptance
)

$ErrorActionPreference = "Stop"
$NativeWindows = [System.Environment]::OSVersion.Platform -eq [System.PlatformID]::Win32NT
if (-not $NativeWindows) { throw "The v091 Windows runtime gate requires a native Windows host" }
if ($StartupTimeoutSeconds -lt 30 -or $StartupTimeoutSeconds -gt 300) {
    throw "StartupTimeoutSeconds must be between 30 and 300"
}
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $EvidenceRoot) {
    $EvidenceRoot = Join-Path $RepoRoot "artifacts\desktop-looking-glass-runtime-poc-v091\windows-native"
}
if (Test-Path -LiteralPath $EvidenceRoot) {
    throw "Windows evidence root already exists and will not be overwritten: $EvidenceRoot"
}
New-Item -ItemType Directory -Path $EvidenceRoot | Out-Null

$GateRoot = Join-Path $EvidenceRoot "unreal-gate"
& (Join-Path $PSScriptRoot "run_unreal_engine_gate.ps1") `
    -UnrealRoot $UnrealRoot -Python $Python -EvidenceRoot $GateRoot -Package
if ($LASTEXITCODE -ne 0) { throw "Win64 build/cook/package gate failed" }

$PackageRoot = Join-Path $GateRoot "package"
$Executable = Join-Path $PackageRoot "GahyeonStage.exe"
$RuntimeExecutable = Join-Path $PackageRoot "GahyeonStage\Binaries\Win64\GahyeonStage.exe"
if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) {
    throw "Packaged GahyeonStage bootstrap executable is missing: $Executable"
}
if (-not (Test-Path -LiteralPath $RuntimeExecutable -PathType Leaf)) {
    throw "Packaged GahyeonStage runtime executable is missing: $RuntimeExecutable"
}
$RuntimeMap = "/Game/Gahyeon/DesktopRuntime/v091/L_GahyeonDesktopRuntime_v091"

Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class GahyeonWindowCapture {
    [StructLayout(LayoutKind.Sequential)] public struct RECT {
        public int Left; public int Top; public int Right; public int Bottom;
    }
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
}
'@

function Invoke-GahyeonVisualRun {
    param([Parameter(Mandatory = $true)][string]$Name)
    $Log = Join-Path $EvidenceRoot "$Name.log"
    $Screenshot = Join-Path $EvidenceRoot "$Name.png"
    $Arguments = @(
        $RuntimeMap, "-windowed", "-ResX=1280", "-ResY=720", "-WinX=80", "-WinY=80",
        "-NoSplash", "-log", "-abslog=$Log"
    )
    $LaunchStarted = (Get-Date).AddSeconds(-2)
    $BootstrapProcess = Start-Process -FilePath $Executable -ArgumentList $Arguments -PassThru
    $WindowProcess = $null
    $Result = $null
    try {
        $Deadline = (Get-Date).AddSeconds($StartupTimeoutSeconds)
        do {
            Start-Sleep -Milliseconds 500
            $Candidates = @(Get-Process -Name "GahyeonStage" -ErrorAction SilentlyContinue | Where-Object {
                try {
                    $_.Refresh()
                    $_.MainWindowHandle -ne [IntPtr]::Zero -and
                        $_.StartTime -ge $LaunchStarted -and
                        [string]::Equals($_.Path, $RuntimeExecutable, [System.StringComparison]::OrdinalIgnoreCase)
                } catch { $false }
            })
            if ($Candidates.Count -gt 1) { throw "$Name found multiple native runtime windows" }
            if ($Candidates.Count -eq 1) { $WindowProcess = $Candidates[0] }
        } while ($null -eq $WindowProcess -and (Get-Date) -lt $Deadline)
        if ($null -eq $WindowProcess) {
            throw "$Name did not expose a native window before the timeout"
        }
        Start-Sleep -Seconds 8
        $Rect = New-Object GahyeonWindowCapture+RECT
        if (-not [GahyeonWindowCapture]::GetWindowRect($WindowProcess.MainWindowHandle, [ref]$Rect)) {
            throw "$Name window bounds could not be read"
        }
        $Width = $Rect.Right - $Rect.Left
        $Height = $Rect.Bottom - $Rect.Top
        if ($Width -lt 640 -or $Height -lt 360) { throw "$Name window is unexpectedly small" }
        [void][GahyeonWindowCapture]::SetForegroundWindow($WindowProcess.MainWindowHandle)
        Start-Sleep -Milliseconds 500
        $Bitmap = New-Object System.Drawing.Bitmap($Width, $Height)
        $Graphics = [System.Drawing.Graphics]::FromImage($Bitmap)
        try {
            $Graphics.CopyFromScreen($Rect.Left, $Rect.Top, 0, 0, $Bitmap.Size)
            $Bitmap.Save($Screenshot, [System.Drawing.Imaging.ImageFormat]::Png)
        } finally {
            $Graphics.Dispose()
            $Bitmap.Dispose()
        }
        if ((Get-Item -LiteralPath $Screenshot).Length -lt 10000) {
            throw "$Name screenshot is too small to be credible"
        }
        if (-not (Test-Path -LiteralPath $Log -PathType Leaf)) { throw "$Name runtime log is missing" }
        $LogText = Get-Content -LiteralPath $Log -Raw
        if ($LogText -notmatch "L_GahyeonDesktopRuntime_v091") {
            throw "$Name did not load the v091 Desktop runtime map"
        }
        if ($LogText -match "Fatal error:|Gahyeon visual actor unavailable") {
            throw "$Name reported a fatal or missing visual actor"
        }
        $Result = [ordered]@{
            name = $Name
            processStarted = $true
            nativeWindowObserved = $true
            mapObserved = $true
            screenshot = (Split-Path -Leaf $Screenshot)
            screenshotSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $Screenshot).Hash.ToLowerInvariant()
            log = (Split-Path -Leaf $Log)
            width = $Width
            height = $Height
        }
    } finally {
        if ($null -ne $WindowProcess -and -not $WindowProcess.HasExited) {
            [void]$WindowProcess.CloseMainWindow()
            if (-not $WindowProcess.WaitForExit(15000)) { Stop-Process -Id $WindowProcess.Id -Force }
        }
        if (-not $BootstrapProcess.HasExited) {
            if (-not $BootstrapProcess.WaitForExit(5000)) { Stop-Process -Id $BootstrapProcess.Id -Force }
        }
    }
    $Result["logSha256"] = (Get-FileHash -Algorithm SHA256 -LiteralPath $Log).Hash.ToLowerInvariant()
    return $Result
}

$First = Invoke-GahyeonVisualRun -Name "first-launch"
$Restart = Invoke-GahyeonVisualRun -Name "restart"
if ($RunRealtimeAcceptance) {
    & (Join-Path $PSScriptRoot "run_desktop_realtime_acceptance.ps1") `
        -PackagedRoot $PackageRoot `
        -EvidenceRoot (Join-Path $EvidenceRoot "realtime-acceptance") `
        -Python $Python -RequirePassed
    if ($LASTEXITCODE -ne 0) { throw "Win64 realtime acceptance failed" }
}

$Manifest = [ordered]@{
    schemaVersion = 1
    status = "passed"
    platform = "Win64"
    engineVersion = "5.8"
    nativeExecution = $true
    packagedBuild = $true
    runtimeMap = $RuntimeMap
    executableSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $Executable).Hash.ToLowerInvariant()
    firstLaunch = $First
    restart = $Restart
    realtimeAcceptanceRun = [bool]$RunRealtimeAcceptance
}
$ManifestPath = Join-Path $EvidenceRoot "manifest.json"
$ManifestJson = $Manifest | ConvertTo-Json -Depth 8
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($ManifestPath, $ManifestJson + [Environment]::NewLine, $Utf8NoBom)
Write-Host "Gahyeon v091 native Windows runtime gate passed: $EvidenceRoot"
