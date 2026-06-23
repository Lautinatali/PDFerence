"""
PDFerence CLI: Standalone command-line interface.
Reuses all core/ modules without Streamlit dependency.
"""
import argparse
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

from pdfference.config import Config
from pdfference.core.pdf_processor import PDFProcessor
from pdfference.core.metadata_fetcher import MetadataFetcher
from pdfference.core.note_generator import NoteGenerator
from pdfference.core.linker import Linker
from pdfference.core.keyword_store import KeywordStore
from pdfference.core.setup import setup_automated
from pdfference.core.models import ProcessingStats, ProcessingResult
from pdfference.analysis.keyword_extractor import KeywordExtractor
from pdfference.utils.logger import Logger


def process_pdfs_command(args):
    """Process PDFs in a folder."""
    logger = Logger("CLI-ProcessPDFs", Config.LOG_DIR)
    
    pdf_processor = PDFProcessor(logger)
    metadata_fetcher = MetadataFetcher(logger)
    note_generator = NoteGenerator(logger)
    
    input_folder = Path(args.input_folder)
    output_folder = Path(args.output_folder or Config.OBSIDIAN_OUTPUT)
    
    if not input_folder.exists():
        logger.error(f"Input folder not found: {input_folder}")
        return 1
    
    logger.info(f"Starting PDF processing: {input_folder}")
    logger.info(f"Output folder: {output_folder}")
    
    stats = ProcessingStats()
    
    for pdf_file in sorted(input_folder.glob("*.pdf")):
        stats.processed += 1
        logger.info(f"Processing {pdf_file.name} ({stats.processed})...")
        
        # Extract DOI
        doi = pdf_processor.extract_doi_from_pdf(pdf_file)
        if not doi:
            logger.warning(f"No DOI found in {pdf_file.name}")
            stats.failed += 1
            continue
        
        # Fetch metadata
        paper = metadata_fetcher.fetch(doi)
        if not paper:
            logger.warning(f"Failed to fetch metadata for {doi}")
            stats.failed += 1
            continue
        
        # Save note
        try:
            note_path = note_generator.save_note(paper, output_folder)
            stats.success += 1
        except Exception as e:
            logger.error(f"Failed to save note: {e}")
            stats.failed += 1
    
    logger.info(f"Processing complete: {stats}")
    return 0 if stats.failed == 0 else 1


def extract_keywords_command(args):
    """Extract keywords from vault."""
    logger = Logger("CLI-ExtractKeywords", Config.LOG_DIR)
    
    extractor = KeywordExtractor(logger)
    
    vault_path = Path(args.vault or Config.VAULT_PATH)
    if not vault_path.exists():
        logger.error(f"Vault not found: {vault_path}")
        return 1
    
    logger.info(f"Extracting keywords from: {vault_path}")
    
    # Extract
    freq = extractor.extract_from_vault(
        vault_path,
        target_header=args.header or "Abstract"
    )
    
    # Deduplicate
    deduplicated = extractor.deduplicate(freq, min_count=args.min_count)
    
    # Output
    output_file = args.output or "keywords.csv"
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("keyword,frequency\n")
            for word, count in deduplicated[:args.limit]:
                f.write(f'"{word}",{count}\n')
        
        logger.success(f"Keywords exported to {output_file}")
        return 0
    except Exception as e:
        logger.error(f"Failed to export: {e}")
        return 1


def apply_links_command(args):
    """Apply wikilinks to vault."""
    logger = Logger("CLI-ApplyLinks", Config.LOG_DIR)
    
    linker = Linker(logger)
    
    vault_path = Path(args.vault or Config.VAULT_PATH)
    if not vault_path.exists():
        logger.error(f"Vault not found: {vault_path}")
        return 1
    
    # Load keywords from file or use defaults
    if args.keywords_file:
        try:
            keywords = set()
            with open(args.keywords_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("keyword"):
                        # CSV format: "keyword",count
                        keyword = line.split(',')[0].strip('"').strip()
                        if keyword:
                            keywords.add(keyword)
            logger.info(f"Loaded {len(keywords)} keywords from {args.keywords_file}")
        except Exception as e:
            logger.error(f"Failed to load keywords file: {e}")
            return 1
    else:
        keywords = set(Config.KEYWORDS_TO_LINK)
        logger.info(f"Using default {len(keywords)} keywords")
    
    # Apply
    processed, modified = linker.apply_links_to_vault(vault_path, keywords)
    logger.info(f"Applied links: {modified}/{processed} files modified")

    return 0


def scan_new_papers_command(args):
    """Scan papers added since last scan for new keywords."""
    logger = Logger("CLI-ScanNewPapers", Config.LOG_DIR)
    extractor = KeywordExtractor(logger)
    store = KeywordStore()

    vault_path = Path(args.vault or Config.VAULT_PATH)
    since_date = store.get_last_scan()

    if not vault_path.exists():
        logger.error(f"Vault not found: {vault_path}")
        return 1

    logger.info(f"Scanning for papers added since {since_date or 'beginning'}")

    freq, new_papers = extractor.extract_new_papers(vault_path, since_date)

    if not new_papers:
        logger.info("No new papers found")
        return 0

    logger.info(f"Found {len(new_papers)} new papers")

    known = store.get_all_keywords()
    candidates = [
        (word, count) for word, count in freq.most_common()
        if word not in known and count >= args.min_count
    ]

    if not candidates:
        logger.info("No new keyword candidates found")
        return 0

    logger.info(f"\n📊 Found {len(candidates)} new keyword candidates:")
    for word, count in candidates[:20]:
        print(f"  • {word}: {count} occurrences")

    return 0


def review_keywords_command(args):
    """Interactively approve new keywords."""
    logger = Logger("CLI-ReviewKeywords", Config.LOG_DIR)
    extractor = KeywordExtractor(logger)
    store = KeywordStore()

    vault_path = Path(args.vault or Config.VAULT_PATH)
    if not vault_path.exists():
        logger.error(f"Vault not found: {vault_path}")
        return 1

    since_date = store.get_last_scan()

    freq, _ = extractor.extract_new_papers(vault_path, since_date)
    known = store.get_all_keywords()
    candidates = [
        (word, count) for word, count in freq.most_common()
        if word not in known and count >= args.min_count
    ]

    if not candidates:
        logger.info("No new candidates to review")
        return 0

    logger.info(f"\n🔍 Review {len(candidates)} keyword candidates:")
    approved_count = 0

    for word, count in candidates[:args.limit]:
        response = input(f"\n✓ Add '{word}' ({count} occurrences)? [y/n/skip]: ").strip().lower()

        if response == 'y':
            store.add_keyword(word)
            approved_count += 1
            logger.success(f"Added: {word}")
        elif response == 'skip':
            continue

    if approved_count > 0:
        store.set_last_scan(datetime.now().isoformat())
        store.save()
        logger.success(f"Approved {approved_count} new keywords")
        logger.info(f"Total keywords now: {len(store.get_all_keywords())}")
        return 0
    else:
        logger.info("No keywords approved")
        return 1


def reindex_vault_command(args):
    """Re-link entire vault with current keyword set."""
    logger = Logger("CLI-ReindexVault", Config.LOG_DIR)
    linker = Linker(logger)
    store = KeywordStore()

    vault_path = Path(args.vault or Config.VAULT_PATH)
    if not vault_path.exists():
        logger.error(f"Vault not found: {vault_path}")
        return 1

    keywords = store.get_all_keywords()

    if not keywords:
        logger.error("No approved keywords found. Run 'review-keywords' first")
        return 1

    logger.info(f"Reindexing vault with {len(keywords)} keywords")
    processed, modified = linker.apply_links_to_vault(vault_path, keywords)

    logger.success(f"Reindex complete: {modified}/{processed} files modified")
    return 0


def setup_command(args):
    """Automated setup: process PDFs → extract keywords → review → apply links."""
    pdf_folder = Path(args.input_folder)
    output_folder = Path(args.output_folder) if args.output_folder else None

    if not pdf_folder.exists():
        print(f"Error: Input folder not found: {pdf_folder}")
        return 1

    results = setup_automated(
        pdf_folder=pdf_folder,
        output_folder=output_folder,
        min_keyword_count=args.min_count,
        keyword_limit=args.limit,
    )

    print("\n" + "="*60)
    print("Setup Complete!")
    print("="*60)
    print(f"PDFs processed: {results['pdfs_processed']}")
    print(f"Keywords extracted: {results['keywords_extracted']}")
    print(f"Keywords approved: {results['keywords_approved']}")
    print(f"Files modified: {results['files_modified']}")
    print("="*60)

    return 0


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="PDFerence: PDF metadata processor with Obsidian integration"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # ─────────────────────────────────────────────────────────────────────────
    # process-pdfs command
    # ─────────────────────────────────────────────────────────────────────────
    process_parser = subparsers.add_parser(
        "process-pdfs",
        help="Process PDFs and extract metadata"
    )
    process_parser.add_argument(
        "input_folder",
        help="Folder containing PDFs to process"
    )
    process_parser.add_argument(
        "-o", "--output-folder",
        help=f"Output folder for notes (default: {Config.OBSIDIAN_OUTPUT})"
    )
    process_parser.set_defaults(func=process_pdfs_command)
    
    # ─────────────────────────────────────────────────────────────────────────
    # extract-keywords command
    # ─────────────────────────────────────────────────────────────────────────
    keywords_parser = subparsers.add_parser(
        "extract-keywords",
        help="Extract keywords from vault"
    )
    keywords_parser.add_argument(
        "-v", "--vault",
        help=f"Vault path (default: {Config.VAULT_PATH})"
    )
    keywords_parser.add_argument(
        "--header",
        default="Abstract",
        help="Section header to extract from (default: Abstract)"
    )
    keywords_parser.add_argument(
        "-m", "--min-count",
        type=int,
        default=2,
        help="Minimum occurrences (default: 2)"
    )
    keywords_parser.add_argument(
        "-l", "--limit",
        type=int,
        default=100,
        help="Top N keywords to export (default: 100)"
    )
    keywords_parser.add_argument(
        "-o", "--output",
        default="keywords.csv",
        help="Output CSV file (default: keywords.csv)"
    )
    keywords_parser.set_defaults(func=extract_keywords_command)
    
    # ─────────────────────────────────────────────────────────────────────────
    # apply-links command
    # ─────────────────────────────────────────────────────────────────────────
    links_parser = subparsers.add_parser(
        "apply-links",
        help="Apply wikilinks to vault"
    )
    links_parser.add_argument(
        "-v", "--vault",
        help=f"Vault path (default: {Config.VAULT_PATH})"
    )
    links_parser.add_argument(
        "-k", "--keywords-file",
        help="CSV file with keywords (from extract-keywords)"
    )
    links_parser.set_defaults(func=apply_links_command)

    # ─────────────────────────────────────────────────────────────────────────
    # scan-new-papers command
    # ─────────────────────────────────────────────────────────────────────────
    scan_parser = subparsers.add_parser(
        "scan-new-papers",
        help="Scan papers added since last scan for new keywords"
    )
    scan_parser.add_argument(
        "-v", "--vault",
        help=f"Vault path (default: {Config.VAULT_PATH})"
    )
    scan_parser.add_argument(
        "-m", "--min-count",
        type=int,
        default=2,
        help="Minimum occurrences (default: 2)"
    )
    scan_parser.set_defaults(func=scan_new_papers_command)

    # ─────────────────────────────────────────────────────────────────────────
    # review-keywords command
    # ─────────────────────────────────────────────────────────────────────────
    review_parser = subparsers.add_parser(
        "review-keywords",
        help="Interactively approve new keywords"
    )
    review_parser.add_argument(
        "-v", "--vault",
        help=f"Vault path (default: {Config.VAULT_PATH})"
    )
    review_parser.add_argument(
        "-m", "--min-count",
        type=int,
        default=2,
        help="Minimum occurrences (default: 2)"
    )
    review_parser.add_argument(
        "-l", "--limit",
        type=int,
        default=50,
        help="Maximum keywords to review (default: 50)"
    )
    review_parser.set_defaults(func=review_keywords_command)

    # ─────────────────────────────────────────────────────────────────────────
    # reindex-vault command
    # ─────────────────────────────────────────────────────────────────────────
    reindex_parser = subparsers.add_parser(
        "reindex-vault",
        help="Re-link entire vault with all approved keywords"
    )
    reindex_parser.add_argument(
        "-v", "--vault",
        help=f"Vault path (default: {Config.VAULT_PATH})"
    )
    reindex_parser.set_defaults(func=reindex_vault_command)

    # ─────────────────────────────────────────────────────────────────────────
    # setup command
    # ─────────────────────────────────────────────────────────────────────────
    setup_parser = subparsers.add_parser(
        "setup",
        help="Automated setup: process PDFs → extract keywords → review → apply links"
    )
    setup_parser.add_argument(
        "input_folder",
        help="Folder containing PDFs to process"
    )
    setup_parser.add_argument(
        "-o", "--output-folder",
        help="Output folder for vault (default: ./output/)"
    )
    setup_parser.add_argument(
        "-m", "--min-count",
        type=int,
        default=2,
        help="Minimum keyword occurrences (default: 2)"
    )
    setup_parser.add_argument(
        "-l", "--limit",
        type=int,
        default=50,
        help="Maximum keywords to review (default: 50)"
    )
    setup_parser.set_defaults(func=setup_command)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1
    
    Config.ensure_dirs()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
