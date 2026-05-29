#!/usr/bin/env python3
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
import re

import fitz
import requests

PDF_URL = os.environ.get("PDF_URL")

# Debug: Check if PDF_URL is set
if not PDF_URL:
    print("ERROR: PDF_URL environment variable is not set", file=sys.stderr)
    sys.exit(1)

print(f"DEBUG: PDF_URL = {PDF_URL}", file=sys.stderr)

OUT_DIR = Path("output")
OUT_DIR.mkdir(parents=True, exist_ok=True)

today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
txt_dated = OUT_DIR / f"notices-{today}.txt"
txt_latest = OUT_DIR / "latest.txt"

headers = {
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "User-Agent": "covilha-aviso-extractor/1.0",
}

# Define lines/patterns to exclude
EXCLUDE_LINES = [
    "Estimado(a) cliente,",
    "Lamentamos o incómodo causado. Agradecemos a compreensão.",
    "Covilhã Mobilidade",
    "+351 225 100 100",
    "(chamada para a rede fixa nacional)",
    "www.covilhamobilidade.pt",
]

def should_exclude_line(line):
    """Check if a line should be excluded"""
    line_stripped = line.strip()
    for pattern in EXCLUDE_LINES:
        if line_stripped.lower() == pattern.lower():
            return True
    return False

print("DEBUG: Downloading PDF...", file=sys.stderr)
response = requests.get(PDF_URL, headers=headers, timeout=60)
response.raise_for_status()
print(f"DEBUG: Response status code: {response.status_code}", file=sys.stderr)
print(f"DEBUG: Response content length: {len(response.content)} bytes", file=sys.stderr)

if not response.content.startswith(b"%PDF"):
    print("ERROR: Response is not a PDF", file=sys.stderr)
    sys.exit(1)

print("DEBUG: Extracting text from PDF...", file=sys.stderr)
doc = fitz.open(stream=response.content, filetype="pdf")
print(f"DEBUG: PDF has {len(doc)} pages", file=sys.stderr)

# Extract text line by line and filter
all_pages = []
for page_num, page in enumerate(doc):
    page_text = page.get_text().strip()
    if page_text:
        print(f"DEBUG: Page {page_num + 1} has {len(page_text)} chars", file=sys.stderr)
        # Process line by line, preserving paragraph breaks
        filtered_content = []
        current_paragraph = []
        
        for line in page_text.split("\n"):
            line = line.rstrip()
            
            if not line.strip():
                # Empty line - end current paragraph
                if current_paragraph:
                    filtered_content.append("\n".join(current_paragraph))
                    current_paragraph = []
            elif not should_exclude_line(line):
                # Non-empty, non-excluded line
                current_paragraph.append(line)
            else:
                # Excluded line
                print(f"DEBUG: Excluding line: {line[:60]}", file=sys.stderr)
                # End current paragraph if we hit an excluded line
                if current_paragraph:
                    filtered_content.append("\n".join(current_paragraph))
                    current_paragraph = []
        
        # Don't forget the last paragraph
        if current_paragraph:
            filtered_content.append("\n".join(current_paragraph))
        
        if filtered_content:
            all_pages.append("\n\n".join(filtered_content))

doc.close()

# Join pages with separator after each page
text = ("\n========\n".join(all_pages)) + "\n========\n"

print(f"DEBUG: Total pages processed: {len(all_pages)}", file=sys.stderr)
print(f"DEBUG: Final extracted text length: {len(text)} chars", file=sys.stderr)

# Check if content has changed
has_changed = True
if txt_latest.exists():
    existing_text = txt_latest.read_text(encoding="utf-8")
    has_changed = existing_text != text
    print(f"DEBUG: Previous file exists. Content changed: {has_changed}", file=sys.stderr)

# Only write files if content has changed
if has_changed:
    txt_dated.write_text(text, encoding="utf-8")
    txt_latest.write_text(text, encoding="utf-8")
    print(f"Extracted {len(text)} chars → {txt_dated} and {txt_latest}")
else:
    print("No changes detected in PDF content")
