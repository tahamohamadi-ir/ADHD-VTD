param(
  [string]$ProjectRoot = "D:\Project\ADHD-VTD"
)

$PackageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$TargetRoot = Join-Path $ProjectRoot ".agents\skills"
New-Item -ItemType Directory -Force -Path $TargetRoot | Out-Null

$skills = @(
  "artifact-reproducibility",
  "benchmark-evaluation",
  "persian-nlu-schema-linking",
  "prompt-engineering",
  "query-shape-contract-engineering",
  "sql-validation-safety"
)

foreach ($skill in $skills) {
  $src = Join-Path $PackageRoot $skill
  $dst = Join-Path $TargetRoot $skill
  if (-not (Test-Path $src)) { Write-Host "MISSING SOURCE: $src"; continue }
  if ((Resolve-Path $src).Path -eq (Resolve-Path $dst -ErrorAction SilentlyContinue).Path) {
    Write-Host "SKIP SELF: $skill"
    continue
  }
  Copy-Item -Path $src -Destination $TargetRoot -Recurse -Force
  Write-Host "INSTALLED: $skill"
}

& (Join-Path $PackageRoot "fix_skill_frontmatter.ps1") -SkillsDir $TargetRoot
