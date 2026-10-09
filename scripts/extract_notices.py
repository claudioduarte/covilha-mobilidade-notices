#!/usr/bin/env python3
import html
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import fitz
import requests

PDF_URL = os.environ.get("PDF_URL")

if not PDF_URL:
    print("ERROR: PDF_URL environment variable is not set", file=sys.stderr)
    sys.exit(1)

ROOT_DIR = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT_DIR / "output"
DOCS_DIR = ROOT_DIR / "docs"
OUT_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)

today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
txt_dated = OUT_DIR / f"notices-{today}.txt"
txt_latest = OUT_DIR / "latest.txt"

headers = {
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "User-Agent": "covilha-aviso-extractor/1.0",
}

EXCLUDE_LINES = [
    "Estimado(a) cliente,",
    "Lamentamos o incómodo causado. Agradecemos a compreensão.",
    "Covilhã Mobilidade",
    "+351 225 100 100",
    "(chamada para a rede fixa nacional)",
    "www.covilhamobilidade.pt",
    "Agradecemos a sua compreensão e desejamos-lhe umas Boas Férias!",
    "Agradecemos a compreensão e lamentamos os incómodos causados.",
]


def should_exclude_line(line: str) -> bool:
    line_stripped = line.strip()
    for pattern in EXCLUDE_LINES:
        if line_stripped.lower() == pattern.lower():
            return True
    return False


def split_paragraphs(text: str):
    return [p.strip() for p in re.split(r"\n\s*\n+", text.strip()) if p.strip()]


def render_notice_card(text: str) -> str:
    paragraphs = split_paragraphs(text)
    if not paragraphs:
        paragraphs = ["No notices available."]

    cards = []
    for paragraph in paragraphs:
        safe_paragraph = html.escape(paragraph).replace("\n", "<br>")
        cards.append(f"<article class=\"notice\"><p>{safe_paragraph}</p></article>")
    return "\n".join(cards)


def build_page(title: str, body_html: str, updated_at: str, archive_url: str = "./archive.html") -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{html.escape(title)}</title>
    <style>
        :root {{
            --bg: #f5f7fb;
            --card: #ffffff;
            --ink: #1f2937;
            --muted: #6b7280;
            --accent: #2563eb;
            --accent-soft: #dbeafe;
            --border: #dfe3ea;
        }}
        * {{ box-sizing: border-box; }}
        body {{
            margin: 0;
            font-family: Arial, Helvetica, sans-serif;
            background: var(--bg);
            color: var(--ink);
            line-height: 1.6;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            padding: 32px 20px 48px;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 16px;
            flex-wrap: wrap;
            margin-bottom: 24px;
        }}
        h1 {{
            margin: 0;
            font-size: clamp(2rem, 3vw, 2.75rem);
        }}
        .archive-link {{
            display: inline-block;
            text-decoration: none;
            background: var(--accent-soft);
            color: var(--accent);
            border: 1px solid var(--border);
            border-radius: 999px;
            padding: 10px 18px;
            font-weight: 600;
        }}
        .meta {{
            color: var(--muted);
            margin-bottom: 20px;
        }}
        .docs {{
            display: grid;
            gap: 18px;
        }}
        .notice {{
            background: var(--card);
            border: 1px solid var(--border);
            border-left: 6px solid var(--accent);
            border-radius: 12px;
            padding: 18px 20px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
        }}
        .notice p {{
            margin: 0;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        .archive-list {{
            display: grid;
            gap: 12px;
            margin-top: 18px;
        }}
        .archive-item {{
            display: block;
            padding: 12px 14px;
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 10px;
            text-decoration: none;
            color: var(--ink);
            font-weight: 600;
        }}
        @media (max-width: 640px) {{
            .header {{
                align-items: flex-start;
            }}
        }}
    </style>
</head>
<body>
    <main class="container">
        <div class="header">
            <h1>{html.escape(title)}</h1>
            <a class="archive-link" href="{archive_url}">Archive</a>
        </div>
        <div class="meta">Updated: {html.escape(updated_at)}</div>
        <section class="docs">
            {body_html}
        </section>
    </main>
</body>
</html>
"""


def build_archive_page() -> str:
    archive_files = sorted(DOCS_DIR.glob("notices-*.html"))
    archive_items = []

    for archive_file in archive_files:
        name = archive_file.name
        if name == "index.html":
            continue
        label = name.replace("notices-", "").replace(".html", "")
        archive_items.append(f'<a class="archive-item" href="./{name}">{label}</a>')

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Covilhã Mobilidade Notices Archive</title>
    <style>
        body {{
            margin: 0;
            font-family: Arial, Helvetica, sans-serif;
            background: #f5f7fb;
            color: #1f2937;
            line-height: 1.6;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            padding: 32px 20px 48px;
        }}
        h1 {{ margin-bottom: 20px; }}
        .archive-list {{ display: grid; gap: 12px; }}
        .archive-item {{
            display: block;
            padding: 12px 14px;
            background: #ffffff;
            border: 1px solid #dfe3ea;
            border-radius: 10px;
            text-decoration: none;
            color: #1f2937;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <main class="container">
        <h1>Archive</h1>
        <div class="archive-list">
            <a class="archive-item" href="./index.html">Latest</a>
            {''.join(archive_items)}
        </div>
    </main>
</body>
</html>
"""


def generate_pages(text: str, notice_date: str):
    body_html = render_notice_card(text)

    index_html = build_page("Covilhã Mobilidade Notices", body_html, notice_date)
    (DOCS_DIR / "index.html").write_text(index_html, encoding="utf-8")

    dated_page = build_page(
        f"Covilhã Mobilidade Notices — {notice_date}",
        body_html,
        notice_date,
        archive_url="./archive.html",
    )
    (DOCS_DIR / f"notices-{notice_date}.html").write_text(dated_page, encoding="utf-8")

    archive_html = build_archive_page()
    (DOCS_DIR / "archive.html").write_text(archive_html, encoding="utf-8")


print("DEBUG: Downloading PDF...", file=sys.stderr)
response = requests.get(PDF_URL, headers=headers, timeout=60)
response.raise_for_status()
print(f"DEBUG: Response status code: {response.status_code}", file=sys.stderr)

if not response.content.startswith(b"%PDF"):
    print("ERROR: Response is not a PDF", file=sys.stderr)
    sys.exit(1)

print("DEBUG: Extracting text from PDF...", file=sys.stderr)
doc = fitz.open(stream=response.content, filetype="pdf")
print(f"DEBUG: PDF has {len(doc)} pages", file=sys.stderr)

all_pages = []
for page_num, page in enumerate(doc):
    page_text = page.get_text().strip()
    if page_text:
        filtered_content = []
        current_paragraph = []
        for line in page_text.split("\n"):
            line = line.rstrip()
            if not line.strip():
                if current_paragraph:
                    filtered_content.append("\n".join(current_paragraph))
                    current_paragraph = []
            elif not should_exclude_line(line):
                current_paragraph.append(line)
            else:
                if current_paragraph:
                    filtered_content.append("\n".join(current_paragraph))
                    current_paragraph = []
        if current_paragraph:
            filtered_content.append("\n".join(current_paragraph))
        if filtered_content:
            all_pages.append("\n\n".join(filtered_content))

doc.close()

text = "\n\n\n\n".join(all_pages)

print(f"DEBUG: Total pages processed: {len(all_pages)}", file=sys.stderr)
print(f"DEBUG: Final extracted text length: {len(text)} chars", file=sys.stderr)

has_changed = True
if txt_latest.exists():
    existing_text = txt_latest.read_text(encoding="utf-8")
    has_changed = existing_text != text
    print(f"DEBUG: Previous file exists. Content changed: {has_changed}", file=sys.stderr)

if has_changed:
    txt_dated.write_text(text, encoding="utf-8")
    txt_latest.write_text(text, encoding="utf-8")
    generate_pages(text, today)
    print(f"Extracted {len(text)} chars → {txt_dated} and {txt_latest}")
    print(f"Generated GitHub Pages content in {DOCS_DIR}")
else:
    print("No changes detected in PDF content")
    if txt_latest.exists():
        latest_text = txt_latest.read_text(encoding="utf-8")
        if latest_text:
            generate_pages(latest_text, today)
            print(f"Refreshed GitHub Pages content in {DOCS_DIR}")
