ASTROGUARD — PHASE 2.4.0 CORRECTED EXECUTION PACKAGE (V3)
==========================================================

This is a targeted correction to the Phase 2.4.0 dataset audit acceptance rule.

Confirmed dataset layout from the user's audit:
- Four groups: baseline/A-1, baseline/P-1, advanced/A-1, advanced/P-1
- Each group has train features, test features, and test labels.
- The current pipeline does not emit train-label arrays.

Correct acceptance rule:
- Train features: required
- Test features: required
- Test labels: required
- Train labels: optional

No raw or processed dataset is modified by the audit.

Package contents:
- PHASE_2_4_0_EXECUTE.ps1
- PHASE_2_4_0_DATASET_AUDIT.py
- PHASE_2_4_0_PREFLIGHT.py
- README_PHASE_2_4_0_PACKAGE_V3.txt

Install:
1. Extract all files directly into:
   C:\Users\PC\source\AstroGuard
2. Keep all existing project files.
3. Run parser validation:
   $t=$null; $e=$null
   [System.Management.Automation.Language.Parser]::ParseFile(
     (Resolve-Path .\PHASE_2_4_0_EXECUTE.ps1).Path,[ref]$t,[ref]$e
   ) | Out-Null
   if ($e.Count -eq 0) { '[PASS] PowerShell syntax' } else { $e | Format-List Message,Extent }
4. Execute only after parser PASS:
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\PHASE_2_4_0_EXECUTE.ps1

The runner performs Python/NumPy preflight, audit syntax validation, dataset
audit, backend regression, existing native CTest (no rebuild), and before/after
SHA-256 preservation checks. Reports are written under artifacts\phase_2_4_0.

Phase 2 is not complete unless final acceptance reports PASS.
