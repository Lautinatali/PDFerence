"""
Central configuration for PDFerence.
Use environment variables to override defaults.
"""
import os
from pathlib import Path
from typing import Optional


class Config:
    """Single source of truth for all settings."""

    # ═══════════════════════════════════════════════════════════════════════
    # PATHS
    # ═══════════════════════════════════════════════════════════════════════
    PROJECT_ROOT: Path = Path(__file__).parent.parent
    LOG_DIR: Path = PROJECT_ROOT / "logs"
    
    # PDF processing folder
    PDF_FOLDER: Path = Path(
        os.getenv("PDF_FOLDER", "")
    ) if os.getenv("PDF_FOLDER") else None
    
    # Obsidian vault (where notes are saved)
    VAULT_PATH: Path = Path(
        os.getenv("VAULT_PATH", r"G:\Mi unidad\Input_network\Input_network")
    )
    OBSIDIAN_OUTPUT: Path = VAULT_PATH / "Notes"
    
    # Move processed PDFs to Input subfolder
    MOVE_PDFS_TO_INPUT: bool = os.getenv("MOVE_PDFS_TO_INPUT", "true").lower() == "true"
    
    # ═══════════════════════════════════════════════════════════════════════
    # API CONFIGURATION
    # ═══════════════════════════════════════════════════════════════════════
    PUBMED_EMAIL: str = os.getenv(
        "PUBMED_EMAIL", "lnatali@immf.uncor.edu"
    )
    CROSSREF_TIMEOUT: int = 10
    OPENALEX_TIMEOUT: int = 10
    
    # ═══════════════════════════════════════════════════════════════════════
    # KEYWORD EXTRACTION
    # ═══════════════════════════════════════════════════════════════════════
    STOP_WORDS: set[str] = {
        'of', 'in', 'to', 'for', 'with', 'on', 'at', 'by', 'from', 'is', 'are', 'was', 'were',
        'the', 'a', 'an', 'and', 'or', 'as', 'be', 'been', 'being', 'it', 'its', 'this', 'that',
        'which', 'who', 'these', 'those', 'we', 'our', 'their', 'they', 'into', 'has', 'have',
        'not', 'but', 'than', 'more', 'also', 'such', 'very', 'can', 'may', 'however', 'during',
        'specific', 'factor', 'identified', 'using', 'well', 'both', 'between', 'through',
        'here', 'there', 'results', 'showed', 'highly',
        'show', 'shows', 'shown', 'including', 'study', 'used',
    }
    
    ABSTRACT_PLACEHOLDERS: set[str] = {
        "no abstract available",
        "abstract available",
        "no abstract",
    }
    
    ACADEMIC_NOISE: set[str] = {
        'role in', 'roles in', 'response to', 'in response', 'understanding of',
        'we found', 'development of', 'involved in', 'loss of', 'associated with',
        'it is', 'there is', 'due to', 'well as', 'as well as', 'here we', 'shown to',
        'plays a', 'play a', 'the expression', 'expression of', 'levels of',
    }
    
    MIN_KEYWORD_COUNT: int = 2
    TOP_KEYWORDS_LIMIT: int = 100
    KEYWORD_MIN_GRAM: int = 1
    KEYWORD_MAX_GRAM: int = 3
    
    # ═══════════════════════════════════════════════════════════════════════
    # WIKILINKS
    # ═══════════════════════════════════════════════════════════════════════
    KEYWORDS_TO_LINK: list[str] = [
        'Smooth Muscle Cells',
        'SMC',
        'METTL3',
        'YTHDF2',
        'YTHDF',
        'Autophagy',
        'm6A',
        'Notch',
        'Cancer',
        'Development',
        'Proliferation',
    ]
    
    # ═══════════════════════════════════════════════════════════════════════
    # PROCESSING
    # ═══════════════════════════════════════════════════════════════════════
    PDF_PROCESSING_TIMEOUT: int = 30
    
    @classmethod
    def ensure_dirs(cls):
        """Ensure all required directories exist."""
        cls.LOG_DIR.mkdir(exist_ok=True, parents=True)
        cls.OBSIDIAN_OUTPUT.mkdir(exist_ok=True, parents=True)
