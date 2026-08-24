# Semantic Metadata Hotfix v1.0.1

This hotfix fixes two issues:

1. Removes the remaining deprecated `student_metrics` literal from `data/schema/business_glossary.fa.json`.
2. Adds UTF-8 stdout/stderr configuration to validation scripts to avoid Windows PowerShell `UnicodeEncodeError` when printing Persian text.

## Apply

```powershell
cd D:\Project\ADHD-VTD
Expand-Archive -Path "$env:USERPROFILE\Downloads\vtd_phase0_semantic_metadata_hotfix_v1_0_1.zip" -DestinationPath ".\_semantic_hotfix" -Force
Copy-Item ".\_semantic_hotfix\vtd_phase0_semantic_metadata_fix_package\data\schema\business_glossary.fa.json" ".\data\schema\business_glossary.fa.json" -Force
Copy-Item ".\_semantic_hotfix\vtd_phase0_semantic_metadata_fix_package\scripts\phase0_validate_semantic_metadata.py" ".\scripts\phase0_validate_semantic_metadata.py" -Force
Copy-Item ".\_semantic_hotfix\vtd_phase0_semantic_metadata_fix_package\scripts\test_schema_metadata_alignment.py" ".\scripts\test_schema_metadata_alignment.py" -Force
python .\scripts\phase0_validate_semantic_metadata.py
python .\scripts\test_schema_metadata_alignment.py
```

Expected result:

```text
Semantic metadata checks: 11/11 passed
✅ Semantic metadata is aligned with current schema.
```
