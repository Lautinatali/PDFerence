"""
PDF processing: DOI extraction and file organization.
"""
import re
from pathlib import Path
from typing import Optional
import fitz  # PyMuPDF

from .models import Paper, ProcessingResult
from ..config import Config
from ..utils.logger import Logger


class PDFProcessor:
    """Handles DOI extraction from PDFs and file organization."""
    
    def __init__(self, logger: Optional[Logger] = None):
        self.logger = logger or Logger("PDFProcessor")
        self.config = Config()
        
        # Flexible DOI pattern (handles various formats)
        self.doi_pattern = re.compile(
            r"(?:doi\s*[:]?\s*|https?://(?:www\.)?doi\.org/|/doi/)?(10\.\d{4,9}/[-._;():/A-Z0-9]+)",
            re.IGNORECASE
        )
    
    def extract_doi_from_pdf(self, pdf_path: Path) -> Optional[str]:
        """
        Extract DOI from PDF with robust preprocessing.
        
        Returns:
            DOI string if found, None otherwise.
        """
        try:
            with fitz.open(pdf_path) as pdf:
                # Extract text from all pages
                text = "".join(page.get_text() for page in pdf)
                
                # Robust preprocessing
                # 1. Remove hyphens at line ends (split words)
                text = re.sub(r'-\s*\n', '', text)
                
                # 2. Normalize line breaks and spaces
                text = text.replace('\n', ' ').replace('\r', ' ')
                text = re.sub(r'\s+', ' ', text)
                
                # 3. Search for DOI pattern
                match = self.doi_pattern.search(text)
                if match:
                    doi = match.group(1).strip()
                    
                    # 4. Clean trailing punctuation
                    doi = re.sub(r"[\.,;:)]+$", "", doi)
                    
                    self.logger.debug(f"DOI extracted from {pdf_path.name}: {doi}")
                    return doi
                
                self.logger.debug(f"No DOI found in {pdf_path.name}")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to read PDF {pdf_path.name}: {e}")
            return None
    
    def organize_pdf(
        self,
        pdf_path: Path,
        dest_folder: Path,
        paper: Paper,
        check_exists: bool = True,
        move_to_input: bool = True
    ) -> Path:
        """
        Rename and move PDF based on paper metadata.
        
        Args:
            pdf_path: Current PDF location
            dest_folder: Destination folder for notes (not PDFs)
            paper: Paper metadata
            check_exists: If True, raise error on existing file
            move_to_input: If True, move original PDF to Input/ subfolder
        
        Returns:
            New PDF path
            
        Raises:
            FileExistsError: If destination file exists and check_exists=True
        """
        safe_title = self._clean_filename(paper.title)
        new_name = f"{paper.first_author_lastname} - {paper.year} - {safe_title}.pdf"
        
        # If moving to Input folder, place PDF there
        if move_to_input and pdf_path.parent.exists():
            input_folder = pdf_path.parent / "Input"
            input_folder.mkdir(parents=True, exist_ok=True)
        else:
            input_folder = dest_folder.parent if dest_folder else pdf_path.parent / "Input"
            input_folder.mkdir(parents=True, exist_ok=True)
        
        new_path = input_folder / new_name
        
        if new_path.exists() and check_exists:
            raise FileExistsError(f"PDF already exists: {new_name}")
        
        result_path = pdf_path.rename(new_path)
        self.logger.success(f"Moved to Input: {new_name}")
        
        return result_path
    
    @staticmethod
    def _clean_filename(text: str) -> str:
        """Sanitize text for use in filesystem."""
        # Remove illegal characters
        text = re.sub(r'[\\/*?:"<>|]', '', text)
        # Normalize whitespace
        text = text.replace('\n', ' ').strip()
        # Collapse multiple spaces
        text = re.sub(r'\s+', ' ', text)
        return text
