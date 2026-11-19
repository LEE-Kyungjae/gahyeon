param([string]$Output = (Join-Path $PSScriptRoot 'GahyeonOverlay.exe'))
$ErrorActionPreference='Stop'
$Compiler=Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
& $Compiler /nologo /target:winexe /optimize+ /r:System.Drawing.dll /r:System.Windows.Forms.dll /r:System.Net.Http.dll /r:System.Web.Extensions.dll "/out:$Output" (Join-Path $PSScriptRoot 'Overlay.cs') (Join-Path $PSScriptRoot 'Chrome.cs') (Join-Path $PSScriptRoot 'Lettering.cs') (Join-Path $PSScriptRoot 'Conversation.cs')
if ($LASTEXITCODE -ne 0) { throw 'Windows overlay compilation failed' }
