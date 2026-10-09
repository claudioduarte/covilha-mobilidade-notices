# 🚍 Covilhã Mobilidade Notices

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)

A Python tool that automatically monitors a PDF source for Covilhã Mobilidade service notices, extracts the relevant text, and publishes the latest result on a GitHub Pages site.

This project checks the source PDF on a schedule, ignores unchanged content, and only generates new output when there is a real notice update.

> Disclaimer: This project was built with the help of GitHub Copilot.

## Features

- 📥 Download and parse the source PDF automatically
- 🔎 Extract only the relevant notice text from the document
- 🧹 Clean repeated boilerplate and noisy content before saving
- 📅 Save dated outputs in `output/` whenever content changes
- 🧾 Publish the latest notice and an archive of previous entries in `docs/`
- 🌐 Generate a static GitHub Pages site from the generated HTML files
- ⚙️ Run automatically with GitHub Actions on a schedule or on demand

## Repository structure

```text
.
├── .github/
│   └── workflows/
│       ├── extract-notices.yaml
│       └── python.yaml
├── docs/
│   ├── index.html
│   ├── archive.html
│   └── notices-YYYY-MM-DD.html
├── output/
│   ├── latest.txt
│   └── notices-YYYY-MM-DD.txt
├── scripts/
│   └── extract_notices.py
├── .gitignore
├── LICENSE
├── README.md
├── requirements.txt
└── ...
```

## How it works

The script in `scripts/extract_notices.py` performs the following steps:

1. Downloads the source PDF from the configured `PDF_URL`
2. Extracts text from the document using PyMuPDF
3. Removes repeated or irrelevant content from the PDF output
4. Saves the cleaned notice text to `output/latest.txt`
5. Writes dated files in the `output/` folder when the content changes
6. Generates static HTML pages in `docs/` for GitHub Pages

## Installation

### Requirements

- Python 3.12+
- `requests`
- `PyMuPDF`

### Setup

Clone the repository and install dependencies:

```bash
git clone https://github.com/claudioduarte/covilha-mobilidade-notices.git
cd covilha-mobilidade-notices
pip install -r requirements.txt
```

Alternatively, install manually:

```bash
pip install requests PyMuPDF
```

## Configuration

Set the PDF URL as a repository secret named `PDF_URL`.

Example:

```bash
export PDF_URL="https://example.com/notice.pdf"
```

Then run:

```bash
python scripts/extract_notices.py
```

## GitHub Actions workflow

The repo includes a workflow in `.github/workflows/extract-notices.yaml`.

That workflow:

- checks out the repository
- installs the Python dependencies
- runs the extraction script
- checks whether the notice content changed
- commits updated files when a new notice is detected
- publishes the latest HTML output and archive pages via GitHub Pages

## GitHub Pages

The generated site is published from the repository's `docs/` folder.

It includes:

- a landing page with the latest notice
- an archive page with historical notices
- individual pages for each dated notice snapshot

## Output examples

The text output is stored in files like:

- `output/latest.txt`
- `output/notices-2026-10-06.txt`

These files are used as the source for the HTML pages in `docs/`.

## License

This project is licensed under the MIT License. See `LICENSE` for details.
