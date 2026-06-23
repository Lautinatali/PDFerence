"""
Wikilink injection: convert keyword mentions to [[links]].
Shared between CLI, Streamlit UI, and standalone scripts.
"""
import re
from pathlib import Path
from typing import Set, Optional

from ..utils.logger import Logger


class Linker:
    """Insert [[wikilinks]] into Markdown files."""
    
    def __init__(self, logger: Optional[Logger] = None):
        self.logger = logger or Logger("Linker")
    
    def apply_links_to_text(
        self,
        content: str,
        keywords: Set[str],
        skip_yaml: bool = True
    ) -> str:
        """
        Replace keyword occurrences with [[keyword]] wikilinks.
        
        Args:
            content: Markdown content
            keywords: Set of keywords to link
            skip_yaml: If True, skip YAML frontmatter
        
        Returns:
            Modified content with wikilinks
        """
        if not keywords:
            return content
        
        # Optionally split YAML frontmatter
        if skip_yaml:
            parts = re.split(
                r'(^---\n.*?\n---)',
                content,
                maxsplit=1,
                flags=re.DOTALL | re.MULTILINE
            )
        else:
            parts = [content]
        
        def process_body(text):
            # Sort by length (longest first) to avoid partial replacements
            for word in sorted(keywords, key=len, reverse=True):
                if not word.strip():
                    continue
                
                # Pattern: word boundary, not already linked
                pattern = rf'(?<!\[\[)(?<!\[)\b({re.escape(word)})\b(?!\]\])(?!\]\()'
                
                def replacement(match):
                    matched_text = match.group(1)
                    # Simple link if exact case match, otherwise use alias
                    if matched_text == word:
                        return f"[[{word}]]"
                    # Alias format: [[Keyword|ActualText]]
                    return f"[[{word}|{matched_text}]]"
                
                text = re.compile(pattern, re.IGNORECASE).sub(replacement, text)
            
            return text
        
        # Reconstruct with YAML
        if skip_yaml and len(parts) > 1:
            return parts[0] + parts[1] + process_body(parts[2])
        return process_body(parts[0])
    
    def apply_links_to_file(
        self,
        file_path: Path,
        keywords: Set[str],
        skip_yaml: bool = True
    ) -> bool:
        """
        Apply links to a Markdown file in-place.
        
        Args:
            file_path: Path to .md file
            keywords: Set of keywords to link
            skip_yaml: If True, skip YAML frontmatter
        
        Returns:
            True if file was modified, False otherwise
        """
        try:
            original = file_path.read_text(encoding="utf-8")
            modified = self.apply_links_to_text(original, keywords, skip_yaml)
            
            if modified != original:
                file_path.write_text(modified, encoding="utf-8")
                self.logger.debug(f"Wikilinks applied: {file_path.name}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to apply links to {file_path.name}: {e}")
            return False
    
    def apply_links_to_vault(
        self,
        vault_path: Path,
        keywords: Set[str],
        skip_yaml: bool = True
    ) -> tuple[int, int]:
        """
        Apply links to all .md files in vault.
        
        Args:
            vault_path: Root path of vault
            keywords: Set of keywords to link
            skip_yaml: If True, skip YAML frontmatter
        
        Returns:
            Tuple of (files_processed, files_modified)
        """
        vault_path = Path(vault_path)
        if not vault_path.exists():
            self.logger.error(f"Vault path not found: {vault_path}")
            return 0, 0
        
        processed = 0
        modified = 0
        
        for md_file in vault_path.rglob("*.md"):
            processed += 1
            if self.apply_links_to_file(md_file, keywords, skip_yaml):
                modified += 1
        
        self.logger.info(f"Linker complete: {modified}/{processed} files modified")
        return processed, modified

    def merge_keywords_in_vault(
        self,
        vault_path: Path,
        source_keyword: str,
        target_keyword: str,
    ) -> int:
        """
        Replace all occurrences of source keyword with target keyword in vault.
        Updates [[source]] -> [[target]] and [[source|alias]] -> [[target|alias]]

        Args:
            vault_path: Root path of vault
            source_keyword: Keyword to replace
            target_keyword: Keyword to replace with

        Returns:
            Count of files modified
        """
        vault_path = Path(vault_path)
        if not vault_path.exists():
            self.logger.error(f"Vault path not found: {vault_path}")
            return 0

        modified = 0

        for md_file in vault_path.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                original = content

                # Pattern 1: [[source]] -> [[target]]
                pattern1 = rf"\[\[{re.escape(source_keyword)}\]\]"
                content = re.sub(pattern1, f"[[{target_keyword}]]", content)

                # Pattern 2: [[source|alias]] -> [[target|alias]]
                pattern2 = rf"\[\[{re.escape(source_keyword)}\|([^\]]+)\]\]"
                content = re.sub(pattern2, f"[[{target_keyword}|\\1]]", content)

                if content != original:
                    md_file.write_text(content, encoding="utf-8")
                    modified += 1
                    self.logger.info(f"Merged keyword in {md_file.name}")

            except Exception as e:
                self.logger.error(f"Failed to merge keywords in {md_file.name}: {e}")

        self.logger.info(f"Keyword merge complete: {modified} files modified")
        return modified
