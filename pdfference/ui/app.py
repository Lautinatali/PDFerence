"""
PDFerence Streamlit UI - Refactored with home dashboard, setup, and keyword management.
"""
import sys
from pathlib import Path

# Add project root to path so imports work when running streamlit from any directory
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st
from datetime import datetime
from collections import Counter

from pdfference.config import Config
from pdfference.core.pdf_processor import PDFProcessor
from pdfference.core.metadata_fetcher import MetadataFetcher
from pdfference.core.note_generator import NoteGenerator
from pdfference.core.linker import Linker
from pdfference.core.keyword_store import KeywordStore
from pdfference.core.setup import setup_automated
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
    "page": "home",
    "keyword_store": KeywordStore(),
    # Setup page state
    "setup_folder_path": "",
    "setup_vault_path": "",
    "setup_processing_done": False,
    "setup_stats": {},
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def go_to_page(page: str):
    """Navigate to a page."""
    st.session_state.page = page
    st.rerun()


def get_vault_file_count(vault_path: Path) -> int:
    """Count markdown files in vault."""
    if vault_path.exists():
        return len(list(vault_path.glob("*.md")))
    return 0


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: HOME DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

def page_home():
    st.title("PDFerence - Home Dashboard")

    # Refresh store from disk
    st.session_state.keyword_store = KeywordStore()
    store = st.session_state.keyword_store

    # Stats
    keywords = store.get_all_keywords()
    last_scan = store.get_last_scan()
    vault_path = Path(Config.VAULT_PATH)
    vault_files = get_vault_file_count(vault_path)

    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Approved Keywords", len(keywords))
    col2.metric("Vault Files", vault_files)
    col3.metric("Last Scan", last_scan[:10] if last_scan else "Never")
    col4.metric("Vault Path", str(vault_path)[-20:] if vault_path.exists() else "Not found")

    st.markdown("---")

    # Quick actions
    st.markdown("### Quick Actions")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Setup New Vault", use_container_width=True, type="primary"):
            go_to_page("setup")

    with col2:
        if st.button("Manage Keywords", use_container_width=True):
            go_to_page("keyword_management")

    with col3:
        if st.button("Reindex Vault", use_container_width=True):
            if not keywords:
                st.error("No keywords to reindex with. Add keywords first.")
            elif not vault_path.exists():
                st.error(f"Vault not found at {vault_path}")
            else:
                with st.spinner("Reindexing vault..."):
                    logger = Logger("Reindex", Config.LOG_DIR)
                    linker = Linker(logger)
                    processed, modified = linker.apply_links_to_vault(vault_path, keywords)
                    st.success(f"Reindexed: {modified}/{processed} files modified")

    st.markdown("---")

    # Keywords list
    if keywords:
        st.markdown("### Current Keywords")
        cols = st.columns(4)
        for idx, keyword in enumerate(sorted(keywords)):
            col = cols[idx % 4]
            col.button(keyword, key=f"kw_{keyword}", disabled=True, use_container_width=True)
    else:
        st.info("No keywords yet. Use 'Setup New Vault' or 'Manage Keywords' to get started.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: SETUP
# ══════════════════════════════════════════════════════════════════════════════

def page_setup():
    st.title("Setup New Vault")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Input")
        pdf_folder = st.text_input(
            "PDF Folder Path",
            value=st.session_state.setup_folder_path,
            placeholder=r"C:\Users\you\Documents\PDFs",
        )
        st.session_state.setup_folder_path = pdf_folder

    with col2:
        st.markdown("### Output")
        vault_path = st.text_input(
            "Vault Output Path (default: ./output/)",
            value=st.session_state.setup_vault_path,
            placeholder=r"C:\Users\you\Documents\Vault",
        )
        st.session_state.setup_vault_path = vault_path

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        min_count = st.slider("Min Keyword Occurrences", min_value=1, max_value=5, value=2)
    with col2:
        keyword_limit = st.slider("Max Keywords to Review", min_value=10, max_value=200, value=50)

    st.markdown("---")

    if st.button("Start Setup", type="primary", use_container_width=True):
        if not pdf_folder:
            st.error("PDF folder path is required")
        else:
            pdf_path = Path(pdf_folder)
            if not pdf_path.exists():
                st.error(f"PDF folder not found: {pdf_folder}")
            else:
                with st.spinner("Running setup workflow..."):
                    output_path = Path(vault_path) if vault_path else None
                    results = setup_automated(
                        pdf_folder=pdf_path,
                        output_folder=output_path,
                        min_keyword_count=min_count,
                        keyword_limit=keyword_limit,
                    )
                    st.session_state.setup_stats = results
                    st.session_state.setup_processing_done = True

    # Show results
    if st.session_state.setup_processing_done and st.session_state.setup_stats:
        st.markdown("---")
        st.markdown("### Results")

        results = st.session_state.setup_stats
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("PDFs Processed", results['pdfs_processed'])
        col2.metric("Keywords Extracted", results['keywords_extracted'])
        col3.metric("Keywords Approved", results['keywords_approved'])
        col4.metric("Files Modified", results['files_modified'])

        st.success("Setup complete!")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Go to Home", use_container_width=True):
                st.session_state.setup_processing_done = False
                st.session_state.setup_stats = {}
                go_to_page("home")
        with col2:
            if st.button("Manage Keywords", use_container_width=True):
                go_to_page("keyword_management")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: KEYWORD MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

def page_keyword_management():
    st.title("Keyword Management")

    store = st.session_state.keyword_store
    keywords = sorted(store.get_all_keywords())

    # Add keyword section
    st.markdown("### Add Keyword")
    col1, col2 = st.columns([4, 1])
    with col1:
        new_keyword = st.text_input("New keyword to add", placeholder="e.g., Machine Learning")
    with col2:
        if st.button("Add", use_container_width=True, key="btn_add"):
            if not new_keyword:
                st.error("Keyword cannot be empty")
            elif new_keyword in keywords:
                st.error("Keyword already exists")
            else:
                store.add_keyword(new_keyword)
                store.save()
                st.success(f"Added: {new_keyword}")
                st.rerun()

    st.markdown("---")

    # Keywords list with remove/rename
    if keywords:
        st.markdown(f"### Current Keywords ({len(keywords)})")

        for keyword in keywords:
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

            with col1:
                st.write(keyword)

            with col2:
                if st.button("Remove", key=f"remove_{keyword}"):
                    if st.session_state.get(f"confirm_{keyword}"):
                        store.remove_keyword(keyword)
                        store.save()
                        st.success(f"Removed: {keyword}")
                        st.rerun()
                    else:
                        st.session_state[f"confirm_{keyword}"] = True
                        st.warning("Click again to confirm removal")

            with col3:
                if st.button("Rename", key=f"rename_{keyword}"):
                    st.session_state[f"rename_mode_{keyword}"] = True

            # Rename input
            if st.session_state.get(f"rename_mode_{keyword}"):
                new_name = st.text_input(
                    f"Rename '{keyword}' to:",
                    key=f"rename_input_{keyword}",
                    placeholder="New name"
                )
                col_confirm, col_cancel = st.columns(2)
                with col_confirm:
                    if st.button("Confirm", key=f"confirm_rename_{keyword}"):
                        if not new_name:
                            st.error("New name cannot be empty")
                        elif new_name in keywords:
                            st.error("Name already exists")
                        else:
                            if store.rename_keyword(keyword, new_name):
                                store.save()
                                st.success(f"Renamed: {keyword} -> {new_name}")
                                st.session_state[f"rename_mode_{keyword}"] = False
                                st.rerun()
                            else:
                                st.error("Rename failed")

                with col_cancel:
                    if st.button("Cancel", key=f"cancel_rename_{keyword}"):
                        st.session_state[f"rename_mode_{keyword}"] = False
                        st.rerun()
    else:
        st.info("No keywords yet. Add some to get started!")

    st.markdown("---")

    # Reindex vault with current keywords
    if keywords:
        st.markdown("### Apply Wikilinks")
        vault_path = Path(Config.VAULT_PATH)

        if not vault_path.exists():
            st.error(f"Vault not found at {vault_path}")
        else:
            if st.button("Reindex Vault with Current Keywords", type="primary", use_container_width=True):
                with st.spinner("Reindexing..."):
                    logger = Logger("ReindexUI", Config.LOG_DIR)
                    linker = Linker(logger)
                    processed, modified = linker.apply_links_to_vault(vault_path, keywords)
                    st.success(f"Reindexed: {modified}/{processed} files modified")

    # Back to home
    st.markdown("---")
    if st.button("Back to Home", use_container_width=True):
        go_to_page("home")


# ══════════════════════════════════════════════════════════════════════════════
# ROUTER & SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

PAGES = {
    "home": page_home,
    "setup": page_setup,
    "keyword_management": page_keyword_management,
}

# Sidebar navigation
with st.sidebar:
    st.title("Navigation")
    page = st.radio(
        "Go to:",
        options=["home", "setup", "keyword_management"],
        format_func=lambda x: {
            "home": "Home Dashboard",
            "setup": "Setup Workflow",
            "keyword_management": "Manage Keywords"
        }.get(x, x),
        key="nav_radio"
    )

    if page != st.session_state.page:
        st.session_state.page = page
        st.rerun()

    st.markdown("---")
    st.caption("Vault: " + str(Config.VAULT_PATH)[-30:])

# Render current page
PAGES[st.session_state.page]()
