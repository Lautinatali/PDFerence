"""
Domain models for PDFerence.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Paper:
    """Represents a processed academic paper."""
    
    doi: str
    title: str
    authors: list[str]
    abstract: str
    year: Optional[int] = None
    journal: Optional[str] = None
    url: Optional[str] = None
    topics: list[str] = field(default_factory=list)
    
    @property
    def first_author_lastname(self) -> str:
        """Extract last name of first author safely."""
        if self.authors:
            # Format: "LastName, FirstName" → extract before comma
            return self.authors[0].split(",")[0].strip()
        return "Unknown"
    
    @property
    def display_authors(self) -> str:
        """Formatted author list for display."""
        if not self.authors:
            return "Unknown"
        if len(self.authors) == 1:
            return self.authors[0]
        return f"{self.authors[0]} et al."


@dataclass
class ProcessingResult:
    """Result of processing a single PDF."""
    
    success: bool
    pdf_path: Optional[Path] = None
    paper: Optional[Paper] = None
    note_path: Optional[Path] = None
    error_message: Optional[str] = None
    
    def __str__(self) -> str:
        if self.success:
            return f"✅ {self.pdf_path.name if self.pdf_path else 'Unknown'}"
        return f"❌ {self.error_message or 'Unknown error'}"


@dataclass
class ProcessingStats:
    """Statistics from a batch processing run."""
    
    processed: int = 0
    success: int = 0
    failed: int = 0
    duplicates: int = 0
    
    @property
    def success_rate(self) -> float:
        """Success rate as percentage."""
        if self.processed == 0:
            return 0.0
        return (self.success / self.processed) * 100
    
    def __str__(self) -> str:
        return (
            f"Processed: {self.processed} | Success: {self.success} | "
            f"Failed: {self.failed} | Duplicates: {self.duplicates} | "
            f"Success Rate: {self.success_rate:.1f}%"
        )
