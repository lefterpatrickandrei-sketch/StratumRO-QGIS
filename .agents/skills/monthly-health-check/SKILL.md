---
name: monthly-health-check
description: Periodic repository health diagnostic covering git statistics, test suite trends, disk usage, and GitHub presence metrics
---

# Monthly Health Check Skill

Run this diagnostic monthly (or before major releases) to assess project health.

## Diagnostic Steps

### 1. Commit Cadence
```bash
git log --since="30 days ago" --format="%h %ad %s" --date=short
git log --format="%ad" --date=format:"%Y-%m" | Group-Object | Sort-Object Name
```
**Healthy:** ≥10 commits/month during active sprints

### 2. Branch Hygiene
```bash
git branch -a
git branch --merged main  # Candidates for deletion
```
**Action:** Delete all merged branches. Evaluate unmerged branches — merge or archive.

### 3. Unpushed Commits
```bash
git rev-list --count origin/main..HEAD
```
**Healthy:** 0 (always push at end of work session)

### 4. Disk Usage by Directory
```powershell
Get-ChildItem -Directory -Exclude ".git","venv" | ForEach-Object {
    $size = (Get-ChildItem $_.FullName -Recurse -File -EA 0 | Measure-Object Length -Sum).Sum
    "$($_.Name): $([math]::Round($size / 1MB, 1)) MB"
} | Sort-Object { [double]($_ -split ': ')[1].Replace(' MB','') } -Descending
```
**Alert if:** Any non-code directory exceeds 500 MB

### 5. Test Suite Health
```bash
venv\Scripts\python -m unittest discover stratum_ro/test
```
**Track:** Total tests, passed, skipped, failed, runtime. Compare with previous month.

### 6. Untracked Files Audit
```bash
git status --short | Select-String "^\?\?"
```
**Action:** Either `.gitignore` or `git add` every untracked item. Zero ambiguity.

### 7. GitHub Presence
Check via GitHub API or browser:
- Stars, forks, watchers
- Open issues/PRs (target: 0 stale issues)
- Last push date
- License present?

### 8. Evidence Matrix Audit
```bash
Select-String "UNVERIFIED" docs/EVIDENCE_MATRIX.md
```
**Healthy:** Zero UNVERIFIED items

## Output Format

Create a summary with:
- Date of check
- Key metrics table (commits, tests, disk, GitHub)
- Action items identified
- Comparison with previous check (if available)
