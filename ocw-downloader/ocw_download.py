#!/usr/bin/env python3
"""
Multi-institution OpenCourseWare downloader — MIT OpenCourseWare + Stanford
Engineering Everywhere (SEE).

MIT: uses the MIT Learn API (https://api.learn.mit.edu) to resolve a course
from a topic, a course number/title, or a direct OCW URL.
SEE: has no API — its ~9-course catalog is hardcoded (SEE_CATALOG) and each
course's materials are discovered by scraping its course page
(see.stanford.edu/Course/<CODE>).

Both institutions download into the same organized folder shape:
video transcripts, lecture notes, problem sets, and exams.

Subcommands
-----------
  search   <query>              List ranked candidate courses from BOTH
                                 institutions, tagged by institution (JSON).
  resolve  <query|code|number|url>  Resolve a single best-match course (JSON).
  download <query|code|number|url>  Download a course's materials to disk.

Video files (.mp4) and images are intentionally skipped — transcripts stand in
for the video. See .wayfinder/assets/00{1,2}-*.md and
.wayfinder/assets/stanford-001-*.md for the researched contract.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

API = "https://api.learn.mit.edu"
OCW = "https://ocw.mit.edu"
UA = "ocw-downloader/1.0 (+https://ocw.mit.edu)"

SEE = "https://see.stanford.edu"

# SEE has no search API and a small, fixed catalog — hardcoded per
# .wayfinder/assets/stanford-001-see-structure.md (verified 2026-07-25).
# The 10th listed course, LOGIC, is hosted externally (intrologic.stanford.edu)
# under different licensing and is intentionally excluded (see map's Out of scope).
SEE_CATALOG = [
    {"code": "CS106A", "title": "Programming Methodology", "dept": "Introduction to Computer Science", "instructor": "Mehran Sahami"},
    {"code": "CS106B", "title": "Programming Abstractions", "dept": "Introduction to Computer Science", "instructor": "Julie Zelenski"},
    {"code": "CS107", "title": "Programming Paradigms", "dept": "Introduction to Computer Science", "instructor": "Jerry Cain"},
    {"code": "CS223A", "title": "Introduction to Robotics", "dept": "Artificial Intelligence", "instructor": "Oussama Khatib"},
    {"code": "CS229", "title": "Machine Learning", "dept": "Artificial Intelligence", "instructor": "Andrew Ng"},
    {"code": "EE261", "title": "The Fourier Transform and its Applications", "dept": "Linear Systems and Optimization", "instructor": "Brad G Osgood"},
    {"code": "EE263", "title": "Introduction to Linear Dynamical Systems", "dept": "Linear Systems and Optimization", "instructor": "Stephen Boyd"},
    {"code": "EE364A", "title": "Convex Optimization I", "dept": "Linear Systems and Optimization", "instructor": "Stephen Boyd"},
    {"code": "EE364B", "title": "Convex Optimization II", "dept": "Linear Systems and Optimization", "instructor": "Stephen Boyd"},
]

# Individual Stanford course microsites (not SEE, not Stanford Online) — each
# course is its own bespoke site with no shared catalog/API, so this is a
# hand-curated registry, one entry per course, extended as courses are added.
# Transcripts come from YouTube captions via the vendored `yttdl` tool (needs
# `uv`); slides/assignments (often on GitHub, per-course structure) are
# intentionally NOT fetched here — out of scope for this first pass.
YTTDL_DIR = Path(__file__).resolve().parent / "yttdl"

MICROSITE_CATALOG = [
    {
        "code": "CS336",
        "title": "Language Modeling from Scratch",
        "dept": "Natural Language Processing",
        "instructor": "Tatsunori Hashimoto, Percy Liang",
        "course_url": "https://cs336.stanford.edu/spring2025",
        "youtube_playlist": "https://www.youtube.com/playlist?list=PLoROMvodv4rOY23Y0BoGoBGgQ1zmU_MT_",
    },
]

CAPTION_EXTS = {".vtt", ".srt", ".webvtt"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".svg"}
SKIP_EXTS = {".mp4", ".m4v", ".mov"} | IMAGE_EXTS

# feature-type -> folder. Extension/title fallbacks handle the rest.
FEATURE_FOLDER = {
    "Lecture Notes": "lecture-notes",
    "Readings": "lecture-notes",
    "Problem Sets": "problem-sets",
    "Problem Set Solutions": "problem-sets",
    "Assignments": "problem-sets",
    "Written Assignments": "problem-sets",
    "Exams": "exams",
    "Exam Solutions": "exams",
}


# --------------------------------------------------------------------------- #
# HTTP helpers
# --------------------------------------------------------------------------- #
def _get(url: str, *, tries: int = 3, as_json: bool = False):
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = resp.read()
            return json.loads(data) if as_json else data
        except Exception as exc:  # noqa: BLE001 - retry any transient failure
            last = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"GET failed after {tries} tries: {url}\n  {last}")


def _api(path: str, **params) -> dict:
    qs = urllib.parse.urlencode(params)
    return _get(f"{API}{path}?{qs}", as_json=True)


# --------------------------------------------------------------------------- #
# Resolution (topic / number / url  ->  course record)
# --------------------------------------------------------------------------- #
def _slug_from_url(text: str) -> str | None:
    m = re.search(r"ocw\.mit\.edu/courses/([^/?#]+)", text)
    return m.group(1) if m else None


def _summarize(course: dict, *, has_video: bool | None = None) -> dict:
    runs = course.get("runs") or [{}]
    run = runs[0]
    cf = course.get("course_feature") or []
    return {
        "institution": "MIT",
        "readable_id": course.get("readable_id"),
        "title": course.get("title"),
        "url": course.get("url"),
        "slug": _slug_from_url(course.get("url") or ""),
        "year": run.get("year"),
        "run_id": run.get("id"),
        "course_feature": cf,
        # Light search-time signal only. Authoritative check is post-enumeration.
        "likely_has_video": ("Lecture Videos" in cf) if has_video is None else has_video,
    }


# A bare MIT course number, e.g. "18.06", "6.006", "24.200", "18.06SC", "21G".
_NUMBER_RE = re.compile(r"^\d+[A-Za-z]*(\.\w+)?$")


def _course_number(readable_id: str | None) -> str:
    return (readable_id or "").split("+", 1)[0]


def search_courses(query: str, limit: int = 8) -> list[dict]:
    # API relevance order is authoritative for topic search — do NOT reorder it.
    data = _api(
        "/api/v1/learning_resources_search/",
        q=query,
        platform="ocw",
        resource_type="course",
        limit=limit,
    )
    return [_summarize(c) for c in data.get("results", [])]


def resolve_course(target: str) -> dict:
    """Return one best-match course summary for a number, title, url, or topic."""
    slug = _slug_from_url(target)
    if slug:
        # Direct URL: match the search hit whose url contains the slug.
        words = slug.replace("-", " ")
        for c in search_courses(words, limit=12):
            if c["slug"] == slug:
                return c
        # Fallback: synthesize from the slug even if search misses.
        return {"readable_id": None, "title": slug, "url": f"{OCW}/courses/{slug}/",
                "slug": slug, "year": None, "run_id": None, "course_feature": [],
                "likely_has_video": None}

    # Exact readable_id (e.g. "18.06+fall_2011")
    if "+" in target:
        data = _api("/api/v1/courses/", readable_id=target)
        if data.get("results"):
            return _summarize(data["results"][0])

    hits = search_courses(target, limit=12)
    if not hits:
        raise SystemExit(json.dumps({"error": "no_match", "query": target}))

    # Bare course number: prefer an exact course-number match over text relevance
    # (search for "18.06" otherwise ranks "18.102" et al. above it).
    if _NUMBER_RE.match(target.strip()):
        want = target.strip().upper()
        exact = [c for c in hits if _course_number(c["readable_id"]).upper() == want]
        if exact:
            return _prefer_video(exact)
        prefix = [c for c in hits
                  if _course_number(c["readable_id"]).upper().startswith(want)
                  and not _course_number(c["readable_id"])[len(want):len(want) + 1].isdigit()]
        if prefix:
            return _prefer_video(prefix)

    return hits[0]


def _prefer_video(cands: list[dict]) -> dict:
    """Among equally-matched course-number variants, favor one likely to have video."""
    cands = sorted(cands, key=lambda c: (not c["likely_has_video"], -(c["year"] or 0)))
    return cands[0]


# --------------------------------------------------------------------------- #
# Stanford Engineering Everywhere (SEE) — resolution
#
# No API: the catalog is the hardcoded SEE_CATALOG, and a course's material
# slug / transcript-filename title aren't derivable from its code — both must
# be scraped from the course page itself. See
# .wayfinder/assets/stanford-001-see-structure.md.
# --------------------------------------------------------------------------- #
_SEE_CODES = {c["code"] for c in SEE_CATALOG}

# /materials/<slug>/transcripts/<CamelTitle>-Lecture<NN>.html — the one
# predictable pattern SEE exposes; scraping it off the course page yields the
# materials slug, the transcript-filename title, AND which lecture numbers
# actually have transcripts, all in one pass (no guessing, no probing).
_SEE_TRANSCRIPT_RE = re.compile(
    r"/materials/([a-z0-9]+)/transcripts/([A-Za-z0-9]+)-Lecture(\d+)\.html", re.I
)


def _see_summarize(entry: dict) -> dict:
    return {
        "institution": "Stanford SEE",
        "code": entry["code"],
        "title": entry["title"],
        "dept": entry["dept"],
        "instructor": entry["instructor"],
        "url": f"{SEE}/Course/{entry['code']}",
        "slug": entry["code"],
        "likely_has_video": True,  # verified true for every SEE course sampled
    }


def see_search_courses(query: str, limit: int = 8) -> list[dict]:
    """Substring match against the fixed catalog — SEE has no ranked search."""
    words = [w for w in query.lower().split() if w]
    hits = []
    for c in SEE_CATALOG:
        hay = f"{c['code']} {c['title']} {c['dept']} {c['instructor']}".lower()
        if any(w in hay for w in words) or query.lower() in hay:
            hits.append(_see_summarize(c))
    return hits[:limit]


def _see_code_from_target(target: str) -> str | None:
    m = re.search(r"see\.stanford\.edu/Course/([A-Za-z0-9]+)", target, re.I)
    if m:
        code = m.group(1).upper()
        return code if code in _SEE_CODES else None
    t = target.strip().upper()
    return t if t in _SEE_CODES else None


def _see_scan_page(html: str) -> tuple[str | None, str | None, list[int]]:
    """From a course page's HTML, pull (materials_slug, title_camel, lecture#s)."""
    matches = _SEE_TRANSCRIPT_RE.findall(html)
    if not matches:
        return None, None, []
    mslug, ctitle = matches[0][0], matches[0][1]
    numbers = sorted({int(n) for _, _, n in matches})
    return mslug, ctitle, numbers


def see_resolve_course(target: str) -> dict:
    """Return one course summary, enriched with scraped materials slug/title."""
    code = _see_code_from_target(target)
    if not code:
        hits = see_search_courses(target, limit=1)
        if not hits:
            raise SystemExit(json.dumps(
                {"error": "no_match", "query": target, "institution": "Stanford SEE"}))
        code = hits[0]["code"]
    entry = next(c for c in SEE_CATALOG if c["code"] == code)
    summary = _see_summarize(entry)
    html = _get(summary["url"]).decode("utf-8", "replace")
    mslug, ctitle, lecture_numbers = _see_scan_page(html)
    summary.update({
        "materials_slug": mslug,
        "title_camel": ctitle,
        "lecture_numbers": lecture_numbers,
        "transcripts_available": bool(lecture_numbers),
    })
    return summary


# --------------------------------------------------------------------------- #
# Stanford course microsites (e.g. CS336) — transcripts via vendored `yttdl`
# --------------------------------------------------------------------------- #
_MICROSITE_CODES = {c["code"] for c in MICROSITE_CATALOG}
_LECTURE_NUM_RE = re.compile(r"lec(?:ture)?\.?\s*(\d+)", re.I)


def _microsite_summarize(entry: dict) -> dict:
    return {
        "institution": "Stanford (course site)",
        "code": entry["code"],
        "title": entry["title"],
        "dept": entry["dept"],
        "instructor": entry["instructor"],
        "url": entry["course_url"],
        "slug": entry["code"],
        "likely_has_video": True,
    }


def microsite_search_courses(query: str, limit: int = 8) -> list[dict]:
    words = [w for w in query.lower().split() if w]
    hits = []
    for c in MICROSITE_CATALOG:
        hay = f"{c['code']} {c['title']} {c['dept']} {c['instructor']}".lower()
        if any(w in hay for w in words) or query.lower() in hay:
            hits.append(_microsite_summarize(c))
    return hits[:limit]


def _microsite_playlist_entries(playlist_url: str) -> list[tuple[str, str]]:
    """[(video_id, title), ...] via the vendored yt-dlp, run through its own uv env."""
    script = (
        "import yt_dlp, json\n"
        "with yt_dlp.YoutubeDL({'quiet': True, 'extract_flat': True}) as ydl:\n"
        f"    info = ydl.extract_info({playlist_url!r}, download=False)\n"
        "    print(json.dumps([[e['id'], e['title']] for e in (info.get('entries') or []) if e]))\n"
    )
    out = subprocess.run(
        ["uv", "run", "--project", str(YTTDL_DIR), "python3", "-c", script],
        capture_output=True, text=True, timeout=120,
    )
    if out.returncode != 0:
        raise RuntimeError(f"playlist enumeration failed: {out.stderr[-500:]}")
    return [tuple(x) for x in json.loads(out.stdout)]


def microsite_resolve_course(target: str) -> dict:
    code = target.strip().upper()
    entry = next((c for c in MICROSITE_CATALOG if c["code"] == code), None)
    if not entry:
        hits = microsite_search_courses(target, limit=1)
        if not hits:
            raise SystemExit(json.dumps(
                {"error": "no_match", "query": target, "institution": "Stanford (course site)"}))
        entry = next(c for c in MICROSITE_CATALOG if c["code"] == hits[0]["code"])
    summary = _microsite_summarize(entry)
    lectures = []
    for vid, vtitle in _microsite_playlist_entries(entry["youtube_playlist"]):
        m = _LECTURE_NUM_RE.search(vtitle)
        lectures.append({"video_id": vid, "title": vtitle, "number": int(m.group(1)) if m else None})
    summary["lectures"] = lectures
    summary["transcripts_available"] = bool(lectures)
    return summary


def microsite_download_course(target: str, dest_root: Path, *, force: bool = False) -> dict:
    course = microsite_resolve_course(target)
    course_dir = dest_root / "courses" / course["code"]
    transcripts_dir = course_dir / "transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)

    manifest = {"course": course, "counts": {}, "transcripts_available": False,
                "downloaded": [], "skipped_video": 0, "errors": []}
    counts: dict[str, int] = {}

    for lec in course["lectures"]:
        manifest["skipped_video"] += 1  # video itself is out of scope, as elsewhere
        nn = f"{lec['number']:02d}" if lec["number"] else lec["video_id"]
        fname = f"Lecture{nn}_transcript.txt"
        out_path = transcripts_dir / fname
        if out_path.exists() and not force:
            counts["transcripts"] = counts.get("transcripts", 0) + 1
            continue
        result = subprocess.run(
            ["uv", "run", "--project", str(YTTDL_DIR), "yttdl", lec["video_id"],
             "-o", str(transcripts_dir), "-q"],
            capture_output=True, text=True, timeout=180,
        )
        fetched = transcripts_dir / f"{lec['video_id']}.txt"
        if result.returncode != 0 or not fetched.exists():
            manifest["errors"].append({
                "title": lec["title"],
                "reason": (result.stderr.strip()[-300:] or "yttdl failed"),
                "url": f"https://www.youtube.com/watch?v={lec['video_id']}",
            })
            continue
        fetched.rename(out_path)
        counts["transcripts"] = counts.get("transcripts", 0) + 1
        manifest["downloaded"].append({
            "folder": "transcripts", "file": str(out_path.relative_to(dest_root)),
            "title": lec["title"], "source": f"https://www.youtube.com/watch?v={lec['video_id']}",
        })

    manifest["counts"] = counts
    manifest["transcripts_available"] = counts.get("transcripts", 0) > 0
    course_dir.mkdir(parents=True, exist_ok=True)
    (course_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    _write_readme(course_dir, {
        "title": course["title"], "year": None, "url": course["url"],
        "institution": course["institution"], "code": course["code"],
    }, manifest["counts"], manifest)
    return manifest


# --------------------------------------------------------------------------- #
# Cross-institution dispatch
# --------------------------------------------------------------------------- #
def combined_search(query: str, limit: int = 8) -> list[dict]:
    """MIT's API hits (query-driven — its catalog is too large to dump whole)
    plus the ENTIRE SEE and microsite catalogs, unfiltered.

    SEE (9 courses) and the microsite registry (currently 1) are small enough
    that keyword/substring filtering does more harm than good: a course whose
    title doesn't literally contain the query word (e.g. "transformers" vs.
    "Machine Learning") would otherwise never appear, even when it's exactly
    what's relevant. Returning them whole and letting the caller (an LLM)
    judge relevance semantically is strictly better at this scale than any
    substring heuristic — see SKILL.md's search guidance.
    """
    return (search_courses(query, limit)
            + [_see_summarize(c) for c in SEE_CATALOG]
            + [_microsite_summarize(c) for c in MICROSITE_CATALOG])


def _is_see_target(target: str) -> bool:
    return bool(_see_code_from_target(target)) or "see.stanford.edu" in target.lower()


def _is_microsite_target(target: str) -> bool:
    return target.strip().upper() in _MICROSITE_CODES


def resolve_any(target: str) -> dict:
    if _is_microsite_target(target):
        return microsite_resolve_course(target)
    if _is_see_target(target):
        return see_resolve_course(target)
    return resolve_course(target)


def download_any(target: str, dest_root: Path, *, force: bool = False) -> dict:
    if _is_microsite_target(target):
        return microsite_download_course(target, dest_root, force=force)
    if _is_see_target(target):
        return see_download_course(target, dest_root, force=force)
    return download_course(target, dest_root, force=force)


# --------------------------------------------------------------------------- #
# Enumeration + categorization
# --------------------------------------------------------------------------- #
def list_contentfiles(run_id: int) -> list[dict]:
    out, offset = [], 0
    while True:
        data = _api("/api/v1/contentfiles/", run_id=run_id, limit=100, offset=offset)
        batch = data.get("results", [])
        if not batch:
            break
        out.extend(batch)
        offset += 100
        if offset >= data.get("count", 0):
            break
    return out


def _is_transcript(cf: dict, ext: str) -> bool:
    if ext in CAPTION_EXTS:
        return True
    name = f"{cf.get('title','')} {cf.get('url','')} {cf.get('key','')}".lower()
    return ext == ".pdf" and "transcript" in name


def categorize(cf: dict) -> str | None:
    """Return the destination folder, or None to skip this file."""
    ext = (cf.get("file_extension") or "").lower()
    if ext in SKIP_EXTS:
        return None
    if _is_transcript(cf, ext):
        return "transcripts"
    for feat in cf.get("content_feature_type") or []:
        if feat in FEATURE_FOLDER:
            return FEATURE_FOLDER[feat]
    if ext in (".pdf", ".m", ".txt", ".docx", ".xlsx", ".zip"):
        return "other"
    return None


# --------------------------------------------------------------------------- #
# Raw file URL discovery (scrape resource page)
# --------------------------------------------------------------------------- #
class _HrefCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for k, v in attrs:
                if k == "href" and v:
                    self.hrefs.append(v)


def raw_file_url(cf: dict) -> str | None:
    """Find the direct file URL by scraping the resource page for the matching href."""
    page = cf.get("url")
    ext = (cf.get("file_extension") or "").lower()
    if not page or not ext:
        return None
    try:
        html = _get(page).decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        return None
    parser = _HrefCollector()
    parser.feed(html)
    # candidate hrefs that point at a real file with our extension
    cands = [h for h in parser.hrefs if h.lower().split("?")[0].endswith(ext)]
    if not cands:
        return None
    # Prefer the href whose basename maps to this contentfile's key slug.
    key_slug = (cf.get("key") or "").rstrip("/").split("/")[-1].lower()
    best = None
    for h in cands:
        base = h.split("?")[0].rsplit("/", 1)[-1].lower()
        stem = base.rsplit(".", 1)[0]
        if key_slug and (stem in key_slug or key_slug in stem or stem.replace("_", "") in key_slug):
            best = h
            break
    href = best or cands[0]
    if href.startswith("//"):
        return "https:" + href
    if href.startswith("/"):
        return OCW + href
    return href


# --------------------------------------------------------------------------- #
# Transcript cleanup (caption -> readable .txt)
# --------------------------------------------------------------------------- #
def is_latin_text(text: str, threshold: float = 0.6) -> bool:
    """True if the transcript is predominantly Latin script (English et al.).

    OCW ships some translated caption files (Chinese, etc.) that the API does
    not language-tag, so we infer from the content and default to English.
    """
    alpha = [ch for ch in text if ch.isalpha()]
    if len(alpha) < 20:
        return True  # too little signal — keep it rather than mis-drop
    ascii_letters = sum(1 for ch in alpha if "a" <= ch.lower() <= "z")
    return (ascii_letters / len(alpha)) >= threshold


def caption_to_text(raw: bytes) -> str:
    lines = raw.decode("utf-8", "replace").splitlines()
    out, seen_blank = [], False
    for ln in lines:
        s = ln.strip()
        if s in ("WEBVTT",) or s.isdigit():
            continue
        if "-->" in s:  # timestamp cue line
            continue
        if not s:
            seen_blank = True
            continue
        s = re.sub(r"<[^>]+>", "", s)  # strip inline tags
        if out and seen_blank:
            out.append("")
        out.append(s)
        seen_blank = False
    # collapse >1 blank lines
    text = "\n".join(out)
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"


# --------------------------------------------------------------------------- #
# Download orchestration
# --------------------------------------------------------------------------- #
VIDEO_EXTS = {".mp4", ".m4v", ".mov"}


def _safe_name(cf: dict, href: str) -> str:
    base = href.split("?")[0].rsplit("/", 1)[-1]
    base = urllib.parse.unquote(base)
    return re.sub(r"[^\w.\-]+", "_", base)


def _abs_url(href: str) -> str:
    if href.startswith("//"):
        return "https:" + href
    if href.startswith("/"):
        return OCW + href
    return href


def video_page_transcripts(page_url: str, youtube_id: str | None) -> list[str]:
    """Scrape a lecture-video resource page for its transcript/caption file URLs.

    OCW does not index per-video transcripts as separate contentfiles — the
    English transcript lives on the video's own page as `<hash>_<youtube_id>.pdf`
    (and sometimes a caption file). Without this, the core deliverable is missed.
    """
    try:
        html = _get(page_url).decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        return []
    parser = _HrefCollector()
    parser.feed(html)
    out, seen = [], set()
    for h in parser.hrefs:
        base = h.lower().split("?")[0].rsplit("/", 1)[-1]
        ext = "." + base.rsplit(".", 1)[-1] if "." in base else ""
        keep = ext in CAPTION_EXTS or (
            ext == ".pdf" and youtube_id and youtube_id.lower() in base
        )
        if keep:
            u = _abs_url(h)
            if u not in seen:
                seen.add(u)
                out.append(u)
    return out


def _existing_sub(course_dir: Path, folder: str, fname: str) -> str | None:
    """Return the sub-path a file already lives in (base or other-languages), else None."""
    if (course_dir / folder / fname).exists():
        return folder
    if (course_dir / folder / "other-languages" / fname).exists():
        return f"{folder}/other-languages"
    return None


def _store(blob: bytes, *, course_dir: Path, dest_root: Path, folder: str, fname: str,
           title: str | None, source: str, manifest: dict, counts: dict,
           caption_text: str | None) -> None:
    """Write a file (routing non-English captions aside) and record it."""
    sub = folder
    if caption_text is not None and folder == "transcripts" and not is_latin_text(caption_text):
        sub = f"{folder}/other-languages"
    out_dir = course_dir / sub
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / fname
    out_path.write_bytes(blob)
    counts[sub] = counts.get(sub, 0) + 1  # tally by actual location, not the base folder
    record = {"folder": sub, "file": str(out_path.relative_to(dest_root)),
              "title": title, "source": source}
    if caption_text is not None:  # emit a cleaned plain-text version
        txt = out_path.with_suffix(".txt")
        try:
            txt.write_text(caption_text, encoding="utf-8")
            record["plain_text"] = str(txt.relative_to(dest_root))
        except Exception:  # noqa: BLE001
            pass
    if folder == "transcripts" and sub == "transcripts":
        manifest["transcripts_available"] = True
    manifest["downloaded"].append(record)


def download_course(target: str, dest_root: Path, *, force: bool = False) -> dict:
    course = resolve_course(target)
    if not course.get("run_id"):
        raise SystemExit(json.dumps(
            {"error": "unresolved_run", "course": course,
             "hint": "Could not find a Learn API run id for this course."}, indent=2))

    slug = course["slug"] or re.sub(r"[^\w\-]+", "-", course["title"].lower())
    course_dir = dest_root / "courses" / slug
    files = list_contentfiles(course["run_id"])

    manifest = {
        "course": course,
        "counts": {},
        "transcripts_available": False,
        "downloaded": [],
        "skipped_video": 0,
        "errors": [],
    }
    counts: dict[str, int] = {}

    # --- Pass 1: video pages -> grab per-video transcripts, skip the video files.
    seen_pages: set[str] = set()
    for cf in files:
        if (cf.get("file_extension") or "").lower() not in VIDEO_EXTS:
            continue
        manifest["skipped_video"] += 1
        page, yt = cf.get("url"), cf.get("youtube_id")
        if not page or page in seen_pages:
            continue
        seen_pages.add(page)
        title = cf.get("title") or "video"
        stem = re.sub(r"[^\w.\-]+", "_", title)[:80].strip("_") or "video"
        for turl in video_page_transcripts(page, yt):
            ext = Path(turl.split("?")[0]).suffix.lower()
            is_cap = ext in CAPTION_EXTS
            fname = f"{stem}{ext}" if is_cap else f"{stem}_transcript.pdf"
            existing = None if force else _existing_sub(course_dir, "transcripts", fname)
            if existing:
                counts[existing] = counts.get(existing, 0) + 1
                if existing == "transcripts":
                    manifest["transcripts_available"] = True
                continue
            try:
                blob = _get(turl)
            except Exception as exc:  # noqa: BLE001
                manifest["errors"].append({"title": title, "reason": str(exc), "url": turl})
                continue
            _store(blob, course_dir=course_dir, dest_root=dest_root, folder="transcripts",
                   fname=fname, title=title, source=turl, manifest=manifest, counts=counts,
                   caption_text=caption_to_text(blob) if is_cap else None)

    # --- Pass 2: non-video files (notes, psets, exams, standalone transcripts).
    for cf in files:
        if (cf.get("file_extension") or "").lower() in VIDEO_EXTS:
            continue
        folder = categorize(cf)
        if folder is None:
            continue
        href = raw_file_url(cf)
        if not href:
            manifest["errors"].append({"title": cf.get("title"), "reason": "no_raw_url",
                                        "page": cf.get("url")})
            continue
        fname = _safe_name(cf, href)
        existing = None if force else _existing_sub(course_dir, folder, fname)
        if existing:
            counts[existing] = counts.get(existing, 0) + 1
            if existing == "transcripts":
                manifest["transcripts_available"] = True
            continue
        try:
            blob = _get(href)
        except Exception as exc:  # noqa: BLE001
            manifest["errors"].append({"title": cf.get("title"), "reason": str(exc), "url": href})
            continue
        is_caption = folder == "transcripts" and Path(fname).suffix.lower() in CAPTION_EXTS
        _store(blob, course_dir=course_dir, dest_root=dest_root, folder=folder, fname=fname,
               title=cf.get("title"), source=href, manifest=manifest, counts=counts,
               caption_text=caption_to_text(blob) if is_caption else None)

    # Report counts from what is actually on disk — the loop counters can double
    # count when duplicate video pages reference the same already-saved transcript.
    counts = _folder_counts(course_dir)
    manifest["counts"] = counts
    manifest["transcripts_available"] = counts.get("transcripts", 0) > 0
    course_dir.mkdir(parents=True, exist_ok=True)
    (course_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    _write_readme(course_dir, course, counts, manifest)
    return manifest


# --------------------------------------------------------------------------- #
# SEE download orchestration
# --------------------------------------------------------------------------- #
class _SeeTranscriptText(HTMLParser):
    """SEE transcript HTML is bare <p>-separated prose (no head/body wrapper)."""

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "p":
            self.parts.append("\n\n")

    def handle_data(self, data):
        self.parts.append(data)


def see_transcript_html_to_text(raw: bytes) -> str:
    # SEE serves these as Windows-1252 (smart quotes etc.) with no charset
    # header — decoding as UTF-8 mangles apostrophes into replacement chars.
    parser = _SeeTranscriptText()
    parser.feed(raw.decode("cp1252", "replace"))
    text = "".join(parser.parts)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"[ \t]*\n[ \t]*", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def _abs_url_see(href: str) -> str:
    if href.startswith("//"):
        return "https:" + href
    if href.startswith("/"):
        return SEE + href
    return href


# Filename keyword heuristics, verified against real hrefs from 4 SEE courses
# (.wayfinder/assets/stanford-001-see-structure.md) — SEE has no per-file
# category metadata (unlike MIT's `content_feature_type`), so this mirrors
# MIT's own extension/title fallback in `categorize()`.
_SEE_EXAM_RE = re.compile(r"exam|midterm|final")
_SEE_PSET_RE = re.compile(r"assignment|homework|section|problemset|problem-set|\bhw\d|\bps\d")


def _see_categorize(url: str) -> str | None:
    fname = url.split("?")[0].rsplit("/", 1)[-1]
    name = fname.lower()
    ext = Path(fname).suffix.lower()
    if "allmaterials.zip" in name or ext in SKIP_EXTS:
        return None  # redundant bundle (per-file is the chosen strategy) / video
    if _SEE_EXAM_RE.search(name):
        return "exams"
    if _SEE_PSET_RE.search(name):
        return "problem-sets"
    if ext == ".pdf":
        return "lecture-notes"
    if ext in (".zip", ".m", ".txt", ".docx", ".xlsx"):
        return "other"
    return None


def see_download_course(target: str, dest_root: Path, *, force: bool = False) -> dict:
    course = see_resolve_course(target)
    if not course.get("materials_slug") or not course.get("title_camel"):
        raise SystemExit(json.dumps(
            {"error": "unresolved_materials", "course": course}, indent=2))

    slug = course["code"]
    course_dir = dest_root / "courses" / slug
    mslug, ctitle = course["materials_slug"], course["title_camel"]

    manifest = {
        "course": course,
        "counts": {},
        "transcripts_available": False,
        "downloaded": [],
        "skipped_video": 0,
        "errors": [],
    }
    counts: dict[str, int] = {}

    # --- Pass 1: per-lecture transcripts. PDF kept as the native file (mirrors
    # MIT's PDF-transcript-era courses); HTML is fetched only to derive the
    # cleaned .txt sidecar (mirrors MIT's caption -> .txt cleanup).
    for i in course["lecture_numbers"]:
        manifest["skipped_video"] += 1  # one mp4 per lecture — out of scope
        nn = f"{i:02d}"
        pdf_url = f"{SEE}/materials/{mslug}/transcripts/{ctitle}-Lecture{nn}.pdf"
        html_url = f"{SEE}/materials/{mslug}/transcripts/{ctitle}-Lecture{nn}.html"
        fname = f"Lecture{nn}_transcript.pdf"
        existing = None if force else _existing_sub(course_dir, "transcripts", fname)
        if existing:
            counts[existing] = counts.get(existing, 0) + 1
            if existing == "transcripts":
                manifest["transcripts_available"] = True
            continue
        try:
            pdf_blob = _get(pdf_url)
        except Exception as exc:  # noqa: BLE001
            manifest["errors"].append(
                {"title": f"Lecture {nn} transcript", "reason": str(exc), "url": pdf_url})
            continue
        caption_text = None
        try:
            caption_text = see_transcript_html_to_text(_get(html_url))
        except Exception:  # noqa: BLE001
            pass  # PDF alone still counts as a transcript; .txt sidecar is a bonus
        _store(pdf_blob, course_dir=course_dir, dest_root=dest_root, folder="transcripts",
               fname=fname, title=f"Lecture {i}", source=pdf_url, manifest=manifest,
               counts=counts, caption_text=caption_text)

    # --- Pass 2: everything else linked from the course page (handouts, notes,
    # problem sets, exams). SEE serves these as plain static links — no API.
    page_html = _get(course["url"]).decode("utf-8", "replace")
    parser = _HrefCollector()
    parser.feed(page_html)
    seen: set[str] = set()
    for h in parser.hrefs:
        u = _abs_url_see(h)
        if f"/materials/{mslug}/" not in u or "/transcripts/" in u or u in seen:
            continue
        seen.add(u)
        folder = _see_categorize(u)
        if folder is None:
            continue
        fname = re.sub(r"[^\w.\-]+", "_", urllib.parse.unquote(u.split("?")[0].rsplit("/", 1)[-1]))
        existing = None if force else _existing_sub(course_dir, folder, fname)
        if existing:
            counts[existing] = counts.get(existing, 0) + 1
            continue
        try:
            blob = _get(u)
        except Exception as exc:  # noqa: BLE001
            manifest["errors"].append({"title": fname, "reason": str(exc), "url": u})
            continue
        _store(blob, course_dir=course_dir, dest_root=dest_root, folder=folder, fname=fname,
               title=fname, source=u, manifest=manifest, counts=counts, caption_text=None)

    counts = _folder_counts(course_dir)
    manifest["counts"] = counts
    manifest["transcripts_available"] = counts.get("transcripts", 0) > 0
    course_dir.mkdir(parents=True, exist_ok=True)
    (course_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    _write_readme(course_dir, {
        "title": course["title"], "year": None, "url": course["url"],
        "institution": course["institution"], "code": course["code"],
    }, counts, manifest)
    return manifest


ALL_FOLDERS = ("transcripts", "transcripts/other-languages",
               "lecture-notes", "problem-sets", "exams", "other")


def _folder_counts(course_dir: Path) -> dict[str, int]:
    """Count actual downloaded files per folder (excluding derived .txt sidecars)."""
    out: dict[str, int] = {}
    for sub in ALL_FOLDERS:
        d = course_dir / sub
        if not d.exists():
            continue
        n = sum(1 for f in d.iterdir()
                if f.is_file() and f.suffix.lower() != ".txt")
        if n:
            out[sub] = n
    return out


def _write_readme(course_dir: Path, course: dict, counts: dict, manifest: dict) -> None:
    year = course.get("year")
    heading = f"# {course.get('title')} ({year})" if year else f"# {course.get('title')}"
    institution = course.get("institution") or "MIT"
    id_label = "Readable id" if institution == "MIT" else "Course code"
    lines = [
        heading,
        "",
        f"- Institution: {institution}",
        f"- Source: {course.get('url')}",
        f"- {id_label}: `{course.get('readable_id') or course.get('code')}`",
        f"- Transcripts available: **{'yes' if manifest['transcripts_available'] else 'NO'}**",
        "",
        "## Downloaded materials",
        "",
    ]
    labels = [
        ("transcripts", "transcripts/ (English)"),
        ("transcripts/other-languages", "transcripts/other-languages/ (translated captions)"),
        ("lecture-notes", "lecture-notes/"),
        ("problem-sets", "problem-sets/"),
        ("exams", "exams/"),
        ("other", "other/"),
    ]
    for key, label in labels:
        if counts.get(key):
            lines.append(f"- **{label}** — {counts[key]} files")
    if manifest["skipped_video"]:
        lines.append(f"- _(skipped {manifest['skipped_video']} video files — out of scope)_")
    if manifest["errors"]:
        lines.append(f"- _(⚠ {len(manifest['errors'])} files could not be fetched — see manifest.json)_")
    lines.append("")
    (course_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Download course materials from MIT OpenCourseWare and "
                     "Stanford Engineering Everywhere.")
    sub = p.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("search", help="List candidate courses for a topic (both institutions).")
    ps.add_argument("query")
    ps.add_argument("--limit", type=int, default=8)

    pr = sub.add_parser("resolve", help="Resolve one best-match course.")
    pr.add_argument("target")

    pd = sub.add_parser("download", help="Download a course's materials.")
    pd.add_argument("target", help="topic, course number/code, readable_id, or course URL")
    pd.add_argument("--dest", default=".", help="destination root (default: cwd)")
    pd.add_argument("--force", action="store_true", help="re-download existing files")

    args = p.parse_args(argv)

    if args.cmd == "search":
        print(json.dumps(combined_search(args.query, args.limit), indent=2))
    elif args.cmd == "resolve":
        print(json.dumps(resolve_any(args.target), indent=2))
    elif args.cmd == "download":
        man = download_any(args.target, Path(args.dest).resolve(), force=args.force)
        summary = {
            "institution": man["course"].get("institution"),
            "course": man["course"]["title"],
            "id": man["course"].get("readable_id") or man["course"].get("code"),
            "transcripts_available": man["transcripts_available"],
            "counts": man["counts"],
            "skipped_video": man["skipped_video"],
            "errors": len(man["errors"]),
        }
        print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
