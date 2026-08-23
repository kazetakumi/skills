#!/usr/bin/env python3
"""Turn this clone into a project folder: move the skills into .claude/skills,
then drop the git history and the installers. Run once, from inside the clone."""
import os
import shutil
import stat
import subprocess
import sys
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

# Empty out everything except this running script.
for item in sorted(root.iterdir()):
    if item == Path(__file__).resolve():
        continue
    if item.is_dir():
        shutil.rmtree(item)
    else:
        item.unlink()

print("root cleaned up; scheduling removal of the clone folder itself")

# Now remove `root` (including this script) via a detached follow-up
# process, since we can't delete a running script/its folder from within.
if os.name == "nt":
    subprocess.Popen(
        ["cmd", "/c", f'ping 127.0.0.1 -n 2 >nul & rmdir /s /q "{root}"'],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
else:
    subprocess.Popen(
        ["/bin/sh", "-c", f'sleep 1; rm -rf "{root}"'],
        start_new_session=True,
    )

sys.exit(0)
