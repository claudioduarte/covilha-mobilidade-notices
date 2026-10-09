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
    <link rel="stylesheet" href="./css/style-archive-notices.css" />
    <link rel="icon" href="./images/favicon_io/favicon.ico" />
    <link rel="manifest" href="./images/favicon_io/site.webmanifest" />
</head>
<body>
    <main class="container">
        <div class="header">
            <h1>{html.escape(title)}</h1>
            <a class="archive-link" href="{archive_url}">Arquivo</a>
        </div>
        <div class="meta">Última atualização: {html.escape(updated_at)}</div>
        <section class="docs">
            {body_html}
        </section>
    </main>
    <footer>
        Dados extraídos de <a href="https://covilhamobilidade.pt/">https://covilhamobilidade.pt/</a>
    </footer>
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
    <title>Arquivo de Avisos | Covilhã Mobilidade</title>
    <link rel="stylesheet" href="./css/style-archive.css" />
    <link rel="icon" href="./images/favicon_io/favicon.ico" />
    <link rel="manifest" href="./images/favicon_io/site.webmanifest" />
</head>
<body>
    <main class="container">
        <h1>Arquivo</h1>
        <div class="archive-list">
            <a class="archive-item" href="./index.html">⬅️ Últimas</a>
            {''.join(archive_items)}
        </div>
    </main>
    <footer>
        <section class="footer-content">
            Dados extraídos de <a href="https://covilhamobilidade.pt/">Covilhã Mobilidade</a>. Um projeto de <a href="https://claudioduarte.pt/">Cláudio Duarte</a>.
        </section>
    </footer>
</body>
</html>
"""


def generate_pages(text: str, notice_date: str):
    body_html = render_notice_card(text)

    index_html = build_page("Avisos | Covilhã Mobilidade", body_html, notice_date)
    (DOCS_DIR / "index.html").write_text(index_html, encoding="utf-8")

    dated_page = build_page(
        f"Aviso | Covilhã Mobilidade — {notice_date}",
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
