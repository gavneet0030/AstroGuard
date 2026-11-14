ASTROGUARD — PHASE 2.4.0 EXECUTION PACKAGE
==========================================

Package contents:
- PHASE_2_4_0_EXECUTE.ps1
- PHASE_2_4_0_DATASET_AUDIT.py
- PHASE_2_4_0_PREFLIGHT.py
- README_PHASE_2_4_0.txt

Extract all files directly into:
C:\Users\PC\source\AstroGuard

Then open PowerShell:
Set-Location C:\Users\PC\source\AstroGuard

Validate:
$t=$null; $e=$null
[System.Management.Automation.Language.Parser]::ParseFile(
 (Resolve-Path .\PHASE_2_4_0_EXECUTE.ps1).Path,[ref]$t,[ref]$e
) | Out-Null
if ($e.Count -eq 0) { '[PASS] PowerShell syntax' } else { $e | Format-List Message,Extent }

Only after parser PASS:
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\PHASE_2_4_0_EXECUTE.ps1

Keep existing project files. This runner does not rebuild native code or rewrite raw/processed datasets.
Reports and preservation snapshots are written under artifacts\phase_2_4_0.
Phase 2 is not complete until Phase 2.4.0 reports PASS.
