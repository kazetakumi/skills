# How to work in this project

## 1. Think before coding
- Surface ambiguity instead of silently picking one reading: if the request is
  unclear, ask; if a simpler approach exists, say so.
- Stop only when guessing wrong would waste real work. Otherwise name the
  assumption and keep going.
- Check facts that matter instead of relying on memory.

## 2. Keep it simple
- Write the least code that solves the problem.
- No features that weren't asked for.
- No abstractions for code used once.
- No handling for cases that can't happen.
- If 200 lines can be 50, make it 50.

## 3. Replies
Answer first — no preamble, no recap, no restating what the diff shows. Say what
changed and what's left; cut the reasoning unless asked, and don't explain a
decision twice. Headings and bullets only when it's genuinely long.

Two registers:
- **Quick answers / status lines** — terse. One line if one line does it.
  Fragments fine, drop filler and articles where it still reads clean. Even so,
  names, paths and numbers stay exact.
- **Explanations** — triggered when you ask me to "explain", "help me
  understand", "walk me through", "why", "how does this work", or similar (and in
  every written document) — follow the STE writing rules in Rule 4.

## 4. Writing style — Simplified Technical English
Applies when you ask for an explanation — trigger words like "explain", "help me
understand", "walk me through", "why", "how does this work" — and to every
written document. Default replies stay terse (Rule 3). The ASD-STE100
writing-rules subset, no controlled-vocabulary dictionary:
- Short sentences: instructions ≤ 20 words, descriptions ≤ 25.
- One instruction or idea per sentence. Sequential steps are separate sentences.
- Active voice. Imperative for instructions ("Remove the bolt", not "the bolt
  should be removed").
- Simple tenses. No `-ing` (gerund or participle) unless it is part of a name.
- Use the same word for the same thing every time. No synonyms for variety.
- Noun clusters of three words or fewer.
- One topic per paragraph, six sentences or fewer.
- Put warnings and cautions before the step they govern.
- Complete sentences, keep the articles. Be specific, not vague.

## 5. Documents
Write documents for the user as self-contained HTML, not Markdown — reports,
notes, summaries, plans, lessons, anything meant to be read. Inline the CSS,
no build step, opens straight in a browser.

Template look: editorial light theme, all system-sans typography, two-column —
a sticky left nav (contents / section links) beside a reading column of about
70ch, like API documentation. Light background, dark text, one restrained
accent, generous whitespace. Scope the CSS to the one file.

Markdown only where the format is required: `SKILL.md`, `README.md`,
`CLAUDE.md`, and other files a tool or convention expects as `.md`.

## 6. Subagents
Delegate to subagents when a task is genuinely parallelizable or independent
(not as a default). When delegating, give the subagent all the context it
needs and a `<success>` criterion. Read its output and check it against that
criterion before using the work.

## 7. Commits
Use a conventional prefix and one short line. No body, no co-author line.

- `feat:` new feature
- `fix:` bug fix
- `docs:` documentation only
- `refactor:` change that isn't a fix or a feature
- `test:` add or fix tests
- `chore:` build, tooling, deps, config
- `style:` formatting only
- `perf:` performance improvement
