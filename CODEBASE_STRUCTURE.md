# PDFerence Codebase Structure & Function Documentation

## Project Overview

**PDFerence** is a tool that processes academic PDFs, extracts metadata via CrossRef/OpenAlex/PubMed APIs, and creates linked notes in Obsidian vaults. It automates the workflow of: (1) extracting DOIs from PDFs, (2) fetching complete metadata, (3) generating Obsidian notes, and (4) creating wikilinks between notes.

### High-Level Workflow

```
PDF File → Extract DOI → Fetch Metadata → Generate Note → Create Wikilinks
   ↓              ↓             ↓              ↓              ↓
[File]      [doi string]  [Paper object] [Markdown]   [Obsidian vault]
```

---

## Directory Structure

```
PDFerence/
├── pdfference/                  # Main package (business logic)
│   ├── config.py               # Centralized configuration
│   ├── __init__.py
│   ├── core/                   # Core data processing
│   │   ├── models.py           # Data classes (Paper, ProcessingResult, etc.)
│   │   ├── pdf_processor.py    # DOI extraction from PDFs
│   │   ├── metadata_fetcher.py # Multi-source API fallback chain
│   │   ├── note_generator.py   # Convert metadata → Markdown
│   │   ├── linker.py           # Inject wikilinks into notes
│   │   └── __init__.py
│   ├── analysis/               # Text analysis & extraction
│   │   ├── keyword_extractor.py # N-gram extraction, deduplication
│   │   └── __init__.py
│   ├── utils/                  # Utility modules
│   │   ├── logger.py           # Unified logging system
│   │   └── __init__.py
│   └── ui/                     # User interfaces
│       ├── app.py              # Streamlit web UI
│       └── __init__.py
├── cli.py                      # Standalone CLI tool
├── tests/                      # Test suite
│   ├── conftest.py             # pytest fixtures
│   └── test_pdfference.py      # Unit & integration tests
├── Legacy/                     # Old code (for reference)
├── requirements.txt            # Dependencies
├── setup.py                    # Package installation config
├── README.md                   # User documentation
├── .env.example                # Environment template
├── .env                        # Local environment (git-ignored)
└── CODEBASE_STRUCTURE.md       # This file
```

---

## Core Modules Reference

### 1. **config.py** — Centralized Configuration

**Purpose**: Single source of truth for all settings (paths, timeouts, API keys, keyword lists).

**Key Constants**:
- `VAULT_PATH`: Obsidian vault location (from `.env`)
- `OBSIDIAN_OUTPUT`: Where notes are saved (`{VAULT_PATH}/Notes`)
- `STOP_WORDS`: Words to ignore in keyword extraction (the, and, etc.)
- `ACADEMIC_NOISE`: Phrases to filter (expression of, role in, etc.)
- `KEYWORDS_TO_LINK`: Keywords to auto-link (Smooth Muscle Cells, m6A, etc.)
- `PUBMED_EMAIL`: Email for PubMed API

**Key Methods**:
- `ensure_dirs()`: Create required directories if missing

**Usage**:
```python
from pdfference.config import Config
print(Config.VAULT_PATH)
print(Config.STOP_WORDS)
```

---

### 2. **core/models.py** — Data Classes

**Purpose**: Type-safe domain models for the application.

#### `Paper` (Dataclass)
Represents an academic paper with metadata.

**Fields**:
- `doi: str` — Digital Object Identifier
- `title: str` — Paper title
- `authors: list[str]` — Authors in format "LastName, FirstName"
- `abstract: str` — Paper abstract
- `year: Optional[int]` — Publication year
- `journal: Optional[str]` — Journal/conference name
- `url: Optional[str]` — Paper URL
- `topics: list[str]` — Research topics/categories

**Properties**:
- `first_author_lastname`: Extract last name of first author safely
- `display_authors`: Formatted string like "Smith et al." or single author name

**Example**:
```python
paper = Paper(
    doi="10.1234/test",
    title="Study of X",
    authors=["Smith, John", "Doe, Jane"],
    abstract="This paper...",
    year=2023,
    journal="Nature"
)
print(paper.first_author_lastname)  # "Smith"
print(paper.display_authors)        # "Smith et al."
```

#### `ProcessingResult` (Dataclass)
Result of processing a single PDF.

**Fields**:
- `success: bool` — Whether processing succeeded
- `pdf_path: Optional[Path]` — Original PDF file path
- `paper: Optional[Paper]` — Extracted metadata (if success)
- `note_path: Optional[Path]` — Generated note file path
- `error_message: Optional[str]` — Error details if failed

**Example**:
```python
result = ProcessingResult(success=True, paper=paper, note_path=Path(...))
print(result)  # "✅ Smith2023Study of X.md"
```

#### `ProcessingStats` (Dataclass)
Statistics from batch processing.

**Fields**:
- `processed: int` — Total files processed
- `success: int` — Successfully processed
- `failed: int` — Failed files
- `duplicates: int` — Duplicate files skipped

**Properties**:
- `success_rate`: Percentage of successful processes

**Example**:
```python
stats = ProcessingStats(processed=100, success=95, failed=5)
print(stats)  # "Processed: 100 | Success: 95 | Failed: 5 | Success Rate: 95.0%"
```

---

### 3. **core/pdf_processor.py** — DOI Extraction & File Organization

**Purpose**: Extract DOI from PDF text and organize/rename PDF files.

#### `PDFProcessor` (Class)

**Constructor**:
```python
processor = PDFProcessor(logger=None)
```

**Key Methods**:

##### `extract_doi_from_pdf(pdf_path: Path) -> Optional[str]`
Extracts DOI from PDF text with robust preprocessing.

**Steps**:
1. Opens PDF and extracts all text
2. Removes hyphens at line ends (fixes split words)
3. Normalizes line breaks and spaces
4. Searches for DOI pattern: `10.XXXX/...`
5. Cleans trailing punctuation

**Returns**: DOI string like `10.1234/test` or `None` if not found

**Example**:
```python
processor = PDFProcessor()
doi = processor.extract_doi_from_pdf(Path("paper.pdf"))
# Returns: "10.1234/test"
```

##### `organize_pdf(pdf_path, dest_folder, paper, check_exists, move_to_input) -> Path`
Rename and move PDF based on metadata.

**Parameters**:
- `pdf_path`: Current location
- `dest_folder`: Note destination (not PDF destination)
- `paper`: Paper object with metadata
- `check_exists`: Raise error if file already exists
- `move_to_input`: Move to `Input/` subfolder

**Returns**: New PDF path

**Naming Pattern**: `{FirstAuthorLastName} - {Year} - {CleanedTitle}.pdf`

**Example**:
```python
new_path = processor.organize_pdf(
    pdf_path=Path("paper.pdf"),
    dest_folder=Path("vault/Notes"),
    paper=paper
)
# Moves to: "Input/Smith - 2023 - Study of X.pdf"
```

---

### 4. **core/metadata_fetcher.py** — Multi-Source API Integration

**Purpose**: Fetch paper metadata with intelligent fallback chain.

#### `MetadataFetcher` (Class)

**Fallback Chain** (in order):
1. **CrossRef** (primary) → Fast, reliable for basic metadata
2. **OpenAlex** (enhancement) → Better abstracts, topics
3. **PubMed** (fallback) → For biomedical papers

#### `fetch(doi: str) -> Optional[Paper]`
Main method: fetches complete metadata via fallback chain.

**Process**:
1. Clean DOI (remove URL prefix if present)
2. Try CrossRef API → If fails, return None
3. If CrossRef succeeds, try to enhance with OpenAlex (abstract + topics)
4. If abstract still missing, try PubMed fallback
5. Ensure abstract is never empty (use placeholder)

**Returns**: `Paper` object or `None`

**Example**:
```python
fetcher = MetadataFetcher()
paper = fetcher.fetch("10.1234/test")
# Returns: Paper(title="...", authors=[...], abstract="...", topics=[...])
```

#### `_from_crossref(doi: str) -> Optional[Paper]`
Queries CrossRef API at `https://api.crossref.org/works/{doi}`.

**Extracts**:
- Title, authors (in format "LastName, FirstName")
- Year, journal, abstract, URL
- Handles missing fields gracefully

#### `_from_openalex(doi: str) -> Optional[dict]`
Queries OpenAlex API at `https://api.openalex.org/works/https://doi.org/{doi}`.

**Extracts**:
- Abstract (rebuilt from inverted index format)
- Topics (list of research categories)

**Note**: OpenAlex returns abstracts in inverted index format (position-based), must be rebuilt.

#### `_from_pubmed(doi: str) -> Optional[str]`
Fallback for biomedical papers.

**Two-step process**:
1. Search by DOI → get PMID (PubMed ID)
2. Fetch XML record → extract abstract

**Requires**: `PUBMED_EMAIL` in config

#### `_rebuild_abstract_from_index(inverted_index) -> Optional[str]`
Reconstructs abstract from OpenAlex inverted index format.

**Format**: `{"word": [position1, position2], ...}` → "word word..."

---

### 5. **core/note_generator.py** — Markdown Generation

**Purpose**: Convert paper metadata into Obsidian-compatible Markdown notes.

#### `NoteGenerator` (Class)

#### `generate_markdown(paper: Paper) -> str`
Generate Markdown content with YAML frontmatter.

**Output Format**:
```markdown
---
title: "Paper Title"
authors: [Author1, Author2, ...]
journal: "Journal Name"
year: 2023
doi: 10.1234/test
topics: [topic1, topic2]
tags: [unread]
url: https://doi.org/10.1234/test
---

# 📄 Abstract

{abstract text}

# 🧠 Personal Notes

- 

# 🔗 Why does it matter?
```

**YAML Escaping**: Special characters like `"` and `:` are escaped for YAML compatibility.

#### `save_note(paper: Paper, output_dir: Path) -> Path`
Save Markdown note to file.

**Naming Pattern**: `{FirstAuthorLastName} {Year} - {CleanedTitle}.md`

**Process**:
1. Create output directory if missing
2. Generate Markdown content
3. Write to file with UTF-8 encoding
4. Return file path

**Example**:
```python
gen = NoteGenerator()
note_path = gen.save_note(paper, Path("vault/Notes"))
# Saves: "vault/Notes/Smith 2023 - Study of X.md"
```

#### `_escape_yaml(text: str) -> str`
Escape special YAML characters in field values.

#### `_clean_filename(text: str) -> str`
Remove illegal filesystem characters from text.

---

### 6. **core/linker.py** — Wikilink Injection

**Purpose**: Convert keyword mentions to `[[wikilinks]]` in Markdown files.

#### `Linker` (Class)

#### `apply_links_to_text(content: str, keywords: Set[str], skip_yaml: bool) -> str`
Replace keyword occurrences with wikilinks in content.

**Process**:
1. Optionally split YAML frontmatter (skip if `skip_yaml=True`)
2. For each keyword (longest first to avoid partial matches):
   - Find word boundaries using regex
   - Skip if already linked `[[...]]`
   - Replace with `[[keyword]]` or `[[keyword|ActualText]]` (case-insensitive alias)
3. Reconstruct content with YAML intact

**Example**:
```python
linker = Linker()
text = "Smooth Muscle Cells are important in development"
keywords = {"Smooth Muscle Cells", "development"}
result = linker.apply_links_to_text(text, keywords)
# Result: "[[Smooth Muscle Cells]] are important in [[development]]"
```

#### `apply_links_to_file(file_path: Path, keywords: Set[str], skip_yaml: bool) -> bool`
Apply wikilinks to a single Markdown file in-place.

**Returns**: `True` if file was modified, `False` otherwise

**Example**:
```python
modified = linker.apply_links_to_file(Path("note.md"), keywords)
```

#### `apply_links_to_vault(vault_path: Path, keywords: Set[str], skip_yaml: bool) -> tuple[int, int]`
Apply wikilinks to all `.md` files in vault recursively.

**Returns**: `(total_processed, total_modified)`

**Example**:
```python
processed, modified = linker.apply_links_to_vault(Path("vault"), keywords)
# Returns: (150, 45) — processed 150 files, modified 45
```

---

### 7. **analysis/keyword_extractor.py** — N-gram Analysis

**Purpose**: Extract meaningful keywords (n-grams) from text, filter noise, deduplicate.

#### `KeywordExtractor` (Class)

#### `extract(text: str, min_gram: int, max_gram: int) -> Counter`
Extract n-grams from text with noise filtering.

**Process**:
1. Tokenize text (lowercase, remove punctuation)
2. Generate n-grams from size `min_gram` to `max_gram` (1=unigrams, 3=trigrams)
3. Filter out stop words and academic noise
4. Return frequency counter

**Returns**: `Counter` object (dict-like with word frequencies)

**Example**:
```python
extractor = KeywordExtractor()
freq = extractor.extract("Smooth muscle cells regulate autophagy", min_gram=1, max_gram=2)
# Returns: Counter({"smooth muscle": 1, "muscle cells": 1, "autophagy": 1, ...})
```

#### `extract_from_vault(vault_path, target_header, min_gram, max_gram) -> Counter`
Extract keywords from all notes in vault under specific header.

**Parameters**:
- `vault_path`: Root path of vault
- `target_header`: Section to extract from (e.g., "Abstract")
- `min_gram`, `max_gram`: N-gram range

**Process**:
1. Find all `.md` files recursively
2. For each file, extract section under header
3. Run `extract()` on that section
4. Aggregate frequencies across all files

**Returns**: Combined `Counter` of all keywords

#### `deduplicate(freq: Counter, min_count: int) -> list[tuple[str, int]]`
Remove substring redundancy; prefer longer, more frequent forms.

**Process**:
1. Filter by minimum count threshold
2. Check if shorter phrases are substrings of longer ones
3. If yes and longer phrase is frequent enough (1.5×), mark as redundant
4. Sort by frequency (descending)

**Purpose**: Avoid duplicate entries like both "muscle cells" and "smooth muscle cells"

**Example**:
```python
freq = Counter({"smooth": 10, "muscle": 8, "smooth muscle": 15, "cells": 5})
result = extractor.deduplicate(freq, min_count=2)
# Result: [("smooth muscle", 15), ("smooth", 10), ("muscle", 8), ("cells", 5)]
# "smooth" and "muscle" aren't removed because they appear independently often enough
```

#### `_tokenize(text: str) -> list[str]`
Tokenize text with Unicode normalization and placeholder filtering.

**Process**:
1. Check for placeholder strings ("no abstract available")
2. Normalize Unicode superscripts/subscripts to regular chars (⁶→6, ᴬ→A)
3. Replace separators (-, /) with spaces
4. Remove non-alphanumeric characters (except accents)
5. Split into tokens and lowercase

**Returns**: List of lowercase tokens

#### `_is_valid_gram(gram: list[str]) -> bool`
Check if n-gram is meaningful.

**Rules**:
- Don't start/end with stop words
- Don't include academic noise phrases
- Minimum 3 characters long
- Not in stop word list

**Example**:
```python
valid = extractor._is_valid_gram(["smooth", "muscle", "cells"])  # True
invalid = extractor._is_valid_gram(["the", "study"])             # False (starts with stop word)
```

#### `_normalize_unicode_char(char: str) -> str`
Convert Unicode superscripts/subscripts to regular characters.

**Mappings**:
- Superscript: `⁶` → `6`, `ᴬ` → `A`
- Subscript: `₆` → `6`, `ₐ` → `a`

#### `_extract_section(content: str, header: str) -> str`
Extract content under specific Markdown header.

**Example**:
```python
text = """# Title
Content

# Abstract
This is the abstract

# Methods
More text"""

result = extract_section(text, "Abstract")
# Returns: "This is the abstract"
```

---

### 8. **utils/logger.py** — Unified Logging

**Purpose**: Single logging system for file, console, and Streamlit UI feedback.

#### `Logger` (Class)

**Constructor**:
```python
logger = Logger(name="MyModule", log_dir=Path("./logs"))
```

**Creates**:
- Timestamped log file in `{log_dir}/{name}_{timestamp}.log`
- Console output (INFO level and above)
- UI buffer for Streamlit display

#### Logging Methods:

- `debug(msg)` — File only (DEBUG level)
- `info(msg)` — File + console + UI (ℹ️  emoji)
- `warning(msg)` — File + console + UI (⚠️  emoji)
- `error(msg)` — File + console + UI (❌ emoji)
- `success(msg)` — File + console + UI (✅ emoji)

**Example**:
```python
logger = Logger("PDFProcessor")
logger.info("Starting PDF processing")
logger.success("Note saved: Smith 2023.md")
logger.error("Failed to fetch metadata")
```

#### UI Methods:

- `get_ui_output() -> str` — Return formatted lines for Streamlit display
- `clear_ui_buffer()` — Clear after rendering

**Example (in Streamlit)**:
```python
logger = Logger("Streamlit")
# ... processing ...
st.text(logger.get_ui_output())
logger.clear_ui_buffer()
```

---

### 9. **cli.py** — Standalone CLI Tool

**Purpose**: Command-line interface for all PDFerence operations.

**Architecture**: Reuses all `core/` modules without Streamlit dependency

#### Commands:

##### `process-pdfs <input_folder> [-o output_folder]`
Process PDFs and extract metadata.

**Steps**:
1. Iterate through all `.pdf` files
2. Extract DOI using `PDFProcessor`
3. Fetch metadata using `MetadataFetcher`
4. Save note using `NoteGenerator`
5. Track statistics (success/failed)

**Example**:
```bash
python cli.py process-pdfs "C:\PDFs" -o "C:\Vault\Notes"
```

**Output**: Success/failure counts and statistics

##### `extract-keywords [-v vault] [--header Header] [-m min_count] [-o output.csv]`
Extract keywords from vault notes.

**Steps**:
1. Iterate through vault notes
2. Extract keywords using `KeywordExtractor.extract_from_vault()`
3. Deduplicate results
4. Export to CSV: `keyword,frequency`

**Example**:
```bash
python cli.py extract-keywords -v "C:\Vault" --header "Abstract" -o keywords.csv
```

**Output CSV**:
```
keyword,frequency
"smooth muscle cells",42
"autophagy",38
"m6A",35
```

##### `apply-links [-v vault] [-k keywords.csv]`
Apply wikilinks to vault notes.

**Steps**:
1. Load keywords from CSV file (or use defaults from config)
2. Apply wikilinks using `Linker.apply_links_to_vault()`
3. Report files processed and modified

**Example**:
```bash
python cli.py apply-links -v "C:\Vault" -k keywords.csv
```

**Output**: "Applied links: 150 files processed, 45 modified"

---

## Entry Points

### 1. **Streamlit UI** (`pdfference/ui/app.py`)
Web interface for interactive processing.

**Start**: `streamlit run pdfference/ui/app.py`

### 2. **CLI Tool** (`cli.py`)
Command-line interface for automation/scripting.

**Start**: `python cli.py <command> [options]`

### 3. **Python API** (Direct imports)
Use modules directly in Python scripts.

```python
from pdfference.core.pdf_processor import PDFProcessor
from pdfference.core.metadata_fetcher import MetadataFetcher
from pdfference.core.note_generator import NoteGenerator

processor = PDFProcessor()
fetcher = MetadataFetcher()
generator = NoteGenerator()

# Your logic here
```

---

## Data Flow Examples

### Complete Workflow: PDF → Note → Wikilinks

```python
from pathlib import Path
from pdfference.config import Config
from pdfference.core.pdf_processor import PDFProcessor
from pdfference.core.metadata_fetcher import MetadataFetcher
from pdfference.core.note_generator import NoteGenerator
from pdfference.core.linker import Linker
from pdfference.analysis.keyword_extractor import KeywordExtractor
from pdfference.utils.logger import Logger

# Initialize
logger = Logger("MyWorkflow", Config.LOG_DIR)
processor = PDFProcessor(logger)
fetcher = MetadataFetcher(logger)
generator = NoteGenerator(logger)
linker = Linker(logger)
extractor = KeywordExtractor(logger)

# Step 1: Process PDF
pdf_path = Path("paper.pdf")
doi = processor.extract_doi_from_pdf(pdf_path)
if not doi:
    logger.error("No DOI found")
    exit(1)

# Step 2: Fetch metadata
paper = fetcher.fetch(doi)
if not paper:
    logger.error("Could not fetch metadata")
    exit(1)

# Step 3: Generate note
note_path = generator.save_note(paper, Config.OBSIDIAN_OUTPUT)

# Step 4: Extract keywords from vault
vault_path = Config.VAULT_PATH
freq = extractor.extract_from_vault(vault_path)
keywords = {word for word, count in extractor.deduplicate(freq)}

# Step 5: Apply wikilinks
processed, modified = linker.apply_links_to_vault(vault_path, keywords)
logger.success(f"Complete! Modified {modified}/{processed} files")
```

---

## Configuration System

All settings are in `config.py` and can be overridden via environment variables (`.env`).

**Key Config Values**:

| Variable | Default | Purpose |
|----------|---------|---------|
| `VAULT_PATH` | `G:\Mi unidad\Input_network\Input_network` | Obsidian vault location |
| `PUBMED_EMAIL` | `lnatali@immf.uncor.edu` | Email for PubMed API |
| `MOVE_PDFS_TO_INPUT` | `true` | Move PDFs to Input/ after processing |
| `STOP_WORDS` | Set of 50+ common words | Words to ignore in keyword extraction |
| `KEYWORDS_TO_LINK` | ["Smooth Muscle Cells", "m6A", ...] | Keywords to auto-link in vault |

**Override via `.env`**:
```env
VAULT_PATH=/custom/vault/path
PUBMED_EMAIL=myemail@example.com
```

---

## Error Handling Strategy

- **Silent failures avoided**: All functions log errors
- **Graceful degradation**: Uses fallback chain (CrossRef → OpenAlex → PubMed)
- **Empty abstract never returned**: Always has a value (at least "No abstract available.")
- **File operations**: Check for existing files, create directories as needed
- **API calls**: Timeout protection and exception handling on all requests

---

## Performance Notes

- **PDF text extraction**: ~1-2 sec per PDF (depends on file size and structure)
- **API calls**: ~500ms per request (with fallback chain)
- **Keyword extraction**: ~100ms per note (scales with vault size)
- **Wikilink application**: ~50ms per note

**Typical workflow**: 100 PDFs → ~2-3 minutes total

---

## Testing

Run pytest suite:
```bash
pytest tests/ -v                    # Run all tests
pytest tests/test_pdfference.py -v  # Specific file
pytest --cov=pdfference             # With coverage report
```

Test file: `tests/test_pdfference.py`
Fixtures: `tests/conftest.py`

---

## Legacy Code

Old files in `Legacy/` folder (kept for reference):
- `bulk_pdf_metadata_renamer.py` → Replaced by `core/pdf_processor.py` + `core/metadata_fetcher.py`
- `link_analyze.py` → Replaced by `analysis/keyword_extractor.py`
- `linker.py` → Replaced by `core/linker.py`
- `app.py` → Replaced by `ui/app.py`

New codebase centralizes all business logic in `pdfference/` package; UIs are just presentation layers.

---

## Summary

**PDFerence** follows a **clean architecture** pattern:

- **Data models** (`models.py`) — Define domain objects
- **Core processors** (`pdf_processor.py`, `metadata_fetcher.py`, `note_generator.py`, `linker.py`) — Transform data
- **Analysis** (`keyword_extractor.py`) — Extract insights
- **Utils** (`logger.py`) — Cross-cutting concerns
- **Config** (`config.py`) — Centralized settings
- **UIs** (`cli.py`, `ui/app.py`) — Presentation layers

All modules are **reusable, testable, and loosely coupled** through dependency injection (logger, config).
