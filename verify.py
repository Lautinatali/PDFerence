#!/usr/bin/env python3
"""
PDFerence Quick Start / Verification Script
Checks that all imports work and basic functionality is available.
"""
import sys
from pathlib import Path

# Fix encoding for Windows console
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def check_imports():
    """Verify all modules can be imported."""
    print("🔍 Checking imports...")
    
    try:
        from pdfference.config import Config
        print("✅ config.py")
        
        from pdfference.core.models import Paper, ProcessingResult, ProcessingStats
        print("✅ core/models.py")
        
        from pdfference.utils.logger import Logger
        print("✅ utils/logger.py")
        
        from pdfference.core.pdf_processor import PDFProcessor
        print("✅ core/pdf_processor.py")
        
        from pdfference.core.metadata_fetcher import MetadataFetcher
        print("✅ core/metadata_fetcher.py")
        
        from pdfference.core.note_generator import NoteGenerator
        print("✅ core/note_generator.py")
        
        from pdfference.core.linker import Linker
        print("✅ core/linker.py")
        
        from pdfference.analysis.keyword_extractor import KeywordExtractor
        print("✅ analysis/keyword_extractor.py")
        
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def check_config():
    """Verify configuration loads."""
    print("\n🔧 Checking configuration...")
    
    try:
        from pdfference.config import Config
        
        print(f"  Vault path: {Config.VAULT_PATH}")
        print(f"  Log dir: {Config.LOG_DIR}")
        print(f"  Stop words: {len(Config.STOP_WORDS)} loaded")
        print(f"  Keywords to link: {len(Config.KEYWORDS_TO_LINK)} configured")
        print("✅ Configuration loaded")
        return True
    except Exception as e:
        print(f"❌ Config error: {e}")
        return False


def check_logger():
    """Verify logger works."""
    print("\n📝 Checking logger...")
    
    try:
        from pdfference.utils.logger import Logger
        from pdfference.config import Config
        
        Config.ensure_dirs()
        logger = Logger("VerificationTest", Config.LOG_DIR)
        
        logger.info("Test info message")
        logger.warning("Test warning message")
        logger.error("Test error message")
        logger.success("Test success message")
        
        if logger.ui_lines:
            print(f"✅ Logger working ({len(logger.ui_lines)} messages)")
        else:
            print("⚠️  Logger created but no output")
        return True
    except Exception as e:
        print(f"❌ Logger error: {e}")
        return False


def check_models():
    """Verify domain models work."""
    print("\n📋 Checking domain models...")
    
    try:
        from pdfference.core.models import Paper, ProcessingStats
        
        # Test Paper
        paper = Paper(
            doi="10.1234/test",
            title="Test Paper",
            authors=["Smith, John", "Doe, Jane"],
            abstract="Test abstract",
            year=2023
        )
        
        print(f"  Paper title: {paper.title}")
        print(f"  First author: {paper.first_author_lastname}")
        print(f"  Display authors: {paper.display_authors}")
        
        # Test ProcessingStats
        stats = ProcessingStats(processed=10, success=8)
        print(f"  Stats: {stats}")
        print(f"  Success rate: {stats.success_rate}%")
        
        print("✅ Models working")
        return True
    except Exception as e:
        print(f"❌ Model error: {e}")
        return False


def check_keyword_extractor():
    """Verify keyword extractor works."""
    print("\n🔍 Checking keyword extractor...")
    
    try:
        from pdfference.analysis.keyword_extractor import KeywordExtractor
        from pdfference.utils.logger import Logger
        
        logger = Logger("KWTest")
        extractor = KeywordExtractor(logger)
        
        text = "Smooth muscle cells regulate autophagy in response to cell stress."
        freq = extractor.extract(text)
        
        print(f"  Extracted {len(freq)} keywords from sample text")
        if freq:
            top = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:3]
            print(f"  Top: {top}")
        
        print("✅ Keyword extractor working")
        return True
    except Exception as e:
        print(f"❌ Extractor error: {e}")
        return False


def check_linker():
    """Verify linker works."""
    print("\n🔗 Checking linker...")
    
    try:
        from pdfference.core.linker import Linker
        from pdfference.utils.logger import Logger
        
        logger = Logger("LinkerTest")
        linker = Linker(logger)
        
        content = "Smooth muscle cells are important."
        keywords = {"Smooth muscle cells"}
        
        result = linker.apply_links_to_text(content, keywords)
        
        print(f"  Original: {content}")
        print(f"  Linked: {result}")
        
        if "[[Smooth muscle cells]]" in result:
            print("✅ Linker working")
            return True
        else:
            print("⚠️  Linker didn't add links")
            return False
    except Exception as e:
        print(f"❌ Linker error: {e}")
        return False


def main():
    """Run all checks."""
    print("=" * 70)
    print("  🚀 PDFerence Verification Script")
    print("=" * 70)
    
    checks = [
        check_imports,
        check_config,
        check_logger,
        check_models,
        check_keyword_extractor,
        check_linker,
    ]
    
    results = [check() for check in checks]
    
    print("\n" + "=" * 70)
    
    if all(results):
        print("✅ All checks passed! PDFerence is ready to use.")
        print("\n📚 Next steps:")
        print("  1. Set up .env with your vault path and email")
        print("  2. Run Streamlit UI: streamlit run pdfference/ui/app.py")
        print("  3. Or use CLI: python cli.py --help")
        print("=" * 70)
        return 0
    else:
        print(f"❌ {results.count(False)} check(s) failed.")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
