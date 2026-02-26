"""
PDF Metadata Processor — Streamlit Interface
============================================
Stage flow:
    select  →  processing  →  keywords  →  done
"""

import streamlit as st
import re
from pathlib import Path
from collections import Counter
from datetime import datetime

# ── page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PDF Processor",
    page_icon="📄",
    layout="wide",
)

# ── session state bootstrap ───────────────────────────────────────────────────
defaults = {
    "stage": "select",
    "folder_path": "",
    "obsidian_path": "",
    "log_lines": [],
    "stats": {"processed": 0, "success": 0, "failed": 0, "duplicates": 0},
    "processing_done": False,   # guard: prevents re-running process_folder on rerun
    # keyword stage
    "keyword_freq": {},       # {word: count}
    "selected_keywords": set(),
    "processed_papers": [],   # list of dicts with paper info for linking
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def log(msg: str):
    """Append a timestamped line to the session log."""
    ts = datetime.now().strftime("%H:%M:%S")
    st.session_state.log_lines.append(f"[{ts}] {msg}")


def advance_to(stage: str):
    st.session_state.stage = stage
    st.rerun()


# ──────────────────────────────────────────────────────────────────────────────
# Import your existing functions here.
# We wrap every call so the UI never crashes if the module isn't available yet.
# ──────────────────────────────────────────────────────────────────────────────
try:
    from bulk_pdf_metadata_renamer import (
        extract_doi_from_pdf,
        get_metadata_from_doi,
        clean_for_filename,
    )
    from import_requests import (
        get_metadata_from_openalex,
        format_metadata_as_markdown,
        save_note_as_markdown,
    )
    MODULES_AVAILABLE = True
except ImportError as _e:
    MODULES_AVAILABLE = False
    _import_error = str(_e)


# ══════════════════════════════════════════════════════════════════════════════
# CORE PROCESSING  (replaces rename_pdfs_in_folder but streams to the UI)
# ══════════════════════════════════════════════════════════════════════════════

def process_folder(folder_path: str, obsidian_path: str, log_box):
    """
    Process all PDFs in folder_path, writing notes to obsidian_path.
    Streams log lines into log_box (an st.empty() container).
    Returns (stats dict, keyword_freq dict, processed_papers list).
    """
    folder = Path(folder_path)
    input_folder    = folder / "Input";      input_folder.mkdir(exist_ok=True)
    error_folder    = folder / "Error";      error_folder.mkdir(exist_ok=True)
    duplicates_folder = folder / "Duplicates"; duplicates_folder.mkdir(exist_ok=True)

    stats = {"processed": 0, "success": 0, "failed": 0, "duplicates": 0}
    keyword_freq: Counter = Counter()
    processed_papers = []

    pdf_files = list(folder.glob("*.pdf"))
    if not pdf_files:
        log("⚠️  No PDF files found in the selected folder.")
        _render_log(log_box)
        return stats, {}, []

    progress = st.progress(0)

    for i, pdf_file in enumerate(pdf_files):
        stats["processed"] += 1
        log(f"📄  Processing: {pdf_file.name}")
        _render_log(log_box)

        # ── DOI extraction ────────────────────────────────────────────────
        doi = extract_doi_from_pdf(pdf_file)
        if doi and doi[-1] in ".);":
            doi = doi[:-1]

        if not doi:
            log(f"   ❌  DOI not found — moved to Error/")
            pdf_file.rename(error_folder / pdf_file.name)
            stats["failed"] += 1
            _render_log(log_box)
            progress.progress((i + 1) / len(pdf_files))
            continue

        log(f"   🔍  DOI: {doi}")
        _render_log(log_box)

        # ── Rename & move PDF ────────────────────────────────────────────
        try:
            metadata = get_metadata_from_doi(doi)
            first_author = metadata["authors"][0].split(",")[0] if metadata["authors"] else "unknown"
            safe_title   = clean_for_filename(metadata["title"])
            new_name     = f"{first_author} - {metadata['year']} - {safe_title}.pdf"
            new_path     = input_folder / new_name
            pdf_file.rename(new_path)
            log(f"   ✅  Renamed → {new_name}")

        except FileExistsError:
            log(f"   ⚠️  Duplicate filename — moved to Duplicates/")
            pdf_file.rename(duplicates_folder / pdf_file.name)
            stats["duplicates"] += 1
            _render_log(log_box)
            progress.progress((i + 1) / len(pdf_files))
            continue

        except Exception as e:
            log(f"   ❌  Error renaming: {e}")
            if pdf_file.exists():
                pdf_file.rename(error_folder / pdf_file.name)
            stats["failed"] += 1
            _render_log(log_box)
            progress.progress((i + 1) / len(pdf_files))
            continue

        # ── Obsidian note + keyword harvest ─────────────────────────────
        try:
            note_metadata = get_metadata_from_openalex(doi)
            md_content    = format_metadata_as_markdown(note_metadata)

            # Snapshot existing .md files so we can detect which one is new
            obsidian_dir = Path(obsidian_path)
            before = set(obsidian_dir.glob("*.md"))

            save_note_as_markdown(md_content, note_metadata, obsidian_path)

            # Detect the actual file that was written — don't guess the name
            after   = set(obsidian_dir.glob("*.md"))
            new_mds = after - before
            if new_mds:
                actual_md_path = max(new_mds, key=lambda p: p.stat().st_mtime)
            else:
                # Note already existed and was updated in-place; find by newest mtime
                actual_md_path = max(after, key=lambda p: p.stat().st_mtime)

            log(f"   📝  Obsidian note → {actual_md_path.name}")

            # Harvest keywords from abstract + title using the full n-gram pipeline
            abstract = note_metadata.get("abstract", "") or ""
            title    = note_metadata.get("title", safe_title) or ""
            keyword_freq.update(extract_keywords_from_text(abstract + " " + title))

            processed_papers.append({
                "doi": doi,
                "title": note_metadata.get("title", safe_title),
                "author": first_author,
                "year": metadata["year"],
                "abstract": abstract,
                "md_path": actual_md_path,   # ← real path, not a guess
            })

            stats["success"] += 1

        except Exception as e:
            log(f"   ⚠️  Note creation error: {e}")
            stats["success"] += 1   # PDF was renamed OK

        _render_log(log_box)
        progress.progress((i + 1) / len(pdf_files))

    # Write log file next to the folder
    log_path = folder / "process_log.txt"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
            f"Processed: {stats['processed']}, Success: {stats['success']}, "
            f"Failed: {stats['failed']}, Duplicates: {stats['duplicates']}\n"
        )

    # Deduplicate before handing off to the keyword stage.
    # _deduplicate_concepts returns a sorted list of (concept, count) tuples.
    deduped = _deduplicate_concepts(keyword_freq, min_count=2)
    return stats, dict(deduped), processed_papers


# ══════════════════════════════════════════════════════════════════════════════
# KEYWORD EXTRACTION ENGINE  (ported from link_analyze.py)
# ══════════════════════════════════════════════════════════════════════════════

# Placeholder strings that mean "no abstract" — skip these entirely
_ABSTRACT_PLACEHOLDERS = {"no abstract available", "abstract available", "no abstract"}

_STOP_WORDS = {
    'of', 'in', 'to', 'for', 'with', 'on', 'at', 'by', 'from', 'is', 'are', 'was', 'were',
    'the', 'a', 'an', 'and', 'or', 'as', 'be', 'been', 'being', 'it', 'its', 'this', 'that',
    'which', 'who', 'these', 'those', 'we', 'our', 'their', 'they', 'into', 'has', 'have',
    'not', 'but', 'than', 'more', 'also', 'such', 'very', 'can', 'may', 'however', 'during',
    'specific', 'factor', 'identified', 'using', 'well', 'both', 'between', 'through',
    'here', 'there', 'results', 'associated', 'increased', 'decreased', 'showed', 'highly',
    'potential', 'level', 'levels', 'significant', 'role', 'roles', 'expression', 'cells',
    'muscle', 'genes', 'protein', 'response', 'human', 'show', 'shows', 'shown', 'including',
    'study', 'used', 'data', 'analysis', 'clinical', 'molecular',
}

_ACADEMIC_NOISE = {
    'role in', 'roles in', 'response to', 'in response', 'understanding of',
    'we found', 'development of', 'involved in', 'loss of', 'associated with',
    'it is', 'there is', 'due to', 'well as', 'as well as', 'here we', 'shown to',
    'plays a', 'play a', 'the expression', 'expression of', 'levels of',
}


def _clean_text_for_keywords(text: str) -> list[str]:
    """Tokenise text, discarding placeholders. Returns a list of lowercase tokens."""
    if not text:
        return []
    if any(p in text.lower() for p in _ABSTRACT_PLACEHOLDERS):
        return []
    text = re.sub(r'[/\\-]', ' ', text)
    text = re.sub(r'[^a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s]', '', text)
    return text.lower().split()


def _is_valid_gram(gram_list: list[str]) -> bool:
    """Return True if an n-gram is a valid concept candidate."""
    gram_str = " ".join(gram_list)
    if gram_list[0] in _STOP_WORDS or gram_list[-1] in _STOP_WORDS:
        return False
    if gram_str in _ACADEMIC_NOISE:
        return False
    if len(gram_str) < 3 or gram_str in _STOP_WORDS:
        return False
    return True


def _deduplicate_concepts(freq: Counter, min_count: int = 2) -> list[tuple[str, int]]:
    """
    Mirror the deduplication logic from link_analyze.py:
    - Prefer longer n-grams over sub-strings they contain, unless the shorter
      form is much more frequent (>1.5× the longer one).
    - Filter by min_count.
    - Sort by (length DESC, count DESC) then re-sort by count for final output.
    """
    seen: set[str] = set()
    candidates = sorted(freq.items(), key=lambda x: (len(x[0]), x[1]), reverse=True)
    result = []
    for concept, count in candidates:
        if count < min_count:
            continue
        is_redundant = any(
            concept in longer and freq[longer] * 1.5 >= count
            for longer in seen
        )
        if not is_redundant:
            seen.add(concept)
            result.append((concept, count))
    result.sort(key=lambda x: x[1], reverse=True)
    return result


def extract_keywords_from_text(text: str) -> Counter:
    """
    Full pipeline: tokenise → build 1/2/3-grams → filter → return Counter.
    Call this once per abstract/title; aggregate the Counters across papers.
    """
    tokens = _clean_text_for_keywords(text)
    counts: Counter = Counter()
    for n in [1, 2, 3]:
        grams = [tokens[i:i+n] for i in range(len(tokens) - n + 1)]
        valid = [" ".join(g) for g in grams if _is_valid_gram(g)]
        counts.update(valid)
    return counts


def _render_log(log_box):
    """Re-render the log lines into the placeholder."""
    content = "\n".join(st.session_state.log_lines[-60:])   # show last 60 lines
    log_box.code(content, language=None)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: SELECT
# ══════════════════════════════════════════════════════════════════════════════

def page_select():
    st.title("📄 PDF Metadata Processor")
    st.markdown("Process a folder of PDFs: extract DOIs, rename files, create Obsidian notes, and pick keywords.")

    if not MODULES_AVAILABLE:
        st.error(
            f"Could not import your processing modules: `{_import_error}`\n\n"
            "Make sure `bulk_pdf_metadata_renamer.py` and `import_requests.py` "
            "are in the same directory as this app."
        )

    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📁 PDF folder")
        folder = st.text_input(
            "Paste the full path to the folder containing your PDFs",
            value=st.session_state.folder_path,
            placeholder=r"C:\Users\you\Documents\Unsorted",
        )
        if folder:
            p = Path(folder)
            if p.is_dir():
                pdf_count = len(list(p.glob("*.pdf")))
                st.success(f"✅  Found **{pdf_count}** PDF(s) in this folder")
            else:
                st.warning("⚠️  Path doesn't exist or isn't a folder")

    with col2:
        st.subheader("🗒️ Obsidian vault folder")
        obsidian = st.text_input(
            "Paste the path where Obsidian notes should be saved",
            value=st.session_state.obsidian_path,
            placeholder=r"G:\Mi unidad\Input_network\Input_network",
        )
        if obsidian and not Path(obsidian).is_dir():
            st.warning("⚠️  Path doesn't exist or isn't a folder")

    st.divider()
    ready = (
        MODULES_AVAILABLE
        and folder
        and Path(folder).is_dir()
        and obsidian
        and Path(obsidian).is_dir()
    )

    if st.button("🚀  Start processing", disabled=not ready, type="primary", use_container_width=True):
        st.session_state.folder_path   = folder
        st.session_state.obsidian_path = obsidian
        st.session_state.log_lines     = []
        advance_to("processing")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: PROCESSING
# ══════════════════════════════════════════════════════════════════════════════

def page_processing():
    st.title("⚙️  Processing PDFs…")
    st.caption(f"Folder: `{st.session_state.folder_path}`")

    log_box = st.empty()

    # Guard: only run the heavy processing once.
    # On any subsequent rerun (e.g. button click), skip straight to showing results.
    if not st.session_state.processing_done:
        with st.spinner("Working…"):
            stats, keyword_freq, processed_papers = process_folder(
                st.session_state.folder_path,
                st.session_state.obsidian_path,
                log_box,
            )
        st.session_state.stats            = stats
        st.session_state.keyword_freq     = keyword_freq
        st.session_state.processed_papers = processed_papers
        st.session_state.processing_done  = True

    # Always render the stored log so it stays visible
    _render_log(log_box)

    stats        = st.session_state.stats
    keyword_freq = st.session_state.keyword_freq

    # Summary metrics
    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Processed",    stats["processed"])
    c2.metric("✅ Success",    stats["success"])
    c3.metric("❌ Failed",     stats["failed"])
    c4.metric("⚠️ Duplicates", stats["duplicates"])

    if keyword_freq:
        st.success(f"Found **{len(keyword_freq)}** candidate keywords across all abstracts.")
        if st.button("→  Go to keyword selection", type="primary", use_container_width=True):
            advance_to("keywords")
    else:
        st.info("No keywords found (no abstracts retrieved, or all failed). Processing is complete.")
        if st.button("🔄  Process another folder", use_container_width=True):
            advance_to("select")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: KEYWORD SELECTION
# ══════════════════════════════════════════════════════════════════════════════

def page_keywords():
    st.title("🏷️  Select Keywords")
    st.markdown(
        "Click a keyword to **select** or **deselect** it. "
        "Selected keywords will be linked in all Obsidian notes."
    )

    freq = st.session_state.keyword_freq
    selected = st.session_state.selected_keywords

    # ── Controls ──────────────────────────────────────────────────────────────
    col_a, col_b, col_c = st.columns([2, 1, 1])
    with col_a:
        max_freq = max(freq.values()) if freq else 2
        min_count = st.slider("Minimum occurrences to show", 1, max(max_freq, 2), 2)
    with col_b:
        sort_by = st.selectbox("Sort by", ["Frequency ↓", "Length + Frequency ↓", "Alphabetical"])
    with col_c:
        st.write("")  # spacer
        if st.button("Clear selection"):
            st.session_state.selected_keywords = set()
            st.rerun()

    # Filter + sort
    filtered = {w: c for w, c in freq.items() if c >= min_count}
    if sort_by == "Frequency ↓":
        sorted_words = sorted(filtered.items(), key=lambda x: -x[1])
    elif sort_by == "Length + Frequency ↓":
        sorted_words = sorted(filtered.items(), key=lambda x: (len(x[0]), x[1]), reverse=True)
    else:
        sorted_words = sorted(filtered.items(), key=lambda x: x[0])

    st.caption(f"Showing **{len(sorted_words)}** keywords · **{len(selected)}** selected")
    st.divider()

    # ── Keyword grid ──────────────────────────────────────────────────────────
    # We render keywords in rows of N columns.
    # Each keyword is a button; clicking it toggles selection.
    N_COLS = 5
    rows = [sorted_words[i:i+N_COLS] for i in range(0, len(sorted_words), N_COLS)]

    for row in rows:
        cols = st.columns(N_COLS)
        for col, (word, count) in zip(cols, row):
            is_selected = word in selected
            label = f"{'✓ ' if is_selected else ''}{word}  ({count})"
            # Use different button styling via help text (native Streamlit has no color per button,
            # but the ✓ prefix gives clear visual feedback)
            if col.button(label, key=f"kw_{word}", use_container_width=True):
                if word in st.session_state.selected_keywords:
                    st.session_state.selected_keywords.discard(word)
                else:
                    st.session_state.selected_keywords.add(word)
                st.rerun()

    # ── Selected summary ──────────────────────────────────────────────────────
    st.divider()
    if selected:
        st.markdown(f"**Selected ({len(selected)}):** " + " · ".join(f"`{w}`" for w in sorted(selected)))
    else:
        st.info("No keywords selected yet.")

    st.write("")
    if st.button(
        f"🔗  Link {len(selected)} keyword(s) in Obsidian notes",
        type="primary",
        disabled=len(selected) == 0,
        use_container_width=True,
    ):
        advance_to("linking")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: LINKING
# ══════════════════════════════════════════════════════════════════════════════

def page_linking():
    st.title("🔗  Creating Wikilinks…")

    selected = st.session_state.selected_keywords
    papers   = st.session_state.processed_papers

    if not papers:
        st.warning("No processed papers to link.")
        if st.button("← Back"):
            advance_to("keywords")
        return

    log_box  = st.empty()
    progress = st.progress(0)
    linked   = 0
    errors   = 0

    for i, paper in enumerate(papers):
        md_path = Path(paper["md_path"])
        log(f"🔗  Linking in: {md_path.name}")
        _render_log(log_box)

        if not md_path.exists():
            log(f"   ⚠️  File not found, skipping")
            _render_log(log_box)
            errors += 1
            progress.progress((i + 1) / len(papers))
            continue

        try:
            text = md_path.read_text(encoding="utf-8")
            modified = _insert_wikilinks(text, selected)
            md_path.write_text(modified, encoding="utf-8")
            log(f"   ✅  Done")
            linked += 1
        except Exception as e:
            log(f"   ❌  Error: {e}")
            errors += 1

        _render_log(log_box)
        progress.progress((i + 1) / len(papers))

    st.divider()
    st.success(f"Linked keywords in **{linked}** note(s). Errors: {errors}.")

    if st.button("🔄  Process another folder", type="primary", use_container_width=True):
        # Reset everything
        for k, v in defaults.items():
            st.session_state[k] = v
        advance_to("select")


def _insert_wikilinks(text: str, keywords: set[str]) -> str:
    """
    Replace occurrences of each keyword with [[keyword]] in the markdown body,
    skipping the YAML front matter and already-linked occurrences.

    Only the FIRST occurrence of each keyword is linked (common Obsidian convention).
    Adjust to your preference.
    """
    # Split off YAML front matter
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            front_matter = "---" + parts[1] + "---"
            body = parts[2]
        else:
            front_matter, body = "", text
    else:
        front_matter, body = "", text

    for kw in sorted(keywords, key=len, reverse=True):  # longest first avoids partial matches
        # Skip if already wikilinked
        if f"[[{kw}]]" in body:
            continue
        # Replace first occurrence, case-insensitive, whole word
        pattern = re.compile(rf"\b({re.escape(kw)})\b", re.IGNORECASE)
        body, count = pattern.subn(rf"[[{kw}]]", body, count=1)

    return front_matter + body


# ══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════════════════════════════════

STAGE_PAGES = {
    "select":     page_select,
    "processing": page_processing,
    "keywords":   page_keywords,
    "linking":    page_linking,
}

# Sidebar breadcrumb
with st.sidebar:
    st.markdown("## PDF Processor")
    stages = list(STAGE_PAGES.keys())
    current = st.session_state.stage
    for s in stages:
        icon = "▶" if s == current else ("✓" if stages.index(s) < stages.index(current) else "·")
        st.markdown(f"{icon} `{s}`")
    st.divider()
    st.caption("If stuck, click below to reset.")
    if st.button("🔄 Reset app"):
        for k, v in defaults.items():
            st.session_state[k] = v
        st.rerun()

STAGE_PAGES[st.session_state.stage]()
