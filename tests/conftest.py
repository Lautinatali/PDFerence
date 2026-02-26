"""Pytest configuration and fixtures."""
import pytest
from pathlib import Path


@pytest.fixture
def sample_pdf_path(tmp_path):
    """Create a temporary sample PDF path."""
    return tmp_path / "sample.pdf"


@pytest.fixture
def sample_vault_path(tmp_path):
    """Create a temporary Obsidian vault."""
    vault = tmp_path / "vault"
    vault.mkdir()
    
    # Create a sample note
    note = vault / "test_note.md"
    note.write_text("""---
title: Test Paper
authors: Smith, John
---

# Abstract

This is a test abstract about smooth muscle cells and autophagy.
""")
    
    return vault
