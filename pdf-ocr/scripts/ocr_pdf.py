#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "docling>=2.115.0",
#     "pypdfium2>=4.0.0",
#     "tqdm>=4.60.0",
# ]
# ///
"""Convert one PDF or a directory of PDFs to Markdown via docling OCR.

Skips PDFs that already have a matching .md in the output directory, and
maintains a CSV/HTML conversion register (history log) in the output dir.
"""

import argparse
import csv
import html
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Thread

import pypdfium2 as pdfium
from tqdm import tqdm

from docling.document_converter import DocumentConverter

REGISTER_FIELDS = ["input_name", "output_name", "timestamp", "pages", "time_taken_sec"]
DEFAULT_SEC_PER_PAGE = 0.6


def count_pages(pdf_path: Path) -> int:
    doc = pdfium.PdfDocument(str(pdf_path))
    try:
        return len(doc)
    finally:
        doc.close()


def load_avg_sec_per_page(register_path: Path) -> float:
    """Seed the per-pdf progress estimate from past runs recorded in the register."""
    if not register_path.exists():
        return DEFAULT_SEC_PER_PAGE
    total_pages = 0
    total_time = 0.0
    with register_path.open(newline="") as f:
        for row in csv.DictReader(f):
            try:
                pages = int(row["pages"])
                time_taken = float(row["time_taken_sec"])
            except (KeyError, ValueError, TypeError):
                continue
            if pages > 0:
                total_pages += pages
                total_time += time_taken
    return (total_time / total_pages) if total_pages else DEFAULT_SEC_PER_PAGE


def append_register(
    register_path: Path, input_name: str, output_name: str, timestamp: str, pages: int, time_taken_sec: float
) -> None:
    is_new = not register_path.exists()
    with register_path.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=REGISTER_FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow(
            {
                "input_name": input_name,
                "output_name": output_name,
                "timestamp": timestamp,
                "pages": pages,
                "time_taken_sec": f"{time_taken_sec:.2f}",
            }
        )


def format_duration(seconds: float) -> str:
    total = int(round(seconds))
    if total < 60:
        return f"{seconds:.1f}s"
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes}m {secs}s"
    return f"{minutes}m {secs}s"


def write_register_html(register_path: Path, register_html_path: Path) -> None:
    """Regenerate register.html from the (append-only) CSV so it's always a
    full, human-readable view of the log -- the CSV stays the source of
    truth, this is just a derived report."""
    rows: list[dict] = []
    if register_path.exists():
        with register_path.open(newline="") as f:
            rows = list(csv.DictReader(f))

    total_pages = sum(int(r["pages"]) for r in rows if r.get("pages", "").isdigit())
    total_time = sum(float(r["time_taken_sec"]) for r in rows if r.get("time_taken_sec"))

    body_rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(r['input_name'])}</td>"
        f"<td>{html.escape(r['output_name'])}</td>"
        f"<td>{html.escape(r['timestamp'])}</td>"
        f"<td class='num'>{html.escape(r['pages'])}</td>"
        f"<td class='num'>{html.escape(format_duration(float(r['time_taken_sec'])))}</td>"
        "</tr>"
        for r in reversed(rows)
    )

    generated_at = datetime.now(timezone.utc).isoformat()
    page = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Conversion register</title>
<style>
  body {{ font-family: -apple-system, sans-serif; margin: 2rem; color: #1a1a1a; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ padding: 0.5rem 0.8rem; border-bottom: 1px solid #ddd; text-align: left; }}
  th {{ background: #f4f4f4; }}
  td.num, th.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  tr:hover {{ background: #f9f9f9; }}
  .summary {{ color: #555; margin-bottom: 1rem; }}
  @media (prefers-color-scheme: dark) {{
    body {{ background: #1a1a1a; color: #eee; }}
    th {{ background: #2a2a2a; }}
    th, td {{ border-bottom: 1px solid #333; }}
    tr:hover {{ background: #242424; }}
    .summary {{ color: #aaa; }}
  }}
</style>
</head>
<body>
<h1>Conversion register</h1>
<p class="summary">{len(rows)} conversions &middot; {total_pages} pages &middot; {format_duration(total_time)} total &middot; generated {generated_at}</p>
<table>
<thead><tr><th>Input</th><th>Output</th><th>Timestamp</th><th class="num">Pages</th><th class="num">Time</th></tr></thead>
<tbody>
{body_rows}
</tbody>
</table>
</body>
</html>
"""
    register_html_path.write_text(page)


def convert_with_progress(
    converter: DocumentConverter, pdf_path: Path, n_pages: int, est_sec_per_page: float, position: int
):
    """Run the (blocking) conversion on a worker thread while animating a
    per-pdf progress bar toward an estimated completion time. Docling doesn't
    expose per-page progress for a single convert() call, so this is a rough
    time-based estimate, not a measured one."""
    result_holder: dict = {}

    def run():
        result_holder["result"] = converter.convert(pdf_path)

    worker = Thread(target=run)
    est_total = max(n_pages * est_sec_per_page, 0.1)

    with tqdm(total=n_pages, desc=pdf_path.name, position=position, leave=False, unit="page") as bar:
        start = time.perf_counter()
        worker.start()
        while worker.is_alive():
            elapsed = time.perf_counter() - start
            fraction = min(elapsed / est_total, 0.98)
            bar.n = int(fraction * n_pages)
            bar.refresh()
            time.sleep(0.2)
        worker.join()
        bar.n = n_pages
        bar.refresh()

    return result_holder["result"]


def resolve_inputs(input_path: Path) -> list[Path]:
    if input_path.is_file():
        if input_path.suffix.lower() != ".pdf":
            raise SystemExit(f"Not a PDF: {input_path}")
        return [input_path]
    if input_path.is_dir():
        return sorted(input_path.glob("*.pdf"))
    raise SystemExit(f"Input not found: {input_path}")


def main():
    parser = argparse.ArgumentParser(description="Convert PDF(s) to Markdown via docling OCR.")
    parser.add_argument("input", nargs="?", default="pdfs", help="PDF file or directory of PDFs (default: ./pdfs)")
    parser.add_argument(
        "-o", "--output", default="outs", help="Output directory for .md files and register (default: ./outs)"
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    outs_dir = Path(args.output)
    outs_dir.mkdir(parents=True, exist_ok=True)
    register_path = outs_dir / "register.csv"
    register_html_path = outs_dir / "register.html"

    pdf_files = resolve_inputs(input_path)
    if not pdf_files:
        print(f"No PDFs found in {input_path}")
        return

    to_process = [p for p in pdf_files if not (outs_dir / f"{p.stem}.md").exists()]
    n_skipped = len(pdf_files) - len(to_process)
    if n_skipped:
        print(f"Skipping {n_skipped} file(s) with existing output in {outs_dir}/")
    if not to_process:
        print("Nothing to convert.")
        return

    converter = DocumentConverter()
    est_sec_per_page = load_avg_sec_per_page(register_path)

    for pdf_path in tqdm(to_process, desc="Overall", position=0, unit="file"):
        n_pages = count_pages(pdf_path)

        t0 = time.perf_counter()
        result = convert_with_progress(converter, pdf_path, n_pages, est_sec_per_page, position=1)
        elapsed = time.perf_counter() - t0

        out_name = f"{pdf_path.stem}.md"
        (outs_dir / out_name).write_text(result.document.export_to_markdown())

        timestamp = datetime.now(timezone.utc).isoformat()
        append_register(register_path, pdf_path.name, out_name, timestamp, n_pages, elapsed)
        write_register_html(register_path, register_html_path)

        if n_pages:
            est_sec_per_page = (est_sec_per_page + elapsed / n_pages) / 2

    print(f"Converted {len(to_process)} file(s) into {outs_dir}/")


if __name__ == "__main__":
    main()
