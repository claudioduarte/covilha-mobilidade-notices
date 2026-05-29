# 🚍 Covilhã Mobilidade Notices

A Python tool to automatically extract and track notices from PDF documents. This project monitors a PDF source, extracts text content, and only generates output files when changes are detected.

## Features

- 📥 **Automatic PDF Extraction**: Downloads and extracts text from PDF documents
- 🔍 **Change Detection**: Only generates output when PDF content actually changes
- 📅 **Timestamped Exports**: Saves dated and latest versions of extracted text
- ⏭️ **Selective Extraction**: Exclude specific paragraphs or patterns from extraction
- 🔄 **No-Cache Headers**: Ensures fresh PDF content with proper cache control
- ⚠️ **Error Handling**: Validates PDF format and handles network errors

## Installation

### Requirements

- Python 3.8+
- `requests` - For downloading PDFs
- `PyMuPDF (fitz)` - For PDF text extraction

### Setup

1. Clone the repository:
```bash
git clone https://github.com/claudioduarte/covilha-mobilidade-notices.git
cd covilha-mobilidade-notices
```

2. Install dependencies:
```bash
pip install requests PyMuPDF
```

## Configuration

### Environment Variables

- `PDF_URL` (required): The URL of the PDF document to extract

Example:
```bash
export PDF_URL="https://example.com/notices.pdf"
```

## Usage

### Basic Usage

Run the extraction script:
```bash
python scripts/extract_notices.py
```

### Output

The script generates two files in the `output/` directory:

- `notices-YYYY-MM-DD.txt` - Timestamped file with today's extraction
- `latest.txt` - Always contains the most recent extraction

**Example output:**
```
Extracted 2450 chars → output/notices-2026-05-29.txt and output/latest.txt
```

If no changes are detected:
```
No changes detected in PDF content
```

## Filtering & Customization

### Excluding Paragraphs

You can exclude specific paragraphs by modifying the `EXCLUDE_PATTERNS` list in `extract_notices.py`:

```python
EXCLUDE_PATTERNS = [
    "Advertisement",
    "Disclaimer",
    "Copyright",
]
```

### Regex-Based Filtering

For more advanced filtering, use regex patterns:

```python
import re

EXCLUDE_PATTERNS = [
    r"^\d{4}-\d{2}-\d{2}",  # Exclude date lines
    r"^(Page|Página) \d+",   # Exclude page numbers
]
```

## Change Detection Logic

The script compares the newly extracted text with the existing `latest.txt` file:

- **First run**: No previous `latest.txt` exists → files are created
- **Changes detected**: New content differs from existing file → files are updated
- **No changes**: Content is identical → no files are written

This prevents unnecessary file churn when the PDF content hasn't changed.

## Project Structure

```
covilha-mobilidade-notices/
├── scripts/
│   └── extract_notices.py    # Main extraction script
├── output/                    # Generated output files
├── README.md
└── LICENSE                    # GPLv3
```

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

## Troubleshooting

### "Response is not a PDF"

The URL returned non-PDF content. Check that:
- `PDF_URL` environment variable is correctly set
- The URL is accessible and returns a valid PDF
- No redirects are preventing the actual PDF download

### No output files generated

This could mean:
- The PDF content matches the existing `latest.txt` (no changes detected)
- The script is excluding all content via filters
- Check console output for error messages

### PDF extraction is slow

For large PDFs, extraction may take time. Consider:
- Setting a higher timeout value in the `requests.get()` call
- Running the script during off-peak hours
