param(
  [string]$SkillsDir = "D:\Project\ADHD-VTD\.agents\skills"
)

$frontmatters = @{
  "artifact-reproducibility" = "Use this skill for manifests, artifact verification, paper table generation, reproducibility scripts, dataset hashes, and release packaging."
  "benchmark-evaluation" = "Use this skill when working on benchmark runner, metrics, ablation, semantic judge, behavioral evaluation, or paper tables."
  "persian-nlu-schema-linking" = "Use this skill for Persian normalization, colloquial and Finglish mapping, ambiguity detection, intent routing, schema linking, value linking, and metric definitions."
  "prompt-engineering" = "Use this skill when editing Jinja prompt templates for SQL generation, repair, clarification, answer generation, or semantic judge."
  "query-shape-contract-engineering" = "Use this skill when fixing valid-but-wrong SQL, scalar, grouped, ranking, timeseries, matrix errors, or prompt over-grouping."
  "sql-validation-safety" = "Use this skill for safety validator, schema validator, join validator, aggregation validator, semantic validator, SQL rewriter, read-only executor, or privacy rules."
}

foreach ($name in $frontmatters.Keys) {
  $file = Join-Path $SkillsDir "$name\SKILL.md"
  if (-not (Test-Path $file)) {
    Write-Host "MISSING: $file"
    continue
  }

  $content = Get-Content -Path $file -Raw -Encoding UTF8
  if ($content.StartsWith("---`n") -or $content.StartsWith("---`r`n")) {
    Write-Host "OK: $name already has frontmatter"
    continue
  }

  $front = "---`nname: $name`ndescription: $($frontmatters[$name])`n---`n`n"
  Set-Content -Path $file -Value ($front + $content) -Encoding UTF8
  Write-Host "PATCHED: $name"
}

Write-Host "Done. Refresh Skills in PyCharm."
