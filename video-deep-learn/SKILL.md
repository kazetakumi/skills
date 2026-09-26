---
name: video-deep-learn
description: Turn one YouTube video (URL, or an already-downloaded transcript) into a single self-contained HTML lesson that teaches everything in that video from first principles — in the video's own order, in the teacher's voice, with the creator's own intent and examples, nothing dropped. Fetches captions with the sibling `yttdl` skill when given a URL, verifies the video's claims by computing them, then sweeps for coverage so no beat is missed. Use when the user pastes a YouTube link or a transcript and wants to genuinely understand it rather than skim it — e.g. "explain this video", "teach me this talk", "deep dive this lecture", "turn this video into a lesson", "use video-deep-learn on <url>".
---

# Video Deep Learn

One video in → **one HTML lesson out** that teaches the whole video from first
principles, in the teacher's own voice, covering every idea the video covers.

**Read [TEACHING.md](TEACHING.md) before writing anything** — the one principle,
the four commitments, the house style, the quality bar, the traps. This file is
the workflow only.

## The five non-negotiables

1. **Scope is the whole video.** Every idea, example, aside, caveat and claim
   gets taught. Depth is not bought by cutting topics — it's bought **per beat**:
   each beat gets *derived*, not summarized.
2. **The video's progression is the spine.** One section per beat, in the
   creator's order. Reorder only where that order genuinely blocks
   understanding, and then say nothing about it — just teach the order that works.
3. **One-shot.** URL in, HTML out. No interview, no clarifying questions, no
   syllabus or progress files. Ask only if the input is broken (dead link,
   empty transcript).
4. **One self-contained HTML page** — no build step, no assets beyond CDN MathJax.
5. **Nothing missed** — guaranteed mechanically by the beat list (step 2) and
   the coverage sweep (step 5), not by good intentions.

## 1. Get the transcript

`$YTTDL` is this skill's sibling `yttdl` directory (`../yttdl` from here — both
live in the same skills folder).

```bash
uv run --project "$YTTDL" yttdl "<video-url>" -o transcripts --translate en
```

`--translate en` gets English out of almost any captioned video. Output lands in
`transcripts/<video_id>.txt`, relative to the caller's current directory.

Grab the title, creator and duration for the header from the same venv:

```bash
uv run --project "$YTTDL" python -c "
import yt_dlp, json
with yt_dlp.YoutubeDL({'quiet':True,'skip_download':True}) as y:
    i = y.extract_info('<video-url>', download=False)
print(json.dumps({k:i.get(k) for k in ('title','uploader','duration')}))"
```

**If given a transcript** (pasted text or a file path), read it and skip both
commands.

If captions are disabled there is nothing to teach from: say so and point the
user at the `watch` skill (frames and audio). Don't build a workaround.

## 2. Map the beats before writing a word

Auto-captions are an unpunctuated wall. Read the whole transcript, then write
down an explicit **beat list** — every distinct idea, example, aside, caveat,
demo and claim, in order. Scratch artifact, not a deliverable; it serves twice,
as the outline now and the coverage checklist later.

Then compress each beat: the irreducible idea, the prior it stands on, the
discovery path, the misconception that bites.

## 3. Verify the claims by computing them

**Do this before drafting, and do not skip it.** Take every number, formula and
factual claim the video makes and actually check it — run the arithmetic in
Python, re-derive the formula, search for the primary source behind a cited
study. Ground anything the transcript leaves unexplained in a real source rather
than parametric memory.

This is the step that changes the lesson most. It reliably finds errors worth
correcting, and it produces the honest tests and counter-examples that turn a
summary into teaching. Build the worked examples out of numbers you computed, so
the page is reproducible.

## 4. Write the lesson

Follow TEACHING.md. Name the file `<slug-of-title>.html` in the caller's current
directory. Open with title, creator and a link back to the video — then drop into
the teaching and never mention the video again.

Long pages are fine. Add a top-of-page contents list past a handful of beats.

## 5. Sweep for coverage, then for depth

- **Coverage sweep.** Walk the beat list against the finished page, beat by
  beat. Every beat must be *taught*, not merely mentioned. Patch each gap.
  Expect the misses to cluster in the video's last third — that is where
  attention drops and it is where they will be.
- **Quality bar.** Then run TEACHING.md's quality bar and revise before showing
  the user.

Coverage without depth is a transcript in nicer fonts. Depth without coverage
is a different lesson than the one the creator taught. This page owes both.
