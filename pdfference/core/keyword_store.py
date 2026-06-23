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

    def set_last_scan(self, date: str):
        """Update last scan timestamp."""
        self.data["last_scan"] = date

    def get_last_scan(self) -> Optional[str]:
        """Get last scan timestamp."""
        return self.data.get("last_scan")
