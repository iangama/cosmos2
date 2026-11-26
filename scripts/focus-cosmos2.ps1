$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$session = Get-Content "$root\output\session.json" | ConvertFrom-Json
$engine = Get-Process -Id $session.app
if ($engine.ProcessName -ne 'OpenSpace' -or !$engine.Path.StartsWith($root, [StringComparison]::OrdinalIgnoreCase)) { throw 'Sessão não identifica o motor deste projeto.' }
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class Cosmos2WindowFocus {
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint p);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
}
'@
[uint32]$cosmos2ForegroundPid = 0
[Cosmos2WindowFocus]::GetWindowThreadProcessId([Cosmos2WindowFocus]::GetForegroundWindow(), [ref]$cosmos2ForegroundPid) | Out-Null
$previous = Get-Process -Id $cosmos2ForegroundPid -ErrorAction SilentlyContinue
$focused = [Cosmos2WindowFocus]::SetForegroundWindow($engine.MainWindowHandle)
@{ previous_foreground_pid=$cosmos2ForegroundPid; previous_process=$previous.ProcessName; engine_pid=$engine.Id; focus_requested=$focused } | ConvertTo-Json
