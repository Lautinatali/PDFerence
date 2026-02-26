# PDFerence: PDF Metadata Processor with Obsidian Integration

A professional-grade tool for processing academic PDFs, extracting metadata via CrossRef/OpenAlex/PubMed APIs, and creating linked notes in your Obsidian vault.

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
│   └── linker.py          # ✅ Shared wikilink injection logic
├── analysis/
│   └── keyword_extractor.py # ✅ N-gram extraction + deduplication
├── utils/
│   └── logger.py          # ✅ Unified logging system
└── ui/
    └── app.py             # ✅ Streamlit UI (pure presentation)
cli.py                      # ✅ Standalone CLI tool
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

Then:
1. **Select** folder with PDFs and vault path
2. **Process** PDFs → extracts metadata, creates notes
3. **Extract Keywords** from vault abstracts
4. **Apply Wikilinks** to create [[links]]

### Using the CLI

```bash
# Process PDFs to notes
python cli.py process-pdfs "path/to/pdfs" -o "path/to/vault"

# Extract keywords to CSV
python cli.py extract-keywords -v "path/to/vault" -o keywords.csv

# Apply wikilinks using keyword file
python cli.py apply-links -v "path/to/vault" -k keywords.csv
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

### `analysis/keyword_extractor.py`
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

## Testing

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

[Your License Here]

## Support

For issues or questions, check existing GitHub issues or create a new one.
