$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$installer = Join-Path $projectRoot '.tooling\vs_BuildTools.exe'
$signature = Get-AuthenticodeSignature $installer
if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Microsoft Corporation') {
    throw 'The compiler installer does not have a valid Microsoft signature.'
}
$installPath = Join-Path $projectRoot '.tooling\vs-buildtools'
$arguments = @(
    '--passive', '--norestart', '--wait',
    '--installPath', ('"' + $installPath + '"'),
    '--add', 'Microsoft.VisualStudio.Component.VC.Tools.x86.x64',
    '--add', 'Microsoft.VisualStudio.Component.Windows11SDK.26100'
)
Write-Output 'Starting the signed Microsoft installer. Windows may display its administrator consent dialog.'
$process = Start-Process -FilePath $installer -ArgumentList $arguments -Verb RunAs -PassThru -Wait
$receipt = @{
    installer = $installer
    signer = $signature.SignerCertificate.Subject
    installPath = $installPath
    exitCode = $process.ExitCode
    completedAt = [DateTime]::UtcNow.ToString('o')
}
$receipt | ConvertTo-Json | Set-Content (Join-Path $projectRoot 'evidence\cpp-installation.json') -Encoding UTF8
$receipt | ConvertTo-Json
if ($process.ExitCode -notin @(0, 3010)) { throw "Compiler installation failed: $($process.ExitCode)" }
