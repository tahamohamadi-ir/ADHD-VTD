# Phase 2 Hotfix v1.0.2 - COUNT(*) Safety Validator Fix

This hotfix fixes a regression introduced by the CTE SELECT-star policy:

- `SELECT * FROM table` remains rejected.
- `SELECT table.* FROM table` remains rejected.
- `COUNT(*)` is now correctly allowed.
- CTE-internal `SELECT *` remains allowed when the final projection is explicit.

## Apply

```powershell
cd D:\Project\ADHD-VTD

Expand-Archive -Path "$env:USERPROFILE\Downloads\vtd_phase2_hotfix_v1_0_2.zip" -DestinationPath ".\_phase2_hotfix_102" -Force

Copy-Item ".\src\sql_validation\safety_validator.py" ".\src\sql_validation\safety_validator.py.bak_phase2_hotfix_1_0_2" -Force

Copy-Item ".\_phase2_hotfix_102\vtd_phase2_hotfix_v1_0_2\src\sql_validation\safety_validator.py" ".\src\sql_validation\safety_validator.py" -Force
Copy-Item ".\_phase2_hotfix_102\vtd_phase2_hotfix_v1_0_2\scripts\test_safety_validator_count_star_hotfix.py" ".\scripts\test_safety_validator_count_star_hotfix.py" -Force
```

## Test

```powershell
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

python .\scripts\test_safety_validator_count_star_hotfix.py
python .\scripts\test_sql_validators.py
python .\scripts\test_evaluation_foundation.py
python .\scripts\run_phase0_evaluation_summary.py
```

Expected:

```text
Safety validator COUNT(*) hotfix checks passed.
SELECT COUNT(*) FROM student_depression
safety True []
Gold SQL ok: 50/50
Evaluation foundation checks passed.
```
