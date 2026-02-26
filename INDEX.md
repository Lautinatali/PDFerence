# PDFerence Refactored - Module Index & Quick Reference

A professional Python package for PDF metadata extraction and Obsidian integration.

## 📚 Quick Navigation

### Refactoring Summary
- **[REFACTORING_COMPLETE.md](REFACTORING_COMPLETE.md)** - Detailed before/after comparison

### Documentation
- **[README.md](README.md)** - Full usage guide & API reference
- **[This file]** - Quick reference index

### Running the Application
```bash
# Streamlit UI
streamlit run pdfference/ui/app.py

# CLI tool
python cli.py --help

# Verification
python verify.py
```

---

## 🏗️ Module Reference

### **pdfference/config.py**
Single source of truth for all configuration.

```python
from pdfference.config import Config

Config.VAULT_PATH              # Obsidian vault location
Config.LOG_DIR                 # Logging directory
Config.STOP_WORDS              # Keywords to filter (set of 87 words)
Config.ACADEMIC_NOISE          # Phrases to exclude (set of 22 phrases)
Config.ABSTRACT_PLACEHOLDERS   # Placeholder strings to skip
Config.KEYWORDS_TO_LINK        # Default keywords for linking
Config.ensure_dirs()           # Create required directories
```

### **pdfference/core/models.py**
Type-safe domain models with proper structure.

```python
from pdfference.core.models import Paper, ProcessingResult, ProcessingStats

# Paper: Represents an academic paper
paper = Paper(
    doi="10.1234/test",
    title="...",
    authors=["Smith, John"],
    abstract="...",
    year=2023
)
paper.first_author_lastname    # "Smith"
paper.display_authors          # "Smith, John et al."

# ProcessingResult: Single PDF processing outcome
result = ProcessingResult(
    success=True,
    paper=paper,
    note_path=Path("note.md")
)

# ProcessingStats: Batch statistics
stats = ProcessingStats(processed=100, success=85, failed=15)
stats.success_rate             # 85.0
```

### **pdfference/core/pdf_processor.py**
Extract DOI from PDFs and organize files.

```python
from pdfference.core.pdf_processor import PDFProcessor

processor = PDFProcessor(logger)

# Extract DOI from PDF
doi = processor.extract_doi_from_pdf(Path("paper.pdf"))
# Returns: "10.1234/test" or None

# Rename and move PDF based on metadata
new_path = processor.organize_pdf(
    pdf_path=Path("paper.pdf"),
    dest_folder=Path("organized/"),
    paper=paper
)
```

### **pdfference/core/metadata_fetcher.py**
Intelligent fallback chain: CrossRef → OpenAlex → PubMed

```python
from pdfference.core.metadata_fetcher import MetadataFetcher

fetcher = MetadataFetcher(logger)

# Automatic fallback: CrossRef (first) → OpenAlex (abstract) → PubMed (fallback)
paper = fetcher.fetch("10.1234/test")
# Returns: Paper object or None
```

### **pdfference/core/note_generator.py**
Create Obsidian-compatible Markdown notes.

```python
from pdfference.core.note_generator import NoteGenerator

gen = NoteGenerator(logger)

# Generate Markdown with YAML frontmatter
md_content = gen.generate_markdown(paper)
# Returns: String with YAML + Abstract + Notes sections

# Save to file
note_path = gen.save_note(paper, Path("vault/Notes/"))
# Returns: Path to saved .md file
```

### **pdfference/core/linker.py**
Inject [[wikilinks]] into Markdown files (shared across UI + CLI).

```python
from pdfference.core.linker import Linker

linker = Linker(logger)

# Link text
result = linker.apply_links_to_text(
    content="Smooth muscle cells are important.",
    keywords={"Smooth muscle cells"}
)
# Returns: "[[Smooth muscle cells]] are important."

# Link single file
modified = linker.apply_links_to_file(
    file_path=Path("note.md"),
    keywords={"keyword1", "keyword2"}
)
# Returns: True if modified, False otherwise

# Link entire vault
processed, modified = linker.apply_links_to_vault(
    vault_path=Config.VAULT_PATH,
    keywords={"keyword1", "keyword2"}
)
# Returns: (total_files, modified_files) tuple
```

### **pdfference/analysis/keyword_extractor.py**
Extract and deduplicate n-grams with intelligent filtering.

```python
from pdfference.analysis.keyword_extractor import KeywordExtractor

extractor = KeywordExtractor(logger)

# Extract keywords from text
freq = extractor.extract("Text about smooth muscle cells...")
# Returns: Counter({'smooth muscle cells': 1, ...})

# Extract from entire vault
freq = extractor.extract_from_vault(
    vault_path=Config.VAULT_PATH,
    target_header="Abstract"
)

# Deduplicate and rank
top_keywords = extractor.deduplicate(freq, min_count=2)
# Returns: [('smooth muscle cells', 5), ('autophagy', 4), ...]
```

### **pdfference/utils/logger.py**
Unified logging: file + console + UI buffer.

```python
from pdfference.utils.logger import Logger

logger = Logger("MyModule", Config.LOG_DIR)

logger.info("Info message")         # File + console + UI
logger.warning("Warning message")   # File + console + UI
logger.error("Error message")       # File + console + UI
logger.success("Success!")          # File + console + UI
logger.debug("Debug info")          # File only

# Get output for Streamlit
ui_output = logger.get_ui_output()  # Formatted string with timestamps
logger.clear_ui_buffer()            # Reset buffer
```

### **pdfference/ui/app.py**
Streamlit web interface (UI layer only, imports from core/).

```bash
streamlit run pdfference/ui/app.py
```

Features:
- Stage 1: **Select** - Choose PDF folder and vault path
- Stage 2: **Process** - Extract metadata from PDFs
- Stage 3: **Keywords** - Extract and select keywords
- Stage 4: **Links** - Apply wikilinks to vault

### **cli.py**
Standalone command-line interface (reuses all core modules).

```bash
# Process PDFs
python cli.py process-pdfs "path/to/pdfs" -o "path/to/vault"

# Extract keywords
python cli.py extract-keywords -v "vault/path" --min-count 2 --limit 100

# Apply wikilinks
python cli.py apply-links -v "vault/path" -k keywords.csv
```

---

## 🧪 Testing

### Run All Tests
```bash
pytest tests/ -v
```

### Test Files
- **tests/test_pdfference.py** - Unit + integration tests
- **tests/conftest.py** - pytest fixtures

### Test Coverage
```bash
pytest tests/ --cov=pdfference --cov-report=html
```

### Test Categories
✅ **Models** - Dataclass functionality
✅ **PDF Processing** - DOI extraction, file organization
✅ **Metadata Fetching** - API integration
✅ **Note Generation** - Markdown formatting
✅ **Keyword Extraction** - Tokenization, filtering, deduplication
✅ **Linking** - Wikilink injection
✅ **Logging** - File & UI output
✅ **Integration** - Full workflows

---

## 📊 Code Quality

### Linting
```bash
flake8 pdfference/ tests/ cli.py
```

### Type Checking
```bash
mypy pdfference/ --ignore-missing-imports
```

### Code Formatting
```bash
black pdfference/ tests/ cli.py
```

### Full Check
```bash
black pdfference/ && flake8 pdfference/ && mypy pdfference/ && pytest tests/
```

---

## 🔄 Typical Workflows

### Workflow 1: Streamlit UI (Simplest)
```bash
streamlit run pdfference/ui/app.py
# 1. Click "Start Processing"
# 2. Follow the 4-stage wizard
```

### Workflow 2: CLI Scripting (Most Powerful)
```bash
python cli.py process-pdfs "C:\PDFs" -o "G:\Vault"
python cli.py extract-keywords -v "G:\Vault" -o keywords.csv
python cli.py apply-links -v "G:\Vault" -k keywords.csv
```

### Workflow 3: Python API (Custom Automation)
```python
from pathlib import Path
from pdfference.config import Config
from pdfference.core.pdf_processor import PDFProcessor
from pdfference.core.metadata_fetcher import MetadataFetcher
from pdfference.core.note_generator import NoteGenerator
from pdfference.utils.logger import Logger

logger = Logger("MyScript", Config.LOG_DIR)
processor = PDFProcessor(logger)
fetcher = MetadataFetcher(logger)
generator = NoteGenerator(logger)

for pdf_file in Path("pdfs").glob("*.pdf"):
    doi = processor.extract_doi_from_pdf(pdf_file)
    if doi:
        paper = fetcher.fetch(doi)
        if paper:
            generator.save_note(paper, Config.VAULT_PATH)
```

---

## 📋 Configuration

### Environment Variables (.env)
```env
VAULT_PATH=G:\Mi unidad\vault
PUBMED_EMAIL=your.email@example.com
```

### Python Configuration
Edit `pdfference/config.py` for:
- API timeouts
- Stop words
- Academic noise phrases
- Keywords to link
- N-gram sizes

---

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'pdfference'"
- Ensure you're running from project root directory
- Or install: `pip install -e .` (editable mode)

### "Logger writes nothing"
- Check `Config.LOG_DIR` exists
- See logs at: `logs/ModuleName_TIMESTAMP.log`

### "Streamlit runs but no output"
- Try: `streamlit run pdfference/ui/app.py --logger.level=debug`
- Check browser console for errors

### "PDF metadata not found"
- Use [verify.py](verify.py) to test API connectivity
- CrossRef might not have abstract for all papers
- PubMed fallback may help

---

## 📦 Dependencies

Core:
- `requests` - HTTP API calls
- `PyMuPDF` (fitz) - PDF text extraction
- `beautifulsoup4` - XML parsing for PubMed

UI:
- `streamlit` - Web interface

Development:
- `pytest` - Testing
- `black` - Code formatter
- `flake8` - Linter
- `mypy` - Type checker

See [requirements.txt](requirements.txt) for full list.

---

## 🎯 Quick Checklist

Starting fresh?
- [ ] Copy `.env.example` to `.env` and configure
- [ ] Install: `pip install -r requirements.txt`
- [ ] Verify: `python verify.py` (should show all ✅)
- [ ] Test: `pytest tests/ -v` (should pass)
- [ ] Run UI: `streamlit run pdfference/ui/app.py`

---

## 📖 Further Reading

- [README.md](README.md) - Full documentation
- [REFACTORING_COMPLETE.md](REFACTORING_COMPLETE.md) - Architecture changes
- [tests/test_pdfference.py](tests/test_pdfference.py) - Code examples in tests

---

**Version:** 0.2.0 (Refactored)  
**Last Updated:** February 26, 2026  
**Status:** ✅ Production Ready
