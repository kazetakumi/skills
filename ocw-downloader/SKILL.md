---
name: ocw-downloader
description: Find a relevant course on MIT OpenCourseWare, Stanford Engineering Everywhere (SEE), or a curated Stanford course microsite (e.g. CS336) and download its video transcripts, lecture notes, problem sets, and exams into an organized folder. Use when the user names a topic (e.g. "linear algebra", "large language models"), an MIT course number ("18.06", "6.006"), a Stanford SEE course code ("CS229", "EE364A"), a Stanford course-site code ("CS336"), a course title, or pastes an ocw.mit.edu / see.stanford.edu course URL and wants the course materials downloaded locally.
---

# OpenCourseWare downloader (MIT + Stanford SEE + Stanford course sites)

Downloads a course's **video transcripts**, **lecture notes/slides/PDFs**, and
**problem sets / assignments / exams** from **MIT OpenCourseWare**
(`ocw.mit.edu`), **Stanford Engineering Everywhere** (`see.stanford.edu`), or a
small hand-curated set of **individual Stanford course microsites** (e.g.
`cs336.stanford.edu`) into an organized `courses/<slug>/` folder. Video files
themselves are intentionally skipped — the transcripts stand in for them.

The engine is the bundled script `ocw_download.py` (pure Python 3 stdlib — no
`pip install` needed for MIT or SEE). MIT is resolved via the MIT Learn API
(`api.learn.mit.edu`); Stanford SEE has no API — it's a small, fixed ~9-course
catalog, hardcoded in the script and resolved by scraping `see.stanford.edu`
course pages. **Stanford course microsites are a third, separate case** — see
below. Run it via the skill's own directory — `<skill-dir>` below is this
skill's base directory (shown when the skill loads):

```
python3 "<skill-dir>/ocw_download.py" <subcommand> ...
```

## The three inputs → a course

- **Topic / keyword** ("quantum mechanics") → run `search` as one input among
  several — it returns MIT's API hits plus the full SEE and microsite
  catalogs, institution-tagged, but **relevance judgment is yours, not the
  script's** (see Workflow step 1 — this is the fix for real search misses
  like "transformers").
- **Course number/code or title** ("18.06", "CS229", "CS336") → `resolve`.
  MIT numbers (`18.06`), SEE codes (`CS229`), and microsite codes (`CS336`)
  never collide, so a bare code/number resolves unambiguously to its source.
- **Direct course URL** (`https://ocw.mit.edu/courses/<slug>/` or
  `https://see.stanford.edu/Course/<CODE>`) → `resolve`. Microsite courses
  resolve by code only (each is its own bespoke site with no single URL
  pattern to match against).

## Stanford course microsites (e.g. CS336) — a narrower case

Individual Stanford courses (like `cs336.stanford.edu`) have no shared
catalog or API — every course is its own site, so this is a **hand-curated
registry** (`MICROSITE_CATALOG` in `ocw_download.py`), currently just CS336.
Adding another course here means adding a new entry by hand, not something
`search` can discover on its own.

**Transcripts only, not slides/assignments.** These courses' materials (slides,
assignment code) typically live in a per-course GitHub repo with its own
structure — genuinely out of scope for this pass, unlike MIT/SEE's PDFs.
Transcripts instead come from **YouTube captions** on the course's lecture
playlist, via the vendored `yttdl` tool
(`<skill-dir>/yttdl/`, itself a `uv` project — **requires `uv` installed**,
unlike the rest of this skill). If `uv` isn't available, tell the user and
offer to install it, or fall back to the course's public materials without
transcripts.

If asked about a topic that isn't in `MICROSITE_CATALOG`, `search` simply
won't surface it from this source — that's expected, not a bug; mention that
the coverage here is intentionally narrow (currently CS336 only) rather than
implying the whole of Stanford's course-site landscape is searched.

## Workflow

1. **If the input is a topic/keyword, YOU do the semantic matching — `search`
   is a data source, not the decision-maker.** MIT's API and SEE/microsite's
   catalogs are both keyword-literal underneath; relying on that alone
   produces real failures (query "transformers" returns geothermal-energy
   "Transforming" noise and misses MIT's actual transformers course, because
   the API never returns it — no amount of re-ranking fixes a course that was
   never in the result set).

   - Run `search "<query>" --limit 8` for a supplementary candidate pool —
     it returns MIT's API hits (query-driven) plus the **entire** SEE and
     microsite catalogs (small enough to always include in full; don't rely
     on their titles containing the literal query words).
   - **Also propose MIT candidates from your own knowledge of the topic**
     (course numbers or titles you're aware of that plausibly cover it) —
     this is the actual fix for MIT's recall gap, not a nice-to-have.
   - **Verify every proposed-from-knowledge MIT candidate via `resolve`
     before mentioning it to the user** — this is the guard rail against
     hallucination. A course number you recall might not exist, might have
     been renumbered, or might have no transcripts; `resolve` against the
     real API is the only thing keeping a knowledge-based guess honest.
     Never present an unverified course number as if it were confirmed.
   - From the combined, verified pool, judge relevance yourself and present
     only what's actually on-topic, by **name** and institution — don't
     dump raw API order, and don't auto-pick on the user's behalf either.
     `likely_has_video` is only a hint; it is not a guarantee of transcripts
     (see step 3).

2. **If the input is a course number/code, title, or URL**, resolve it directly:
   ```
   python3 "<skill-dir>/ocw_download.py" resolve "18.06"
   python3 "<skill-dir>/ocw_download.py" resolve "CS229"
   python3 "<skill-dir>/ocw_download.py" resolve "CS336"
   ```
   Show the resolved course name (and institution) and ask for a quick
   confirm before downloading. For microsite courses, `resolve` also returns
   `lectures` (video id, title, parsed lecture number) — useful to sanity
   check before a 17-video download.

3. **Download the confirmed course.** Pass the `readable_id` (MIT, best) or
   `code` (Stanford SEE / microsite) or URL of the course the user chose in
   step 1/2 — not a bare topic. Use `--dest` to control where `courses/` is
   created (default: cwd; for this repo, run it from the repo root so
   downloads land here):
   ```
   python3 "<skill-dir>/ocw_download.py" download "18.06SC+fall_2011" --dest .
   python3 "<skill-dir>/ocw_download.py" download "CS229" --dest .
   python3 "<skill-dir>/ocw_download.py" download "CS336" --dest .
   ```
   The command prints a JSON summary. **Check `transcripts_available`:**
   - `true` → report the per-folder counts to the user.
   - `false` → **warn the user** this course has no video transcripts (rare —
     every SEE/microsite course checked had transcripts for every lecture;
     some older MIT courses are notes-only), and offer to pick a different
     course or keep just the notes/psets it does have.

4. **Report** what landed, referring to the course by name **and
   institution**. Point the user at `courses/<slug>/README.md` (human index,
   now includes an `Institution:` line) and `manifest.json` (full file list
   with source URLs). Mention any `errors` count from the summary.

## Output layout

```
courses/<slug>/
  README.md            # human-readable index (institution, source, transcript status)
  manifest.json         # every file + its source URL + institution
  transcripts/         # per-lecture transcripts (PDF/caption files, kept native)
    *.txt              # cleaned plain-text version of every transcript
    other-languages/   # non-English translated captions (MIT only), kept aside
  lecture-notes/
  problem-sets/        # includes assignments + solutions
  exams/               # includes exam solutions (when present)
  other/               # uncategorized course documents
```

MIT slugs are long hyphenated titles (`18-06sc-linear-algebra-fall-2011`);
Stanford SEE and microsite slugs are short course codes (`CS229`, `CS336`) —
none of the three ever collide, so all coexist directly under `courses/` with
no extra namespacing. Microsite courses only ever populate `transcripts/`
(YouTube captions are plain text — there's no separate native format to keep
alongside a `.txt`, so `Lecture<NN>_transcript.txt` is both).

## Notes & flags

- `--force` re-downloads files that already exist (default: skip → safe re-runs).
- **MIT:** transcripts vary by course vintage — newer courses have caption
  files (`.vtt`/`.srt`), older ones have transcript PDFs per video page.
- **Stanford SEE:** transcripts are served as parallel HTML + PDF per
  lecture; the PDF is kept as the native file, the HTML is cleaned into the
  `.txt` sidecar (decoded as Windows-1252 — SEE serves smart quotes without a
  charset header, and UTF-8 mangles them).
- **Stanford SEE licensing:** materials are released under
  **Creative Commons BY-NC-SA 4.0** (NonCommercial — stricter than MIT OCW's
  terms) — mention this if the user asks about reuse.
- **Stanford microsite courses (CS336):** transcripts come from YouTube
  captions (auto-generated or uploaded) via `yttdl` — quality can vary more
  than MIT/SEE's native transcripts. Requires `uv`. Slides/assignments are
  **not** downloaded (they're typically a separate GitHub repo per course) —
  mention this gap to the user and point them at the course's own site/repo
  if they need those.
- Out of scope by design: lecture **video files**, AI-generated summaries,
  and sources outside MIT OCW / Stanford SEE / the curated microsite registry
  (e.g. Stanford Online/edX courses, or SEE's externally-hosted LOGIC course).
  Don't try to add arbitrary new sources here without extending
  `MICROSITE_CATALOG` deliberately.
- If `search` returns nothing from any source, tell the user no course
  matched — for microsite courses, also mention the registry is small and
  hand-curated (not a live search).
