---
name: video-deep-learn
description: Turn one YouTube video (URL, or an already-downloaded transcript) into a single self-contained HTML lesson that teaches everything in that video from first principles — the `deep-learn` teaching philosophy applied to full coverage of one video, in the video's own order and with the creator's own intent, nothing dropped. Fetches captions via the sibling `yttdl` skill when given a URL. Use when the user pastes a YouTube link or a transcript and wants to genuinely understand it — e.g. "explain this video", "teach me this talk", "deep dive this lecture", "turn this video into a lesson".
---

# Video Deep Learn

One video in → **one HTML lesson out** that teaches the whole video from first
principles, in the teacher's voice, covering every idea the video covers.

## Inherit the philosophy from `deep-learn`

**First, read `../deep-learn/SKILL.md`** (sibling directory of this SKILL.md)
and adopt it: the one principle (connection and causality, never lists), the
five commitments, the traps, the house style, the quality bar. That file is the
teaching craft; this file only says how it changes for a video.

Do not paste deep-learn's rules here or restate them — read them there.

## The four overrides

Deep-learn assumes a topic and a conversation. A video is a fixed artifact with
an author who already chose what matters, so four things change:

1. **Scope is the whole video, not one crux.** Deep-learn's commitment 1
   ("narrow brutally", cut everything but one crux) is **overridden**. Nothing
   in the video gets dropped. Depth is no longer bought by cutting topics —
   it's bought **per beat**: every idea the video raises gets derived, not
   summarized.

2. **The video's progression is the spine.** Build a **spine of cruxes in the
   video's own order** — one section per beat the creator actually teaches —
   and apply deep-learn's commitments *inside each*: derive it from a prior the
   learner already owns (usually the payoff of the previous beat), walk the
   discovery (problem → natural attempt that fails → the fix), make the learner
   see it before you reveal it. Reorder only where the video's order genuinely
   blocks understanding, and when you do, say nothing about it — just teach the
   order that works.

3. **No gates, no grilling.** This is one-shot: URL in, HTML out. Skip
   deep-learn's Gate 1 and Gate 2 entirely — the video's own level and its own
   goal stand in for the interview. Ask the user nothing unless the input itself
   is broken (dead link, empty transcript).

4. **No syllabus state.** `syllabus.json`, `lessons/`, `index.html`, statuses,
   the notes array — none of it applies. One page, no state machine.

## Same intent as the creator

You are teaching *their* lesson, properly — not your own lesson on their topic.
Absorb the video's goal, its examples, its claims, its emphasis, its opinions
and asides, then teach them **in first person** (deep-learn's commitment 5
stands: never "the speaker says", "the video explains", "at 12:40 he"). Their
example is the example — don't swap in one you like better; where their example
is thin, *deepen* it rather than replace it. Where they emphasize, you dwell;
where they wave a hand, you derive the step they skipped. Add your own
scaffolding freely — the origin story, the failed attempt, the diagram, the
misconception — but never a different destination.

If the video makes a claim you know to be wrong, don't silently rewrite it:
teach the claim in first person as they taught it, then correct it in an aside as
your own second thought — "I said X above; that's the standard telling, and it's
slightly wrong, here's why" — which keeps the correction honest without breaking
voice.

## 1. Get the transcript

**If given a URL** — use the sibling `yttdl` skill. `$YTTDL` below is the
absolute path to this skill's sibling `yttdl` directory (`../yttdl` from this
SKILL.md; both live under the same skills folder):

```bash
uv run --project "$YTTDL" yttdl "<video-url>" -o transcripts --translate en
```

`--translate en` is the default choice — it gets English out of almost any
captioned video (see `$YTTDL/SKILL.md`). Output lands in `transcripts/<video_id>.txt`
relative to the caller's current directory.

If captions are disabled, the video yields nothing to teach from: say so and
point the user at the `watch` skill, which reads frames and audio. Don't build a
workaround.

**If given a transcript** (pasted text, or a file path) — read it and skip the
download entirely.

Also fetch the **title, creator, and URL** for the lesson header. Then, if the
transcript leaves a claim, term, or derivation genuinely unexplained, look it up
on the web — deep-learn's "ground every claim in a source, never parametric
memory" applies here too. The transcript is the spine, not the ceiling.

## 2. Map the beats before writing a word

Auto-captions are an unpunctuated wall. Before teaching, segment the transcript
into an explicit **beat list** — every distinct idea, example, aside, caveat,
demo, and claim, in order. Write it down (scratch file or your own notes; it is
not a deliverable). This list is both the outline and, later, the coverage
checklist.

Then compress each beat the deep-learn way: what's the irreducible idea, what
prior does it stand on, what's the discovery path, what misconception bites
here. Only then write.

## 3. Write the lesson

One **self-contained HTML file** — inline CSS/JS, no build step, MathJax via
CDN if there's math — in deep-learn's house style (warm paper `#fbfaf6`, ink
`#2b2620`, system serif, single ~640px column, muted accent `#355070`, light
code blocks, asides inline with a left rule, `<details>` for every reveal so
the learner produces before they're told).

Name it from the video: `<slug-of-title>.html` in the caller's current
directory. Open with the video's title, creator, and a link back to it — then
drop into the teaching and never mention the video again.

Long videos make long pages; that is fine. Give the page a sticky or top-of-page
contents list once it runs past a handful of beats, so the spine is visible.

## 4. Sweep for coverage, then for depth

Two passes, in this order — the first is unique to this skill, the second is
inherited:

- **Coverage sweep.** Walk the beat list from step 2 against the finished HTML,
  beat by beat. Every beat must be *taught*, not merely mentioned. Patch each
  gap. This is the "don't miss anything" guarantee, and it's mechanical on
  purpose — you will otherwise lose the last third of a long video.
- **Quality bar.** Now run deep-learn's quality bar on the whole page: did I
  transmit understanding or fill boxes, could the learner predict a new case,
  is every claim derived rather than asserted, where is the learner passive,
  does a real person teach this. Revise before showing the user.

Coverage without depth is a transcript with nicer fonts. Depth without coverage
is a different skill (`deep-learn`). This page owes the learner both.
