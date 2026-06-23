"""
Note generation: convert metadata to Obsidian-compatible Markdown.
"""
from pathlib import Path
from typing import Optional
from datetime import datetime

from .models import Paper
from ..config import Config
from ..utils.logger import Logger


class NoteGenerator:
    """Convert paper metadata to Obsidian Markdown notes."""
    
    def __init__(self, logger: Optional[Logger] = None):
        self.logger = logger or Logger("NoteGenerator")
        self.config = Config()
    
    def generate_markdown(self, paper: Paper) -> str:
        """
        Generate Markdown content for a paper note.

        Args:
            paper: Paper metadata

        Returns:
            Markdown string with YAML frontmatter
        """
        # YAML frontmatter
        authors_str = ", ".join(paper.authors) if paper.authors else "Unknown"
        topics_str = ", ".join(paper.topics) if paper.topics else ""
        date_added = paper.date_added.isoformat() if paper.date_added else datetime.now().isoformat()

        md = f'''---
title: "{self._escape_yaml(paper.title)}"
authors: [{authors_str}]
journal: "{self._escape_yaml(paper.journal or 'Unknown')}"
year: {paper.year or 0}
doi: {paper.doi}
date_added: {date_added}
topics: [{topics_str}]
tags: [unread]
url: {paper.url or f"https://doi.org/{paper.doi}"}
---

# 📄 Abstract

{paper.abstract}

# 🧠 Personal Notes

-

# 🔗 Why does it matter?
'''
        return md
    
    def save_note(self, paper: Paper, output_dir: Path) -> Path:
        """
        Save note to file.
        
        Args:
            paper: Paper metadata
            output_dir: Directory to save note
        
        Returns:
            Path to saved note
            
        Raises:
            IOError: If write fails
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        safe_title = self._clean_filename(paper.title)
        filename = f"{paper.first_author_lastname} {paper.year} - {safe_title}.md"
        
        # Generate content
        content = self.generate_markdown(paper)
        
        # Write file
        file_path = output_dir / filename
        file_path.write_text(content, encoding='utf-8')
        
        self.logger.success(f"Note saved: {filename}")
        return file_path
    
    @staticmethod
    def _escape_yaml(text: str) -> str:
        """Escape special characters for YAML."""
        if not text:
            return ""
        # Simple escaping: quote if contains special chars
        if any(c in text for c in ['"', "'", '\n', ':']):
            return text.replace('"', '\\"')
        return text
    
    @staticmethod
    def _clean_filename(text: str) -> str:
        """Sanitize text for filesystem."""
        import re
        text = re.sub(r'[\\/*?:"<>|]', '', text)
        return text.replace('\n', ' ').strip()
