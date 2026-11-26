$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$compilerEnvironment="$root\.tooling\vs-buildtools\VC\Auxiliary\Build\vcvars64.bat"
$batch="$root\output\verify-native-readers-build.cmd"
$command=@"
@echo off
call "$compilerEnvironment" >nul
if errorlevel 1 exit /b 1
cl.exe /nologo /std:c++20 /O2 /EHsc /utf-8 /I"$root\.upstream\openspace" /I"$root\.upstream\openspace\ext\ghoul\include" "$root\scripts\verify-native-readers.cpp" /Fe:"$root\output\verify-native-readers.exe" /Fo:"$root\output\verify-native-readers.obj"
"@
$command | Set-Content $batch -Encoding ASCII
& cmd.exe /d /c $batch
if ($LASTEXITCODE -ne 0) { throw 'Compilacao do verificador nativo falhou.' }
$result=& "$root\output\verify-native-readers.exe" "$root\data\galaxy\points.off" | Out-String
if ($LASTEXITCODE -ne 0) { throw 'Verificacao dos leitores nativos falhou.' }
$report=$result | ConvertFrom-Json
$hashes=@{}
foreach($file in @('scripts/verify-native-readers.cpp','data/galaxy/points.off',
  '.upstream/openspace/modules/galaxy/rendering/galaxypointreader.h',
  '.upstream/openspace/ext/ghoul/include/ghoul/font/utf8.h')) {
  $hashes[$file]=(Get-FileHash "$root/$file" -Algorithm SHA256).Hash.ToLowerInvariant()
}
$report | Add-Member -NotePropertyName source_sha256 -NotePropertyValue $hashes
$report | Add-Member -NotePropertyName native_compiler -NotePropertyValue 'MSVC via project vcvars64'
$report | ConvertTo-Json -Depth 5 | Set-Content "$root\evidence\native-readers-check.json" -Encoding UTF8
Get-Content "$root\evidence\native-readers-check.json"
