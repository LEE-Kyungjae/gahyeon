param(
    [string]$RuntimeRoot = 'C:\GahyeonRuntime\roster-20261016',
    [string]$EngineRoot = 'C:\Program Files\Epic Games\UE_5.8'
)
$ErrorActionPreference = 'Stop'
$Manifest = Get-Content -Raw (Join-Path $RuntimeRoot 'canonical-character-runtime.json') | ConvertFrom-Json
if ($Manifest.status -ne 'ready' -or $Manifest.runtime -ne 'unreal' -or $Manifest.windows.status -ne 'ready') { throw 'Canonical Windows runtime is not ready' }
$Platform = $Manifest.windows
if (-not $Platform.runtimeMap -or -not $Platform.characterAsset -or -not $Platform.animationProfile) { throw 'Incomplete canonical Windows character identity' }
$Project = Join-Path $RuntimeRoot $Platform.project
$Overlay = Join-Path $RuntimeRoot 'native\GahyeonOverlay.exe'
$Editor = Join-Path $EngineRoot 'Engine\Binaries\Win64\UnrealEditor.exe'
$Module = Join-Path $RuntimeRoot 'GahyeonDesktopMetaHumanPOC\Binaries\Win64\UnrealEditor-GahyeonDesktopMetaHumanPOC.dll'
foreach ($File in @($Project,$Overlay,$Editor,$Module)) { if (-not (Test-Path -LiteralPath $File)) { throw "Missing runtime file: $File" } }
$env:GAHYEON_CORE_URL = 'http://127.0.0.1:18080/api'
$env:GAHYEON_CLIENT_TOKEN = (& wsl.exe -d Ubuntu-24.04 -- cat /home/ubuntu/.config/gahyeon/client-token).Trim()
if (-not $env:GAHYEON_CLIENT_TOKEN) { throw 'Missing Core client credential' }
$Status = Invoke-RestMethod -Uri ($env:GAHYEON_CORE_URL + '/gahyeon/desktop/speech/status') -Headers @{ Authorization = 'Bearer ' + $env:GAHYEON_CLIENT_TOKEN }
$Arguments = @('"' + $Project + '"',$Platform.runtimeMap,'-game','-windowed','-ForceRes','-ResX=1600','-ResY=1258','-RenderOffscreen','-NoSplash','-nosourcecontrol','-GahyeonCPUAlphaFallback','-ExecCmds="r.MotionBlurQuality 0,r.DefaultFeature.MotionBlur 0,r.ScreenPercentage 100,r.AntiAliasingMethod 1,r.TextureStreaming 0,r.PostProcessing.PropagateAlpha 1,r.ExposureOffset 0.5"','-abslog="' + (Join-Path $RuntimeRoot 'runtime.log') + '"')
$Runtime = Start-Process -FilePath $Editor -ArgumentList ($Arguments -join ' ') -PassThru -WorkingDirectory $RuntimeRoot
$Ui = $null
try {
    $Ui = Start-Process -FilePath $Overlay -PassThru -WorkingDirectory $RuntimeRoot
    @{ runtimePid=$Runtime.Id; overlayPid=$Ui.Id; speech=$Status; runtime='unreal' } | ConvertTo-Json | Set-Content -Encoding UTF8 (Join-Path $RuntimeRoot 'launch-result.json')
    while (-not $Runtime.HasExited -and -not $Ui.HasExited) { Start-Sleep -Seconds 1; $Runtime.Refresh(); $Ui.Refresh() }
} finally {
    if ($Ui -and -not $Ui.HasExited) { Stop-Process -Id $Ui.Id }
    if (-not $Runtime.HasExited) { Stop-Process -Id $Runtime.Id }
    Remove-Item Env:GAHYEON_CLIENT_TOKEN -ErrorAction SilentlyContinue
}
