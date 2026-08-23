#!/usr/bin/env python3
"""Turn this clone into a project folder: move the skills into .claude/skills,
then drop the git history and the installers. Run once, from inside the clone."""
import os
import shutil
import stat
from pathlib import Path

root = Path(__file__).resolve().parent
project_root = root.parent
dest = project_root / ".claude" / "skills"
dest.mkdir(parents=True, exist_ok=True)

for item in sorted(root.iterdir()):
    if item.is_dir() and not item.name.startswith("."):
        shutil.move(str(item), str(dest / item.name))

claude_md = root / "claude.md"
if claude_md.exists():
    shutil.move(str(claude_md), str(project_root / claude_md.name))

git = root / ".git"
try:
    shutil.rmtree(git)
except PermissionError:
    # Windows marks git's pack files read-only, which blocks the delete.
    for path in git.rglob("*"):
        os.chmod(path, stat.S_IWRITE)
    shutil.rmtree(git)

print("skills moved to .claude/skills")

for installer in ("install.sh", "install.ps1", "install.py"):
    (root / installer).unlink(missing_ok=True)

# Delete whatever's left in root (this script's own dir), since its
# contents have all been relocated or removed above.
for item in sorted(root.iterdir()):
    if item == Path(__file__).resolve():
        continue  # don't delete the running script out from under itself
    if item.is_dir():
        shutil.rmtree(item)
    else:
        item.unlink()

print("root cleaned up")
