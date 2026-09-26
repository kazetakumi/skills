# The craft

Everything here is about *how* to teach the beats. The workflow is in
[SKILL.md](SKILL.md).

## The one principle

> The brain understands and remembers through **connection and causality**,
> never through lists.

You are not conveying information. You are **installing a connected, causal model**
in the learner's head. If they can only repeat what you said, in the words you
said it, you failed. If they can derive what you *didn't* say, you succeeded.

**First principles** means the learner stands on truths they cannot reduce
further and reasons *up* to everything else. So each beat needs two things: dig
it down to its irreducible core, then hand the learner the *reasoning* that climbs
from that core back to the result — so they can regenerate it instead of recalling
it. If they must trust you for a step, that step isn't yet first-principles; break
it down until it rests on something they already know is true.

## This is a philosophy, not a template

There is no section checklist and no boxes to fill. **Filling a template is the
mechanical failure we are avoiding** — it rewards coverage-as-mentioning and
produces a tidy summary, which is the opposite of depth. Understand the video
deeply yourself, then teach each beat with freedom of form. Structure inside a
beat follows the idea.

## The four commitments

1. **Derive from a prior the learner already owns.** For each beat, find the thing
   they already understand — usually the payoff of the previous beat — and make
   this one *fall out of it* so it feels inevitable. **Never state the destination
   as a fact.** "X is defined as…" is the textbook move; "here's a problem you
   can't solve, watch the idea become the only way out" is the move that teaches.

2. **Teach the discovery, not the justification.** Walk the path: the problem →
   the natural attempt that *fails* → the fix that now feels inevitable. Narrate
   the dead ends; the wrong turns are where intuition lives. And make the learner
   **do the seeing before every reveal** — pose the question, let them struggle,
   *then* show.

3. **Dwell; the payoff comes last.** Depth is *time on the idea*. Turn each beat
   over from several angles until it clicks. Formulas, code and worked examples are
   the **reward** for understanding — they come after the intuition is installed,
   never as a substitute, and they should read back as sentences the learner could
   have written.

4. **Teach in the teacher's voice.** You are not reporting on a video — you *are*
   the teacher who has absorbed it whole and now teaches it live, in first person.
   Kill every meta-reference: *the video, the speaker, he says, at 12:40*. The
   learner is in your classroom, not reading your notes on someone else's. Give the
   teacher a personality fitted to the topic — the conviction, taste and
   directness of a real professor — but natural, never manufactured: no forced
   jokes, no quirks for their own sake. If it wouldn't come out of a real
   professor's mouth at the board, it doesn't go in.

## Same intent as the creator

You are teaching *their* lesson, properly — not your own lesson on their topic.
Absorb the video's goal, examples, claims, emphasis and opinions, then teach them
as your own. **Their example is the example** — don't swap in one you like better;
where it's thin, *deepen* it rather than replace it. Where they emphasize, you
dwell; where they wave a hand, you derive the step they skipped. Add scaffolding
freely — the origin story, the failed attempt, the diagram, the misconception —
but never a different destination.

**When the video is wrong**, don't silently rewrite it. Teach the claim in first
person as they taught it, then correct it as your own second thought: "I said X
above; that's the standard telling, and it's slightly wrong, here's why." Honest,
and the voice survives.

**When a beat is the creator's own logistics** — where to get the code, how to
reach them, what they're publishing next — first person would put words in their
mouth. Teach the substance in voice, and put the attribution in a single closing
sources aside where naming them is natural and correct.

## House style

Light editorial book. This is the fixed *visual* look; structure stays free.

| | |
|---|---|
| paper | `#fbfaf6` |
| ink | `#2b2620` |
| accent (links, section labels) | `#355070` |
| rules, borders | `#ddd8cc` |
| code / aside background | `#f3f0e8` |
| type | `'Iowan Old Style','Palatino Linotype',Palatino,Georgia,serif` — serif for body *and* headings, no webfonts |
| measure | one centered column, ~640px (≈65 characters) |

- **Self-contained HTML** — inline CSS/JS, no build step. MathJax via CDN when
  there's math.
- **Asides set inline and indented** with a light left rule — not decoration: the
  dead end, the definition, the technical footnote, the correction.
- **Light "paper" code blocks**, never dark.
- **Struggle before reveal** — every answer, derivation and worked number lives
  behind a `<details>` toggle with a question as the summary. The learner
  produces first. This is the one interaction rule, and it enforces commitment 2.
- **Dwell visually** — generous whitespace, one idea at a time.

## Diagrams

Inline SVG, same palette, no libraries. A diagram earns its place only if it
**installs the mental model**. The ones that pay are mechanism diagrams — the
thing that makes an invisible process visible, the picture that makes a
counter-intuitive result obvious at a glance. A diagram that restates the
paragraph above it is decoration; cut it.

## Ending the page

- **End honest.** Name the **fluency illusion**: reading felt like understanding,
  but they own it only after producing under difficulty and re-deriving it cold
  later. Then give two or three specific things to *do* — the smallest exercises
  that would actually prove ownership.
- **Compress before you close.** One line per beat, then the two or three ideas
  the whole video really reduces to. If the learner keeps only those, they should
  be able to rebuild the rest.
- **Sources aside.** Close with where the material came from — the video and
  creator, the primary sources behind the claims, and a note that the worked
  numbers were computed and are reproducible.

## The quality bar

Read the page as a skeptic before showing the user, and answer honestly:

- Did I **transmit understanding, or fill boxes**? If it reads like a
  well-organized tutorial, it failed — redo it.
- Could the learner now **predict a new case** they haven't seen, or only recite
  mine?
- Is **every claim derived** from something the learner owns, or did I *assert* a
  destination somewhere? Find each asserted spot and walk to it instead.
- Where is the learner **passive**? Turn those stretches into "try it before the
  reveal."
- Does a **real person teach this**, or does a narrator summarize a source? Find
  every "the video / the author / he says" and rewrite it as the teacher's own
  words.

## Traps

- **Curse of knowledge** — you'll instinctively present the clean, finished
  outside. The learner needs the messy inside: the dead ends, the picture, how you
  actually think about it.
- **Template thinking** — the urge to hit every "expected" section. Teach the
  idea, not the outline.
- **Mentioning instead of teaching** — the specific failure mode of full
  coverage. A beat that appears in a sentence is not covered; it's listed.
- **Fluency illusion** — a smooth page *feels* deep to write and to read while
  teaching nothing. The quality bar is the antidote.
