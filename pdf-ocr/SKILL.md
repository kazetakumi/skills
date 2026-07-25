---
name: pdf-ocr
description: Convert PDF files to Markdown using docling's OCR/document-understanding pipeline, with progress bars and a persistent CSV/HTML conversion log. Use when the user wants to OCR a PDF, extract or convert a PDF (or folder of PDFs) into Markdown/plain text, or batch-process scanned documents into readable text.
---

# PDF OCR (docling)

Converts PDFs to Markdown using [docling](https://github.com/docling-project/docling), which handles both
digital and scanned/image-based PDFs (OCR + layout + table structure).

## Requirements

- `uv` must be installed (`brew install uv` or https://docs.astral.sh/uv/). The script is a
  self-contained `uv` script (PEP 723 inline deps) — no project setup or manual venv needed.
- First run downloads docling's OCR/layout models (a few hundred MB); needs internet access once,
  then models are cached locally.

## Quick start

Run from the repo root (paths below are relative to it):

Convert a single PDF:

```bash
uv run .claude/skills/pdf-ocr/scripts/ocr_pdf.py path/to/document.pdf
```

Convert every PDF in a folder:

```bash
uv run .claude/skills/pdf-ocr/scripts/ocr_pdf.py path/to/pdf_folder/
```

Pass `-o` to control where `.md` files land:

```bash
uv run .claude/skills/pdf-ocr/scripts/ocr_pdf.py document.pdf -o outs/
```

With no arguments, it looks for PDFs in `./pdfs/` and writes to `./outs/`, matching this repo's
`pdfs/` / `outs/` layout.

## Behavior

- **Skips already-converted files**: if `outs/<name>.md` already exists, that PDF is skipped. Delete
  the `.md` to force reconversion.
- **Conversion register**: every run appends to `<output>/register.csv` (input name, output name,
  timestamp, page count, time taken) and regenerates `<output>/register.html` as a human-readable log.
  This history is also used to estimate progress-bar timing on later runs.
- **Progress bars**: an overall file-count bar plus a per-file page-based bar (time-estimated, since
  docling doesn't expose true per-page progress for a single `convert()` call).

## Notes

- Large or scanned PDFs can take a while (OCR is CPU/GPU-bound); the register's historical
  seconds-per-page estimate makes the per-file bar more accurate after the first few conversions.
- Output is Markdown via docling's `export_to_markdown()` — tables and headings are preserved where
  docling detects structure.
