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


def normalize_pdf_text(raw_text: str) -> str:
    """
    Convert raw PDF line-wrapped text into readable paragraphs.
    This merges broken lines, strips standard boilerplate, and keeps
    notice text readable for humans.
    """
    if not raw_text:
        return ""

    text = raw_text.replace("\r\n", "\n").replace("\r", "\n")

    # Fix text broken by PDF page wrapping and hyphenation.
    text = re.sub(r"(?<=\w)-\s*\n\s*", "", text)
    text = re.sub(r"(?<=\w)-\s+(?=\w)", "", text)
    text = re.sub(r"\t+", " ", text)

    clean_lines = []
    for line in text.split("\n"):
        clean = re.sub(r"\s+", " ", line.strip())
        if not clean:
            continue
        if should_exclude_line(clean):
            continue
        clean_lines.append(clean)

    if not clean_lines:
        return ""

    merged = []
    buffer = ""

    for line in clean_lines:
        is_bullet = line.startswith(("•", "-", "*"))
        starts_new_block = re.match(r"^[A-ZÁÉÍÓÚÀÂÊÔÜÃÕÇ0-9«\"]", line) is not None

        if not buffer:
            buffer = line
            continue

        if is_bullet:
            merged.append(buffer)
            buffer = line
            continue

        if buffer.endswith((".", "!", "?", ":", ";", "…")) or starts_new_block:
            merged.append(buffer)
            buffer = line
            continue

        buffer = f"{buffer} {line}"

    if buffer:
        merged.append(buffer)

    # Keep real blank-line separation while removing noise from wrapped lines.
    return "\n\n".join(part.strip() for part in merged if part.strip())


def render_notice_card(text: str) -> str:
    paragraphs = split_paragraphs(text)
    if not paragraphs:
        paragraphs = ["Não há avisos disponíveis."]

    paragraphs_html = []
    for paragraph in paragraphs:
        safe_paragraph = html.escape(paragraph).replace("\n", "<br>")
        paragraphs_html.append(f"<p>{safe_paragraph}</p>")
    return '<article class="notice">' + "\n".join(paragraphs_html) + "</article>"


def site_header() -> str:
    return """<header class="site-header">
    <div class="site-header-inner">
        <a class="brand" href="./index.html" aria-label="Avisos Covilhã Mobilidade, página inicial">
            <span class="brand-mark" aria-hidden="true">C<span>.</span></span>
            <span class="brand-text">Covilhã <strong>Mobilidade</strong><small>AVISOS DE SERVIÇO</small></span>
        </a>
        <nav class="site-nav" aria-label="Navegação principal">
            <a href="./index.html">Último aviso</a>
            <a href="./archive.html">Arquivo <span aria-hidden="true">↗</span></a>
        </nav>
    </div>
</header>"""


def site_footer() -> str:
    return """<footer class="site-footer">
    <div class="footer-inner">
        <p>Informação para quem anda pela cidade.</p>
        <p>Dados extraídos de <a href="https://covilhamobilidade.pt/">Covilhã Mobilidade</a> · Um projeto de <a href="https://claudioduarte.pt/">Cláudio Duarte</a></p>
    </div>
</footer>"""


def build_page(title: str, body_html: str, updated_at: str, *, is_index: bool = False) -> str:
    heading = "O seu percurso,<br>mais informado<span>.</span>" if is_index else "Um aviso<br>do arquivo<span>.</span>"
    eyebrow = "INFORMAÇÃO DE SERVIÇO" if is_index else "ARQUIVO DE AVISOS"
    description = (
        "Consulte aqui o último aviso de serviço da Covilhã Mobilidade."
        if is_index else "Consulte os detalhes deste aviso guardado no arquivo."
    )
    notice_label = "Último aviso" if is_index else "Aviso arquivado"
    date_label = "Atualizado em" if is_index else "Data do aviso"
    return f"""<!DOCTYPE html>
<html lang="pt-PT">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{html.escape(title)}</title>
    <meta name="description" content="Avisos de serviço da Covilhã Mobilidade." />
    <link rel="stylesheet" href="./css/site.css" />
    <link rel="icon" href="./images/favicon_io/favicon.ico" />
    <link rel="manifest" href="./images/favicon_io/site.webmanifest" />
</head>
<body>
    {site_header()}
    <main id="main-content" class="page-shell">
        <section class="hero" aria-labelledby="page-title">
            <div class="hero-copy">
                <p class="eyebrow"><span aria-hidden="true"></span>{eyebrow}</p>
                <h1 id="page-title">{heading}</h1>
                <p class="hero-description">{description}</p>
            </div>
            <div class="hero-art" aria-hidden="true">
                <span class="route-label">COVILHÃ<br>MOBILIDADE</span>
                <span class="route-line"><i></i><i></i><i></i></span>
                <span class="route-number">CM <strong>01</strong></span>
            </div>
        </section>
        <section class="notice-section" aria-labelledby="notice-heading">
            <div class="section-heading">
                <div><p class="section-kicker">INFORMAÇÃO DE SERVIÇO</p><h2 id="notice-heading">{notice_label}</h2></div>
                <p class="date-label">{date_label} <time datetime="{html.escape(updated_at, quote=True)}">{html.escape(updated_at)}</time></p>
            </div>
            {body_html}
            <div class="notice-actions"><a class="text-link" href="./archive.html">Explorar o arquivo <span aria-hidden="true">↗</span></a></div>
        </section>
    </main>
    {site_footer()}
</body>
</html>
"""


def build_archive_page() -> str:
    archive_files = sorted(DOCS_DIR.glob("notices-*.html"), reverse=True)
    archive_items = []

    for archive_file in archive_files:
        name = archive_file.name
        label = name.replace("notices-", "").replace(".html", "")
        archive_items.append(
            f'<a class="archive-item" href="./{html.escape(name, quote=True)}">'
            f'<span><small>AVISO DE SERVIÇO</small><time datetime="{html.escape(label, quote=True)}">'
            f'{html.escape(label)}</time></span><span class="archive-arrow" aria-hidden="true">↗</span></a>'
        )

    items_html = "\n            ".join(archive_items)

    return f"""<!DOCTYPE html>
<html lang="pt-PT">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Arquivo de Avisos | Covilhã Mobilidade</title>
    <meta name="description" content="Arquivo de avisos de serviço da Covilhã Mobilidade." />
    <link rel="stylesheet" href="./css/site.css" />
    <link rel="icon" href="./images/favicon_io/favicon.ico" />
    <link rel="manifest" href="./images/favicon_io/site.webmanifest" />
</head>
<body>
    {site_header()}
    <main id="main-content" class="page-shell">
        <section class="archive-intro">
            <p class="eyebrow"><span aria-hidden="true"></span>HISTÓRICO DE SERVIÇO</p>
            <h1>Arquivo de avisos<span>.</span></h1>
            <p class="hero-description">Consulte os avisos anteriores da Covilhã Mobilidade.</p>
        </section>
        <section class="archive-section" aria-labelledby="archive-heading">
            <div class="section-heading">
                <div><p class="section-kicker">CONSULTAR</p><h2 id="archive-heading">Avisos anteriores</h2></div>
                <p class="date-label">Mais recentes primeiro</p>
            </div>
            <div class="archive-list">
                {items_html}
            </div>
        </section>
    </main>
    {site_footer()}
</body>
</html>
"""


def generate_pages(text: str, notice_date: str):
    body_html = render_notice_card(text)

    index_html = build_page("Avisos | Covilhã Mobilidade", body_html, notice_date, is_index=True)
    (DOCS_DIR / "index.html").write_text(index_html, encoding="utf-8")

    dated_page = build_page(
        f"Aviso | Covilhã Mobilidade — {notice_date}",
        body_html,
        notice_date,
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
        normalized = normalize_pdf_text(page_text)
        if normalized:
            all_pages.append(normalized)

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
