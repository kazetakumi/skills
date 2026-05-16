# skills

A collection of Claude Code skills for learning, building, and thinking.

## What is a skill?

A skill is a markdown instruction file that tells Claude Code how to behave in a specific context. Invoke any skill with `/skill-name` in Claude Code.

## Skills

| Skill | Description |
|-------|-------------|
| [first-principles-tutor](./first-principles-tutor/SKILL.md) | Learn while building. Breaks any concept into axioms, teaches from the ground up, anchors to real project code, and tracks your progress across sessions. |

## Installing a skill

Copy the skill folder into `~/.claude/skills/`:

```bash
cp -r first-principles-tutor ~/.claude/skills/
```

Then invoke it in Claude Code:

```
/first-principles-tutor build the backend
```

## Structure

```
skills/
└── skill-name/
    ├── SKILL.md          # Instructions Claude reads
    └── learner/          # Runtime data (git-ignored per skill)
        ├── graph.json
        ├── profile.md
        ├── traversal.py
        └── concepts/
```
