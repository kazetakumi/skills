#!/bin/sh
# Turn this clone into a project folder: move the skills into .claude/skills,
# then drop the git history and the installers. Run once, from inside the clone.
set -eu

cd "$(dirname "$0")"

mkdir -p .claude/skills
for skill in */; do
  mv "$skill" .claude/skills/
done

rm -rf .git

echo "skills moved to .claude/skills"
exec rm -f install.sh install.ps1 install.py
