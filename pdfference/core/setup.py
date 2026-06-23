"""
Automated setup workflow: process PDFs, extract keywords, review, and link.
Supports both CLI (with input prompts) and UI (with external keyword approval).
"""
from pathlib import Path
from datetime import datetime

from pdfference.config import Config
from pdfference.core.pdf_processor import PDFProcessor
from pdfference.core.metadata_fetcher import MetadataFetcher
from pdfference.core.note_generator import NoteGenerator
from pdfference.core.keyword_store import KeywordStore
from pdfference.core.linker import Linker
from pdfference.analysis.keyword_extractor import KeywordExtractor
from pdfference.utils.logger import Logger


def setup_phase_1_process(
    pdf_folder: Path,
    output_folder: Path = None,
    min_keyword_count: int = 2,
) -> dict:
    """
    Phase 1: Process PDFs and extract keywords (no user interaction).

    Args:
        pdf_folder: Path to folder containing PDFs
        output_folder: Path to output vault (defaults to ./output/)
        min_keyword_count: Minimum occurrences for keyword inclusion

    Returns:
        Dictionary with: pdfs_processed, keywords_extracted (list of (word, count) tuples)
    """
    if output_folder is None:
        output_folder = Path.cwd() / "output"

    output_folder = Path(output_folder)
    pdf_folder = Path(pdf_folder)

    output_folder.mkdir(parents=True, exist_ok=True)

    logger = Logger("Setup-Phase1", Config.LOG_DIR)
    logger.info(f"Phase 1: Processing PDFs and extracting keywords")
    logger.info(f"PDF folder: {pdf_folder}")
    logger.info(f"Output folder: {output_folder}")

    # Process PDFs
    logger.info("\nStep 1: Processing PDFs...")

    pdf_processor = PDFProcessor(logger)
    metadata_fetcher = MetadataFetcher(logger)
    note_generator = NoteGenerator(logger)

    pdfs_processed = 0
    pdfs_failed = 0

    pdf_files = sorted(pdf_folder.glob("*.pdf"))
    if not pdf_files:
        logger.warning(f"No PDFs found in {pdf_folder}")
        return {
            "pdfs_processed": 0,
            "keywords_extracted": [],
        }

    for pdf_file in pdf_files:
        pdfs_processed += 1
        logger.info(f"  Processing {pdf_file.name} ({pdfs_processed}/{len(pdf_files)})")

        doi = pdf_processor.extract_doi_from_pdf(pdf_file)
        if not doi:
            logger.warning(f"  -> No DOI found, skipping")
            pdfs_failed += 1
            continue

        paper = metadata_fetcher.fetch(doi)
        if not paper:
            logger.warning(f"  -> Failed to fetch metadata for {doi}")
            pdfs_failed += 1
            continue

        try:
            note_path = note_generator.save_note(paper, output_folder)
            logger.info(f"  SAVED: {note_path.name}")
        except Exception as e:
            logger.error(f"  -> Failed to save note: {e}")
            pdfs_failed += 1

    logger.success(f"Processed {pdfs_processed - pdfs_failed}/{pdfs_processed} PDFs")

    # Extract keywords
    logger.info("\nStep 2: Extracting keywords from vault...")

    extractor = KeywordExtractor(logger)
    freq = extractor.extract_from_vault(output_folder, target_header="Abstract")

    if not freq:
        logger.warning("No keywords found in vault")
        return {
            "pdfs_processed": pdfs_processed - pdfs_failed,
            "keywords_extracted": [],
        }

    deduplicated = extractor.deduplicate(freq, min_count=min_keyword_count)
    logger.success(f"Extracted {len(deduplicated)} keywords")

    # Return keywords for approval
    keywords_list = deduplicated  # List of (word, count) tuples
    return {
        "pdfs_processed": pdfs_processed - pdfs_failed,
        "keywords_extracted": keywords_list,
    }


def setup_phase_2_review(
    output_folder: Path,
    approved_keywords: set,
) -> dict:
    """
    Phase 2: Apply wikilinks using approved keywords and save to store.

    Args:
        output_folder: Path to output vault
        approved_keywords: Set of approved keyword strings

    Returns:
        Dictionary with: files_modified, keywords_approved
    """
    output_folder = Path(output_folder)
    logger = Logger("Setup-Phase2", Config.LOG_DIR)

    logger.info("\nStep 3: Applying wikilinks...")

    linker = Linker(logger)
    processed, modified = linker.apply_links_to_vault(output_folder, approved_keywords)
    logger.success(f"Applied links: {modified}/{processed} files modified")

    # Save approved keywords to store for future incremental scans
    try:
        store = KeywordStore()
        for word in approved_keywords:
            store.add_keyword(word)
        store.set_last_scan(datetime.now().isoformat())
        store.save()
        logger.info(f"Saved approved keywords to keyword store")
    except Exception as e:
        logger.warning(f"Could not save to keyword store: {e}")

    return {
        "files_modified": modified,
        "keywords_approved": len(approved_keywords),
    }


def setup_automated(
    pdf_folder: Path,
    output_folder: Path = None,
    min_keyword_count: int = 2,
    keyword_limit: int = 50,
) -> dict:
    """
    Automated workflow: process PDFs, extract keywords, interactive review, apply links.
    Uses input() for interactive keyword review (CLI only).

    Args:
        pdf_folder: Path to folder containing PDFs
        output_folder: Path to output vault (defaults to ./output/)
        min_keyword_count: Minimum occurrences for keyword inclusion
        keyword_limit: Max keywords to show for review

    Returns:
        Dictionary with: pdfs_processed, keywords_extracted, keywords_approved, files_modified
    """
    # Phase 1: Process and extract
    phase1 = setup_phase_1_process(pdf_folder, output_folder, min_keyword_count)

    pdfs_processed = phase1["pdfs_processed"]
    keywords_list = phase1["keywords_extracted"]

    if not keywords_list:
        return {
            "pdfs_processed": pdfs_processed,
            "keywords_extracted": 0,
            "keywords_approved": 0,
            "files_modified": 0,
        }

    logger = Logger("Setup-Interactive", Config.LOG_DIR)

    # Phase 1.5: Interactive review
    logger.info(f"\nStep 2: Review {min(len(keywords_list), keyword_limit)} keyword candidates")

    approved_keywords = set()

    for word, count in keywords_list[:keyword_limit]:
        try:
            response = (
                input(f"\n  Add '{word}' ({count} occurrences)? [y/n/skip]: ")
                .strip()
                .lower()
            )
            if response == "y":
                approved_keywords.add(word)
                logger.info(f"    Added: {word}")
        except KeyboardInterrupt:
            logger.info("\nReview cancelled by user")
            break

    logger.success(f"Approved {len(approved_keywords)} keywords")

    if not approved_keywords:
        logger.warning("No keywords approved, skipping wikilink application")
        return {
            "pdfs_processed": pdfs_processed,
            "keywords_extracted": len(keywords_list),
            "keywords_approved": 0,
            "files_modified": 0,
        }

    # Phase 2: Apply links
    phase2 = setup_phase_2_review(output_folder or Path.cwd() / "output", approved_keywords)

    return {
        "pdfs_processed": pdfs_processed,
        "keywords_extracted": len(keywords_list),
        "keywords_approved": phase2["keywords_approved"],
        "files_modified": phase2["files_modified"],
    }
