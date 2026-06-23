"""
Keyword persistence and approval tracking.
Maintains a JSON file of approved keywords with metadata.
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Optional


class KeywordStore:
    """Manage approved keywords in JSON file."""

    def __init__(self, store_path: Optional[Path] = None):
        self.store_path = Path(store_path) if store_path else Path("keywords_store.json")
        self.data = self._load()

    def _load(self) -> dict:
        """Load keywords from JSON file."""
        if self.store_path.exists():
            try:
                with open(self.store_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return self._default_store()
        return self._default_store()

    @staticmethod
    def _default_store() -> dict:
        """Return empty store structure."""
        return {
            "keywords": {},
            "last_scan": None,
            "metadata": {}
        }

    def save(self):
        """Persist keywords to JSON."""
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.store_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def add_keyword(self, keyword: str, date_added: Optional[str] = None):
        """Add keyword to approved set."""
        if keyword not in self.data["keywords"]:
            self.data["keywords"][keyword] = {
                "date_added": date_added or datetime.now().isoformat(),
                "status": "approved"
            }

    def get_all_keywords(self) -> set[str]:
        """Return all approved keywords."""
        return set(self.data["keywords"].keys())

    def contains(self, keyword: str) -> bool:
        """Check if keyword is known."""
        return keyword in self.data["keywords"]

    def remove_keyword(self, keyword: str) -> bool:
        """Remove a keyword. Returns True if keyword existed."""
        if keyword in self.data["keywords"]:
            del self.data["keywords"][keyword]
            return True
        return False

    def rename_keyword(self, old_name: str, new_name: str) -> bool:
        """Rename a keyword, preserving metadata. Returns True on success."""
        if old_name not in self.data["keywords"]:
            return False
        if new_name in self.data["keywords"]:
            return False
        self.data["keywords"][new_name] = self.data["keywords"].pop(old_name)
        return True

    def get_keyword_metadata(self, keyword: str) -> dict:
        """Get metadata for a keyword. Returns empty dict if not found."""
        return self.data["keywords"].get(keyword, {})

    def update_keyword_metadata(self, keyword: str, **kwargs):
        """Update metadata fields for a keyword."""
        if keyword in self.data["keywords"]:
            self.data["keywords"][keyword].update(kwargs)

    def merge_keyword(self, source_name: str, target_name: str) -> bool:
        """
        Merge two keywords. Removes source, keeps target.
        Returns True on success.
        """
        if source_name not in self.data["keywords"]:
            return False
        if target_name not in self.data["keywords"]:
            return False
        if source_name == target_name:
            return False
        del self.data["keywords"][source_name]
        return True

    def set_last_scan(self, date: str):
        """Update last scan timestamp."""
        self.data["last_scan"] = date

    def get_last_scan(self) -> Optional[str]:
        """Get last scan timestamp."""
        return self.data.get("last_scan")
