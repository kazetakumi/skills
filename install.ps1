# Turn this clone into a project folder: move the skills into .claude\skills,
# then drop the git history and the installers. Run once, from inside the clone.
$ErrorActionPreference = 'Stop'

Set-Location $PSScriptRoot

$dest = '.claude\skills'
New-Item -ItemType Directory -Force -Path $dest | Out-Null

Get-ChildItem -Directory |
  Where-Object { $_.Name -notlike '.*' } |
  ForEach-Object { Move-Item -LiteralPath $_.FullName -Destination $dest }

# Git marks its pack files read-only, which blocks the delete.
Get-ChildItem .git -Recurse -Force -File | ForEach-Object { $_.IsReadOnly = $false }
Remove-Item .git -Recurse -Force

Write-Host 'skills moved to .claude/skills'
Remove-Item install.ps1, install.sh, install.py -Force
