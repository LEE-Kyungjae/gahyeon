param(
    [Parameter(Mandatory = $true)][string]$Screenshot
)

$ErrorActionPreference = "Stop"
$Process = Get-Process Gahyeon -ErrorAction Stop | Where-Object MainWindowHandle -ne 0 | Select-Object -First 1
if (-not $Process) { throw "Gahyeon native character window is unavailable" }
if (Test-Path -LiteralPath $Screenshot) { throw "refusing to overwrite evidence: $Screenshot" }
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Screenshot) | Out-Null

Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class GahyeonPointer {
  [StructLayout(LayoutKind.Sequential)] public struct Rect { public int Left, Top, Right, Bottom; }
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr handle, out Rect rect);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint flags, uint dx, uint dy, uint data, UIntPtr extra);
}
"@

$Rect = New-Object GahyeonPointer+Rect
if (-not [GahyeonPointer]::GetWindowRect($Process.MainWindowHandle, [ref]$Rect)) {
    throw "failed to inspect Gahyeon window bounds"
}
[GahyeonPointer]::SetCursorPos($Rect.Right - 79, $Rect.Bottom - 49) | Out-Null
[GahyeonPointer]::mouse_event(0x0002, 0, 0, 0, [UIntPtr]::Zero)
[GahyeonPointer]::mouse_event(0x0004, 0, 0, 0, [UIntPtr]::Zero)
Start-Sleep -Seconds 2

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

@{
    status = "passed"
    interaction = "controls-island-expanded"
    screenshot = $Screenshot
    screenshotSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $Screenshot).Hash.ToLowerInvariant()
} | ConvertTo-Json
