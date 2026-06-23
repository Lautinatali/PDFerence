# PDFerence: PDF Metadata Processor with Obsidian Integration

A tool for processing academic PDFs, extracting metadata via CrossRef/OpenAlex/PubMed APIs, and creating linked notes in your Obsidian vault.

## Architecture Refactoring (v0.2)

This refactored version replaces scattered logic across multiple files with a **clean, modular architecture**:

```
pdfference/
├── config.py              # ✅ Single source of truth for all settings
├── core/
│   ├── models.py          # ✅ Type-safe domain models (Paper, ProcessingResult)
│   ├── pdf_processor.py   # ✅ DOI extraction + file organization
│   ├── metadata_fetcher.py # ✅ Unified API integration (CrossRef→OpenAlex→PubMed)
│   ├── note_generator.py  # ✅ Markdown note creation
│   ├── linker.py          # ✅ Shared wikilink injection logic
│   ├── keyword_store.py   # ✅ Keyword persistence + management (add/remove/rename)
│   └── setup.py           # ✅ Automated workflow orchestration
├── analysis/
│   └── keyword_extractor.py # ✅ N-gram extraction + deduplication
├── utils/
│   └── logger.py          # ✅ Unified logging system
└── ui/
    └── app.py             # ✅ Streamlit UI (3 pages: home, setup, keyword management)
cli.py                      # ✅ Standalone CLI tool (7 commands including setup)
```

### Key Improvements

| Aspect | Before | After |
|--------|--------|-------|
| **Code Duplication** | 4+ copies of core logic | Single shared modules |
| **Configuration** | Hardcoded everywhere | Centralized `config.py` + `.env` |
| **Type Safety** | No hints | Full typing + dataclasses |
| **Testing** | Impossible | Comprehensive pytest suite |
| **Reusability** | Streamlit-only | CLI + Streamlit + scripts |
| **Logging** | print() scattered | Unified Logger with file output |
| **Error Handling** | Silent failures | Explicit exceptions + logging |

---

## Quick Start

### Installation

```bash
# Clone or navigate to project
cd PDFerence

# Create virtual environment
python -m venv venv
.\venv\Scripts\activate  # Windows
# or: source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your paths and email
```

### Using the Streamlit UI

```bash
streamlit run pdfference/ui/app.py
```

Then navigate through three main pages:

1. **Home Dashboard** - View keyword stats, vault status, quick actions
2. **Setup Workflow** - Automated: process PDFs → extract keywords → interactive review → apply links
3. **Keyword Management** - Add/remove/rename keywords, reindex vault

### Using the CLI

```bash
# Automated setup (fastest way to get started)
python cli.py setup "path/to/pdfs" -o "path/to/vault"

# Or use individual commands:
python cli.py process-pdfs "path/to/pdfs" -o "path/to/vault"
python cli.py extract-keywords -v "path/to/vault" -o keywords.csv
python cli.py apply-links -v "path/to/vault" -k keywords.csv
python cli.py reindex-vault -v "path/to/vault"
```

### Using Python API Directly

```python
from pathlib import Path
from pdfference.config import Config
from pdfference.core.pdf_processor import PDFProcessor
from pdfference.core.metadata_fetcher import MetadataFetcher
from pdfference.core.note_generator import NoteGenerator
from pdfference.utils.logger import Logger

# Initialize
logger = Logger("MyApp", Config.LOG_DIR)
pdf_proc = PDFProcessor(logger)
fetcher = MetadataFetcher(logger)
note_gen = NoteGenerator(logger)

# Process a single PDF
pdf_path = Path("paper.pdf")
doi = pdf_proc.extract_doi_from_pdf(pdf_path)
paper = fetcher.fetch(doi)
note_path = note_gen.save_note(paper, Config.VAULT_PATH)
```

---

## Configuration

### Environment Variables (.env)

```env
# Vault path
VAULT_PATH=G:\Mi unidad\Input_network\Input_network

# Required for PubMed API
PUBMED_EMAIL=your.email@example.com
```

### Python Config (config.py)

All settings centralized in `pdfference/config.py`:
- API timeouts
- Stop words and academic noise filters
- Keywords to link
- Min/max n-gram sizes

---

## Module Reference

### `config.py`
Centralized settings. Use in any module:
```python
from pdfference.config import Config
print(Config.STOP_WORDS)
print(Config.VAULT_PATH)
```

### `core/models.py`
Type-safe domain models:
- `Paper`: Academic paper with metadata
- `ProcessingResult`: Single PDF processing result
- `ProcessingStats`: Batch processing statistics

### `core/pdf_processor.py`
```python
processor = PDFProcessor(logger)
doi = processor.extract_doi_from_pdf(Path("paper.pdf"))
new_path = processor.organize_pdf(pdf_path, dest_folder, paper)
```

### `core/metadata_fetcher.py`
Automatic fallback chain: CrossRef → OpenAlex → PubMed
```python
fetcher = MetadataFetcher(logger)
paper = fetcher.fetch("10.1234/test")  # Returns Paper or None
```

### `core/note_generator.py`
Create Obsidian-compatible notes:
```python
gen = NoteGenerator(logger)
note_path = gen.save_note(paper, Path("vault/Notes"))
```

### `core/linker.py`
Inject [[wikilinks]] into notes:
```python
linker = Linker(logger)
# Single file
linker.apply_links_to_file(Path("note.md"), {"keyword1", "keyword2"})
# Entire vault
processed, modified = linker.apply_links_to_vault(vault_path, keywords)
```

### `core/keyword_store.py`
Persist and manage approved keywords:
```python
store = KeywordStore()
# Add/remove keywords
store.add_keyword("machine learning")
store.remove_keyword("deep learning")
# Rename keyword
store.rename_keyword("ML", "machine learning")
# Retrieve all keywords
all_keywords = store.get_all_keywords()
# Persistence
store.save()
```

### `core/setup.py`
Automated workflow: process PDFs → extract keywords → review → link:
```python
results = setup_automated(
    pdf_folder=Path("./papers"),
    output_folder=Path("./vault"),
    min_keyword_count=2,
    keyword_limit=50
)
# Returns: {pdfs_processed, keywords_extracted, keywords_approved, files_modified}
```
Extract n-grams from abstracts:
```python
extractor = KeywordExtractor(logger)
# Extract from single text
freq = extractor.extract("Text about smooth muscle cells...")
# Extract from entire vault
freq = extractor.extract_from_vault(vault_path, target_header="Abstract")
# Deduplicate and rank
top_keywords = extractor.deduplicate(freq, min_count=2)
```

### `utils/logger.py`
Unified logging to file + console + UI:
```python
logger = Logger("MyModule", Config.LOG_DIR)
logger.info("Info message")  # File + console + UI buffer
logger.error("Error message")
logger.success("Success!")
output = logger.get_ui_output()  # For Streamlit
```

---

## Keyword Management

### Overview

Keywords are the foundation of the wikilink system. PDFerence supports:

1. **Automatic Extraction**: Extract n-grams from vault abstracts
2. **Manual Approval**: Review and approve keywords interactively
3. **Persistent Storage**: Keywords saved to `keywords_store.json` for incremental scans
4. **CRUD Operations**: Add, remove, rename keywords via CLI or UI

### Workflows

#### CLI: Setup Command (Recommended for new vaults)

```bash
python cli.py setup /path/to/pdfs -o /path/to/vault -m 2 -l 50
```

This automates the entire flow:
1. Processes PDFs → creates notes
2. Extracts keywords from abstracts
3. Shows [y/n/skip] prompts for each keyword
4. Applies wikilinks using approved keywords
5. Saves keywords to persistent store

#### CLI: Review & Reindex (for incremental scans)

```bash
# Find new keywords in papers added since last scan
python cli.py scan-new-papers -v /path/to/vault -m 2

# Review and approve new keywords
python cli.py review-keywords -v /path/to/vault -l 50

# Re-apply all approved keywords to entire vault
python cli.py reindex-vault -v /path/to/vault
```

#### UI: Keyword Management Dashboard

1. Start from **Keyword Management** page
2. View all current keywords
3. **Add keyword**: Type name + click Add
4. **Remove keyword**: Click Remove (confirm with second click)
5. **Rename keyword**: Click Rename, enter new name, confirm
6. **Reindex vault**: Apply all keywords to vault files

### Keyword Store

Keywords are stored in `keywords_store.json`:

```json
{
  "keywords": {
    "machine learning": {
      "date_added": "2026-06-23T15:30:00",
      "status": "approved"
    },
    "neural networks": {
      "date_added": "2026-06-23T15:30:05",
      "status": "approved"
    }
  },
  "last_scan": "2026-06-23T15:35:00",
  "metadata": {}
}
```

When you add/remove/rename keywords via UI or CLI, the store is automatically updated and persisted.

---

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_pdfference.py -v

# Run with coverage
pytest tests/ --cov=pdfference --cov-report=html
```

Test files:
- `tests/test_pdfference.py`: Unit + integration tests
- `tests/conftest.py`: Pytest fixtures

---

## Migration from Old Code

If you're upgrading from the old version:

1. **Old `bulk_pdf_metadata_renamer.py`** → New `core/pdf_processor.py` + `core/metadata_fetcher.py`
2. **Old `link_analyze.py`** → New `analysis/keyword_extractor.py`
3. **Old `linker.py`** → New `core/linker.py` (now shared)
4. **Old `app.py`** → New `ui/app.py` (simplified, imports from core/)
5. **New `cli.py`** → Standalone CLI tool

All business logic is now in `pdfference/` package; UIs are just presentation layers.

---

## Development Workflow

### Adding a New Feature

1. **Write test first** in `tests/test_pdfference.py`
   ```python
   def test_my_feature(self):
       # Your test
       assert result == expected
   ```

2. **Implement in appropriate module**
   - PDF logic → `core/pdf_processor.py`
   - API calls → `core/metadata_fetcher.py`
   - Text analysis → `analysis/keyword_extractor.py`
   - UI → `ui/app.py` or `cli.py`

3. **Use centralized config**
   ```python
   from pdfference.config import Config
   # Don't hardcode paths/settings
   ```

4. **Use logger for feedback**
   ```python
   logger.info("Processing started")
   logger.error("Failed to fetch metadata")
   ```

5. **Run tests**
   ```bash
   pytest tests/ -v
   ```

### Code Quality

```bash
# Format code
black pdfference/ tests/ cli.py

# Check style
flake8 pdfference/ tests/ cli.py

# Type checking
mypy pdfference/ --ignore-missing-imports

# All checks
black pdfference/ && flake8 pdfference/ && mypy pdfference/ && pytest tests/
```

---

## Troubleshooting

### "No DOI found in PDF"
- Some PDFs don't have accessible text (scanned images)
- Try extracting text manually and adding DOI to filename

### "CrossRef lookup failed"
- Check internet connection
- DOI might be malformed
- Try directly: `https://api.crossref.org/works/{doi}`

### "No abstract available"
- CrossRef doesn't always include abstracts
- Try enabling PubMed fallback (happens automatically)
- Manually add abstract to note

### Streamlit runs but shows no output
- Check `pdfference/ui/app.py` imports
- Verify Python path includes project root
- Try running from project directory

---

## Performance Notes

- **PDF extraction**: ~1-2 sec per PDF (depends on file size)
- **Metadata fetching**: ~500ms per API call
- **Keyword extraction**: Scales with vault size; ~100ms per note
- **Wikilink application**: ~50ms per note

Typical workflow: 100 PDFs → ~2-3 minutes total

---

## Future Enhancements

- [ ] Batch PDF upload to UI
- [ ] Automatic DOI from CrossRef if not found in PDF
- [ ] Support for other metadata sources (DBLP, arXiv)
- [ ] Obsidian plugin instead of CLI
- [ ] Web API server (FastAPI)
- [ ] Database backend for tracking processing history
- [ ] Advanced NLP for better keyword extraction

---

## License

MIT License

Copyright (c) [year] [fullname]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.


## Support

For issues or questions, check existing GitHub issues or create a new one.
