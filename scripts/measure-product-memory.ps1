param([ValidatePattern('^[a-z0-9_-]+$')][string]$Label)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$session=Get-Content "$root/output/session.json" | ConvertFrom-Json
$destination="$root/evidence/product-memory-$Label.json"
if(Test-Path $destination){throw 'Preserve a coleta anterior; use outro identificador.'}
$all=Get-CimInstance Win32_Process
$owned=@([int]$session.app,[int]$session.server)
do {$previous=$owned.Count;$owned=@($owned)+@($all | Where-Object {$owned -contains [int]$_.ParentProcessId} | ForEach-Object {[int]$_.ProcessId});$owned=@($owned | Sort-Object -Unique)} while($owned.Count -ne $previous)
$rows=@($owned | ForEach-Object {Get-Process -Id $_ -ErrorAction SilentlyContinue} | ForEach-Object {[PSCustomObject]@{pid=$_.Id;name=$_.ProcessName;working_set_bytes=$_.WorkingSet64;private_commit_bytes=$_.PrivateMemorySize64}})
$state=Invoke-RestMethod 'http://127.0.0.1:4700/api/state'
@{schema=1;utc=(Get-Date).ToUniversalTime().ToString('o');session=$session;mode=$state.mode;processes=$rows;sum_working_set_bytes=($rows | Measure-Object -Property working_set_bytes -Sum).Sum;sum_private_commit_bytes=($rows | Measure-Object -Property private_commit_bytes -Sum).Sum;scope='One native Windows product-process snapshot including engine, CEF, server and worker descendants if present. Working-set sum can count shared DLL pages twice. Separate isolated server excluded.'} | ConvertTo-Json -Depth 8 | Set-Content $destination -Encoding UTF8
Write-Output $destination
