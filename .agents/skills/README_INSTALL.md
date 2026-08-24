# ADHD-VTD Agent Skills - Frontmatter Fixed

This package contains six JetBrains AI Assistant / Agent Skills. Each skill is a directory with a `SKILL.md` file and YAML frontmatter containing at least `name` and `description`.

## Install

Copy the six skill folders into:

```text
D:\Project\ADHD-VTD\.agents\skills
```

Expected final structure:

```text
D:\Project\ADHD-VTD\.agents\skills\artifact-reproducibility\SKILL.md
D:\Project\ADHD-VTD\.agents\skills\benchmark-evaluation\SKILL.md
D:\Project\ADHD-VTD\.agents\skills\persian-nlu-schema-linking\SKILL.md
D:\Project\ADHD-VTD\.agents\skills\prompt-engineering\SKILL.md
D:\Project\ADHD-VTD\.agents\skills\query-shape-contract-engineering\SKILL.md
D:\Project\ADHD-VTD\.agents\skills\sql-validation-safety\SKILL.md
```

Then open PyCharm:

```text
Settings > Tools > AI Assistant > Skills
```

Add or refresh this directory:

```text
D:\Project\ADHD-VTD\.agents\skills
```

## Verify in PowerShell

```powershell
cd D:\Project\ADHD-VTD\.agents\skills
Get-ChildItem -Directory | ForEach-Object {
  $skill = Join-Path $_.FullName 'SKILL.md'
  if (Test-Path $skill) {
    $first = Get-Content $skill -TotalCount 1
    "$($_.Name) => SKILL.md exists, first line: $first"
  }
}
```

Each first line must be `---`.
