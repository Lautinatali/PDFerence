"""
Keyword extraction and analysis.
"""
import re
from collections import Counter
from pathlib import Path
from typing import Optional

from ..config import Config
from ..utils.logger import Logger


class KeywordExtractor:
    """
    Extract and deduplicate n-grams (keywords) from text.
    Filters out stop words and academic noise.
    """
    
    def __init__(self, logger: Optional[Logger] = None):
        self.logger = logger or Logger("KeywordExtractor")
        self.config = Config()
    
    def extract(
        self,
        text: str,
        min_gram: int = 1,
        max_gram: int = 3
    ) -> Counter:
        """
        Extract n-grams from text, filtering noise.
        
        Args:
            text: Text to analyze
            min_gram: Minimum gram size (1 = unigrams)
            max_gram: Maximum gram size (3 = trigrams)
        
        Returns:
            Counter with gram frequencies
        """
        tokens = self._tokenize(text)
        if not tokens:
            return Counter()
        
        counts = Counter()
        
        for n in range(min_gram, max_gram + 1):
            grams = [tokens[i:i+n] for i in range(len(tokens) - n + 1)]
            valid = [
                " ".join(g) for g in grams
                if self._is_valid_gram(g)
            ]
            counts.update(valid)
        
        return counts
    
    def extract_from_vault(
        self,
        vault_path: Path,
        target_header: str = "Abstract",
        min_gram: int = 1,
        max_gram: int = 3
    ) -> Counter:
        """
        Extract keywords from all notes in vault.
        
        Args:
            vault_path: Root path of vault
            target_header: Section to extract from (e.g., "# Abstract")
            min_gram: Minimum gram size
            max_gram: Maximum gram size
        
        Returns:
            Counter with all keywords
        """
        vault_path = Path(vault_path)
        if not vault_path.exists():
            self.logger.error(f"Vault path not found: {vault_path}")
            return Counter()
        
        all_counts = Counter()
        
        for md_file in vault_path.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                
                # Extract section under header
                section_text = self._extract_section(content, target_header)
                if section_text:
                    counts = self.extract(section_text, min_gram, max_gram)
                    all_counts.update(counts)
                    
            except Exception as e:
                self.logger.debug(f"Error processing {md_file.name}: {e}")
                continue
        
        self.logger.info(f"Extracted {len(all_counts)} unique keywords from vault")
        return all_counts
    
    def deduplicate(
        self,
        freq: Counter,
        min_count: int = 2
    ) -> list[tuple[str, int]]:
        """
        Remove substring redundancy; prefer longer forms.
        
        Args:
            freq: Counter of keywords
            min_count: Minimum occurrences to include
        
        Returns:
            Sorted list of (keyword, count) tuples
        """
        seen = set()
        # Sort: longest first, then by frequency
        candidates = sorted(
            freq.items(),
            key=lambda x: (len(x[0]), x[1]),
            reverse=True
        )
        
        result = []
        
        for concept, count in candidates:
            if count < min_count:
                continue
            
            # Check if this is a substring of a longer, frequent concept
            is_redundant = any(
                concept in longer and freq[longer] * 1.5 >= count
                for longer in seen
            )
            
            if not is_redundant:
                seen.add(concept)
                result.append((concept, count))
        
        # Re-sort by frequency for final output
        result.sort(key=lambda x: x[1], reverse=True)
        return result
    
    def _tokenize(self, text: str) -> list[str]:
        """
        Tokenize text with placeholder filtering and Unicode normalization.
        
        Args:
            text: Text to tokenize
        
        Returns:
            List of lowercase tokens
        """
        # Check for placeholder strings
        if not text or any(
            placeholder in text.lower()
            for placeholder in self.config.ABSTRACT_PLACEHOLDERS
        ):
            return []
        
        # Normalize superscripts and subscripts to regular characters
        # e.g., ⁶ → 6, ₆ → 6, ᶜ → c, ᴬ → A
        text = ''.join(
            self._normalize_unicode_char(char)
            for char in text
        )
        
        # Normalize separators (hyphens, slashes become spaces)
        text = re.sub(r'[/\\-]', ' ', text)
        
        # Remove non-alphanumeric (keep accents)
        text = re.sub(r'[^a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s]', '', text)
        
        return text.lower().split()
    
    def _is_valid_gram(self, gram: list[str]) -> bool:
        """
        Check if n-gram is a meaningful concept.
        
        Args:
            gram: List of tokens forming an n-gram
        
        Returns:
            True if gram is valid, False otherwise
        """
        gram_str = " ".join(gram)
        
        # Rule 1: Don't start/end with stop words
        if gram[0] in self.config.STOP_WORDS or gram[-1] in self.config.STOP_WORDS:
            return False
        
        # Rule 2: Don't include academic noise phrases
        if gram_str in self.config.ACADEMIC_NOISE:
            return False
        
        # Rule 3: Minimum length + not in stop words
        if len(gram_str) < 3 or gram_str in self.config.STOP_WORDS:
            return False
        
        return True
    
    @staticmethod
    def _normalize_unicode_char(char: str) -> str:
        """
        Convert Unicode superscripts and subscripts to normal characters.
        
        Args:
            char: Single character to normalize
        
        Returns:
            Normalized character
        """
        # Superscript mappings
        superscript_map = {
            '⁰': '0', '¹': '1', '²': '2', '³': '3', '⁴': '4', '⁵': '5',
            '⁶': '6', '⁷': '7', '⁸': '8', '⁹': '9',
            'ᴬ': 'A', 'ᴮ': 'B', 'ᴰ': 'D', 'ᴱ': 'E', 'ᴳ': 'G', 'ᴴ': 'H',
            'ᴵ': 'I', 'ᴶ': 'J', 'ᴷ': 'K', 'ᴸ': 'L', 'ᴹ': 'M', 'ᴺ': 'N',
            'ᴼ': 'O', 'ᴾ': 'P', 'ᴿ': 'R', 'ˢ': 'S', 'ᵀ': 'T', 'ᴰ': 'D',
            'ᵁ': 'U', 'ᵀ': 'T', 'ⁿ': 'n', 'ˣ': 'x', 'ʸ': 'y', 'ᶜ': 'c',
            'ᴬ': 'a', 'ᵇ': 'b', 'ᶜ': 'c', 'ᵈ': 'd', 'ᵉ': 'e', 'ᶠ': 'f',
            'ᵍ': 'g', 'ʰ': 'h', 'ⁱ': 'i', 'ʲ': 'j', 'ᵏ': 'k', 'ˡ': 'l',
            'ᵐ': 'm', 'ⁿ': 'n', 'ᵒ': 'o', 'ᵖ': 'p', 'ʳ': 'r', 'ˢ': 's',
            'ᵗ': 't', 'ᵘ': 'u', 'ᵛ': 'v', 'ʷ': 'w', 'ˣ': 'x', 'ʸ': 'y',
            'ᶻ': 'z', 'ᶜ': 'c', 'ᵐ': 'm',
        }
        
        # Subscript mappings
        subscript_map = {
            '₀': '0', '₁': '1', '₂': '2', '₃': '3', '₄': '4', '₅': '5',
            '₆': '6', '₇': '7', '₈': '8', '₉': '9',
            'ₐ': 'a', 'ₑ': 'e', 'ᵢ': 'i', 'ₒ': 'o', 'ᵤ': 'u', 'ₓ': 'x',
            'ₙ': 'n', 'ₘ': 'm', 'ₕ': 'h', 'ₚ': 'p', 'ₜ': 't', 'ₛ': 's',
        }
        
        return superscript_map.get(char, subscript_map.get(char, char))
    
    @staticmethod
    def _extract_section(content: str, header: str) -> str:
        """
        Extract content under a specific header.
        
        Args:
            content: Full Markdown content
            header: Header name (e.g., "Abstract")
        
        Returns:
            Text content under header
        """
        # Pattern: match header, capture until next header or EOF
        pattern = rf'^#\s+.*?{re.escape(header)}.*?\n(.*?)(?=\n# |\Z)'
        match = re.search(pattern, content, re.DOTALL | re.MULTILINE | re.IGNORECASE)
        
        if match:
            return match.group(1).strip()
        return ""
