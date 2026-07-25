# Raw -> processed data extraction prompt

Reusable prompt/checklist for turning new raw files dropped in `data/` into RAG-ready text in
`data/processed/`. Paste the relevant parts to Claude when new raw docs are added.

## Prompt to reuse

> New raw file(s) were added to `data/`. Read each one directly (PDF pages render as images if there's
> no text layer - view them like photos, don't guess) and write a clean, structured `.txt` file into
> `data/processed/` for each source, following the section style used in `shameerpet_broucher.txt` /
> `lakeside_manor_booklet.txt` (clear ALL-CAPS section headers, short factual lines/bullets, no marketing
> fluff, no duplicated boilerplate across files - if two raw docs overlap, put shared facts in one file and
> only the delta in the other). Then:
> 1. Add an entry to `SOURCE_PDF` in `services/rag_service.py` mapping the new processed filename to the
>    raw PDF filename it came from, so retrieved chunks link back to the real, downloadable document.
> 2. Run `index_documents()` (or `POST /index`) to reindex.
> 3. Sanity-check with `retrieve("<likely user question>")` and confirm the answer + document link work.

## Handling large / scanned PDFs (no text layer, > 20MB)

The `Read` tool can't page-render PDFs here (poppler/`pdftoppm` isn't installed) and refuses PDFs over
20MB outright. Work around it locally instead of skipping the file:

```bash
python -m venv /path/to/scratch/pdfvenv
/path/to/scratch/pdfvenv/Scripts/python.exe -m pip install --quiet pymupdf
```

```python
import fitz  # pymupdf
doc = fitz.open("data/<file>.pdf")
for i, page in enumerate(doc):
    pix = page.get_pixmap(matrix=fitz.Matrix(1.2, 1.2))  # ~1000px wide, keeps images small enough to view
    pix.save(rf"<scratch_dir>\page_{i+1:02d}.png")
```

Then `Read` each PNG (they're normal images) and transcribe the content. This is a one-off local tool for
extraction only - it's installed in a throwaway venv, never added to `requirements.txt`.

## What to include per document

- Project/company facts: name, developer, established year, track record
- Location: address, and the exact Maps link if one was given (see below) - don't just paraphrase the
  address, keep the literal shareable link so it can be handed back to users verbatim
- Pricing, specs, dimensions, amenities - as printed, don't round or summarize away specific numbers
- Contact info: phone, email, website
- A short caption for any meaningful photo (skip pure branding/logo images)
- Skip video - Claude Code has no video viewing/transcription capability here. If a written description is
  supplied later, add it as a text block instead.

## Location / Maps links

If a Google Maps link (short `maps.app.goo.gl/...` or full `google.com/maps/place/...`) is provided for a
property, put it in the processed file as its own line, e.g.:

```
MAP: https://maps.app.goo.gl/<id> (Google Maps pin for <project name>; resolves to <resolved place URL>,
coordinates <lat>, <lng>)
```

Keep the original short link (what people actually share/paste) as the primary value - the system prompts
in `ai_service.py`/`gemini_service.py` are instructed to reuse an explicit `MAP:` link verbatim instead of
constructing a `maps.google.com/?q=...` search link from the address text.
