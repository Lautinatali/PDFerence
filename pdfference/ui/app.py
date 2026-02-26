"""
PDFerence Streamlit UI
Simplified to pure presentation layer; delegates to core/ modules.
"""
import streamlit as st
from pathlib import Path
from collections import Counter

from pdfference.config import Config
from pdfference.core.pdf_processor import PDFProcessor
from pdfference.core.metadata_fetcher import MetadataFetcher
from pdfference.core.note_generator import NoteGenerator
from pdfference.core.linker import Linker
from pdfference.analysis.keyword_extractor import KeywordExtractor
from pdfference.utils.logger import Logger


# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="PDFerence",
    page_icon="📄",
    layout="wide",
)

Config.ensure_dirs()

# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════════════════════

defaults = {
    "stage": "select",
    "folder_path": "",
    "obsidian_path": "",
    "log_lines": [],
    "stats": {"processed": 0, "success": 0, "failed": 0, "duplicates": 0},
    "processing_done": False,
    # keyword stage
    "keyword_freq": {},
    "selected_keywords": set(),
    "processed_papers": [],
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def log_to_session(msg: str):
    """Append timestamped line to session log."""
    from datetime import datetime
    ts = datetime.now().strftime("%H:%M:%S")
    st.session_state.log_lines.append(f"[{ts}] {msg}")


def advance_to(stage: str):
    """Transition to next stage."""
    st.session_state.stage = stage
    st.rerun()


def render_log():
    """Display log output in UI."""
    if st.session_state.log_lines:
        with st.container(border=True):
            st.text("\n".join(st.session_state.log_lines))


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: SELECT
# ══════════════════════════════════════════════════════════════════════════════

def page_select():
    st.title("📄 PDFerence — PDF Metadata Processor")
    
    st.markdown("### Step 1: Configure paths")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📁 PDF Folder")
        default_pdf = str(Config.PDF_FOLDER) if Config.PDF_FOLDER else ""
        folder_input = st.text_input(
            "Paste the full path to the folder containing your PDFs",
            value=st.session_state.folder_path or default_pdf,
            placeholder=r"C:\Users\you\Documents\Unsorted",
        )
        st.session_state.folder_path = folder_input
        
        # Live PDF count check
        if folder_input:
            p = Path(folder_input)
            if p.is_dir():
                pdf_count = len(list(p.glob("*.pdf")))
                st.success(f"✅ Found **{pdf_count}** PDF(s) in this folder")
            else:
                st.warning("⚠️ Path doesn't exist or isn't a folder")
    
    with col2:
        st.subheader("🗒️ Obsidian Vault Path")
        default_vault = str(Config.VAULT_PATH)
        vault_input = st.text_input(
            "Paste the path where Obsidian notes should be saved",
            value=st.session_state.obsidian_path or default_vault,
            placeholder=r"G:\Mi unidad\Input_network\Input_network",
        )
        st.session_state.obsidian_path = vault_input
        
        # Vault path validation
        if vault_input:
            if not Path(vault_input).is_dir():
                st.warning("⚠️ Path doesn't exist or isn't a folder")
    
    st.markdown("---")
    
    if st.button("✅ Start Processing", use_container_width=True, type="primary"):
        if not st.session_state.folder_path or not st.session_state.obsidian_path:
            st.error("❌ Please fill in both paths")
        else:
            advance_to("processing")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: PROCESSING
# ══════════════════════════════════════════════════════════════════════════════

def page_processing():
    st.title("🔄 Processing PDFs")
    
    if not st.session_state.processing_done:
        logger = Logger("Processing", Config.LOG_DIR)
        pdf_processor = PDFProcessor(logger)
        metadata_fetcher = MetadataFetcher(logger)
        note_generator = NoteGenerator(logger)
        
        folder = Path(st.session_state.folder_path)
        
        log_placeholder = st.empty()
        
        logger.info(f"Starting processing of {folder}")
        
        # Process all PDFs
        stats = {
            "processed": 0,
            "success": 0,
            "failed": 0,
            "duplicates": 0,
        }
        papers = []
        
        with st.spinner("Processing..."):
            for pdf_file in folder.glob("*.pdf"):
                stats["processed"] += 1
                logger.info(f"Processing: {pdf_file.name}")
                
                # Extract DOI
                doi = pdf_processor.extract_doi_from_pdf(pdf_file)
                if not doi:
                    logger.error(f"No DOI found in {pdf_file.name}")
                    stats["failed"] += 1
                    continue
                
                # Fetch metadata
                paper = metadata_fetcher.fetch(doi)
                if not paper:
                    logger.error(f"Failed to fetch metadata for {doi}")
                    stats["failed"] += 1
                    continue
                
                # Save note
                try:
                    note_path = note_generator.save_note(
                        paper,
                        Path(st.session_state.obsidian_path)
                    )
                    papers.append(paper)
                    stats["success"] += 1
                    
                    # Move PDF to Input subfolder
                    try:
                        pdf_processor.organize_pdf(
                            pdf_file,
                            Path(st.session_state.obsidian_path),
                            paper,
                            move_to_input=Config.MOVE_PDFS_TO_INPUT
                        )
                    except Exception as e:
                        logger.warning(f"Could not move PDF: {e}")
                        
                except Exception as e:
                    logger.error(f"Failed to save note: {e}")
                    stats["failed"] += 1
                
                # Update UI
                log_placeholder.text("\n".join(logger.ui_lines))
        
        st.session_state.stats = stats
        st.session_state.processed_papers = papers
        st.session_state.processing_done = True
    
    # Show stats
    stats = st.session_state.stats
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Processed", stats["processed"])
    col2.metric("Success", stats["success"], delta=f"{100*stats['success']//max(stats['processed'],1)}%")
    col3.metric("Failed", stats["failed"])
    col4.metric("Duplicates", stats["duplicates"])
    
    render_log()
    
    st.markdown("---")
    if st.button("➡️ Next: Extract Keywords", use_container_width=True, type="primary"):
        advance_to("keywords")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: KEYWORD EXTRACTION
# ══════════════════════════════════════════════════════════════════════════════

def page_keywords():
    st.title("🔍 Extract Keywords")
    
    logger = Logger("KeywordExtraction", Config.LOG_DIR)
    extractor = KeywordExtractor(logger)
    
    if not st.session_state.keyword_freq:
        st.info("ℹ️ Extracting keywords from vault... (this may take a moment)")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            status_text.text("Scanning vault...")
            progress_bar.progress(10)
            
            freq = extractor.extract_from_vault(
                Path(st.session_state.obsidian_path),
                target_header="Abstract"
            )
            progress_bar.progress(50)
            
            status_text.text("Deduplicating keywords...")
            deduplicated = extractor.deduplicate(freq, min_count=2)
            progress_bar.progress(90)
            
            # Convert to dict for session state
            st.session_state.keyword_freq = {
                word: count for word, count in deduplicated[:Config.TOP_KEYWORDS_LIMIT]
            }
            
            status_text.text(f"✅ Extracted {len(st.session_state.keyword_freq)} keywords")
            progress_bar.progress(100)
        except Exception as e:
            status_text.error(f"❌ Error extracting keywords: {e}")
            logger.error(f"Keyword extraction failed: {e}")
            return
    
    st.markdown("### Select Keywords to Create Wikilinks")
    
    # Display frequency table
    keyword_freq = st.session_state.keyword_freq
    if keyword_freq:
        st.markdown("Click keywords to toggle selection:")
        
        # Display as buttons with counts
        keywords_list = list(keyword_freq.keys())
        cols = st.columns(3)
        
        for idx, word in enumerate(keywords_list):
            col = cols[idx % 3]
            with col:
                count = keyword_freq[word]
                is_selected = word in st.session_state.selected_keywords
                
                # Button styling based on selection
                button_label = f"✓ {word}" if is_selected else word
                if col.button(
                    f"{button_label}\n_{count}_",
                    key=f"kw_{word}_{idx}",
                    use_container_width=True,
                    type="primary" if is_selected else "secondary"
                ):
                    if is_selected:
                        st.session_state.selected_keywords.discard(word)
                    else:
                        st.session_state.selected_keywords.add(word)
                    st.rerun()
        
        st.markdown("---")
        st.info(f"Selected: {len(st.session_state.selected_keywords)} keywords")
    
    st.markdown("---")
    
    if st.button("➡️ Next: Apply Wikilinks", use_container_width=True, type="primary"):
        advance_to("linking")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: LINKING
# ══════════════════════════════════════════════════════════════════════════════

def page_linking():
    st.title("🔗 Apply Wikilinks")
    
    logger = Logger("Linking", Config.LOG_DIR)
    linker = Linker(logger)
    
    st.markdown(f"**Keywords to link:** {len(st.session_state.selected_keywords)}")
    
    if st.session_state.selected_keywords:
        st.caption(", ".join(list(st.session_state.selected_keywords)[:5]) + "...")
    
    if st.button("🚀 Apply Links to Vault", use_container_width=True, type="primary"):
        with st.spinner("Applying wikilinks..."):
            processed, modified = linker.apply_links_to_vault(
                Path(st.session_state.obsidian_path),
                st.session_state.selected_keywords
            )
        
        col1, col2 = st.columns(2)
        col1.metric("Files Processed", processed)
        col2.metric("Files Modified", modified)
        
        st.success("✅ Wikilinks applied successfully!")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Back to Keywords", use_container_width=True):
            advance_to("keywords")
    with col2:
        if st.button("✨ Complete", use_container_width=True, type="primary"):
            st.balloons()
            advance_to("select")



# ══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════════════════════════════════

STAGE_PAGES = {
    "select": page_select,
    "processing": page_processing,
    "keywords": page_keywords,
    "linking": page_linking,
}

# Sidebar breadcrumb
with st.sidebar:
    st.title("📍 Progress")
    stages = ["select", "processing", "keywords", "linking"]
    current_idx = stages.index(st.session_state.stage)
    
    for i, stage in enumerate(stages):
        status = "✅" if i < current_idx else "→" if i == current_idx else "⭕"
        st.caption(f"{status} {stage.capitalize()}")

# Render current page
STAGE_PAGES[st.session_state.stage]()
