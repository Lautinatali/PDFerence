# Vault Maintenance Workflow — New Features Guide

## What Was Implemented

You now have a **persistent keyword management system** that tracks approved keywords and supports incremental vault maintenance.

### New Components

1. **`core/keyword_store.py`** — Manages approved keywords in JSON
2. **`date_added` field** — Added to `Paper` class and markdown frontmatter
3. **New CLI commands**:
   - `scan-new-papers` — Find new papers and extract candidate keywords
   - `review-keywords` — Interactively approve new keywords
   - `reindex-vault` — Re-link entire vault with current keyword set

### How It Works

**State** is stored in `keywords_store.json` (git-ignored by default):
```json
{
  "keywords": {
    "Smooth Muscle Cells": {"date_added": "2026-06-20", "status": "approved"},
    "m6A": {"date_added": "2026-06-20", "status": "approved"},
    "autophagy": {"date_added": "2026-06-21", "status": "approved"}
  },
  "last_scan": "2026-06-23T15:30:00",
  "metadata": {}
}
```

---

## Initial Setup (One-Time)

### Step 1: Extract initial keywords from vault
```bash
python cli.py extract-keywords -v "C:\Vault" --header "Abstract" -o keywords.csv
```
Shows the top keywords from all papers in your vault.

### Step 2: Interactively approve keywords
```bash
python cli.py review-keywords -v "C:\Vault" --min-count 2 --limit 50
```

**Interactive loop**:
```
Review 50 keyword candidates:

✓ Add 'smooth muscle cells' (42 occurrences)? [y/n/skip]: y
Added: smooth muscle cells

✓ Add 'autophagy' (38 occurrences)? [y/n/skip]: y
Added: autophagy

✓ Add 'noise phrase' (5 occurrences)? [y/n/skip]: n
```

- Type `y` to approve
- Type `n` to skip
- Type `skip` to move to next (don't approve, but don't add to list)

When done, `keywords_store.json` is created + `last_scan` timestamp is set.

### Step 3: Link entire vault
```bash
python cli.py reindex-vault -v "C:\Vault"
```

Output:
```
Reindexing vault with 15 keywords
Reindex complete: 120/150 files modified
```

---

## Maintenance Workflow (Repeat Monthly/Weekly)

### Step 1: Add new papers
```bash
# Copy 10 new PDFs to a folder
python cli.py process-pdfs "C:\NewPDFs" -o "C:\Vault\Notes"
```

Each new note gets a `date_added` field automatically with today's date.

### Step 2: Scan for new candidate keywords
```bash
python cli.py scan-new-papers -v "C:\Vault" --min-count 2
```

**Output example**:
```
Scanning for papers added since 2026-06-23T15:30:00
Found 10 new papers

📊 Found 27 new keyword candidates:
  • cell migration: 8 occurrences
  • gene expression: 7 occurrences
  • protein interaction: 6 occurrences
  • ...
```

This only extracts keywords from papers added *after* `last_scan`.

### Step 3: Review and approve new keywords
```bash
python cli.py review-keywords -v "C:\Vault" --min-count 2 --limit 30
```

Same interactive loop as initial setup. Approve the keywords you want to track.

### Step 4: Re-link entire vault
```bash
python cli.py reindex-vault -v "C:\Vault"
```

**What happens**:
- Old papers: New keywords are linked in their abstracts
- New papers: All keywords (old + new) are linked
- Already-linked keywords: Skipped (safe to re-run)

---

## Understanding the Commands

### `scan-new-papers`

**What it does**:
1. Loads `last_scan` timestamp from `keywords_store.json`
2. Finds all `.md` files with `date_added > last_scan`
3. Extracts keywords from titles + abstracts of new papers only
4. Compares with approved keywords
5. Shows candidates not yet approved

**Why useful**:
- Fast: Only processes new papers
- Shows what's trending in recent additions
- Lets you decide if new concepts should be linked

**Options**:
```bash
python cli.py scan-new-papers \
  -v "C:\Vault"              # Vault path
  -m 2                       # Min occurrences (default: 2)
```

---

### `review-keywords`

**What it does**:
1. Finds new candidate keywords (same as scan-new-papers)
2. Prompts you interactively for each one
3. Saves approved keywords to `keywords_store.json`
4. Updates `last_scan` timestamp

**Why interactive**:
- You control vocabulary (no auto-linking)
- Catch typos before they spread
- Decide what's important to your research

**Options**:
```bash
python cli.py review-keywords \
  -v "C:\Vault"              # Vault path
  -m 2                       # Min occurrences
  -l 30                      # Show max 30 keywords
```

**Responses**:
- `y` — Approve and add to `keywords_store.json`
- `n` — Skip and don't add
- `skip` — Move to next (don't add to list, don't record decision)
- `Enter` (blank) — Treated as `n`

---

### `reindex-vault`

**What it does**:
1. Loads all approved keywords from `keywords_store.json`
2. Iterates through all `.md` files in vault
3. Injects `[[keyword]]` wikilinks where found
4. Skips already-linked text
5. Reports files processed + modified

**Why safe to re-run**:
- Regex pattern `(?<!\[\[)...(?!\]\])` avoids already-linked text
- Running twice doesn't double-link
- Safe to run after approving new keywords

**Options**:
```bash
python cli.py reindex-vault \
  -v "C:\Vault"             # Vault path
```

---

## Typical Monthly Workflow

```bash
# 1. Add new PDFs
python cli.py process-pdfs "C:\NewPDFs" -o "C:\Vault\Notes"

# 2. Preview what's new
python cli.py scan-new-papers -v "C:\Vault"

# 3. Approve keywords you want to track
python cli.py review-keywords -v "C:\Vault" -l 25

# 4. Link the vault (old papers get new keywords, new papers get all)
python cli.py reindex-vault -v "C:\Vault"
```

Total time: ~1-2 minutes for 10 papers + 20 keyword approvals.

---

## Files and State

### `keywords_store.json`
- Location: Project root (same dir as `cli.py`)
- Format: JSON
- Contains: Approved keywords + last scan timestamp
- **Should be committed to git** (it's your keyword vocabulary)

### `date_added` in notes
- Added automatically by `NoteGenerator`
- Format: ISO 8601 (e.g., `2026-06-23T15:30:00`)
- Used to find "new papers" since last scan
- Human-readable in YAML frontmatter

### Example note frontmatter:
```yaml
---
title: "Cell Migration in Smooth Muscle"
authors: [Smith, John]
year: 2023
date_added: 2026-06-23T13:25:47  # Auto-added here
topics: []
---
```

---

## Troubleshooting

### Q: "No new papers found"
**Likely cause**: `date_added` in existing papers is older than `last_scan`
**Fix**: 
```bash
# Option 1: Reset last_scan to earlier date
# Edit keywords_store.json, change "last_scan": null

# Option 2: Rescan everything
rm keywords_store.json  # Clears state
python cli.py review-keywords  # Treats all papers as "new"
```

### Q: "No approved keywords found"
**Cause**: `keywords_store.json` is missing or empty
**Fix**:
```bash
python cli.py review-keywords -v "C:\Vault"  # Run review first
```

### Q: Keywords not linking in old papers
**Cause**: They weren't approved yet
**Fix**:
```bash
python cli.py review-keywords -v "C:\Vault"  # Approve them
python cli.py reindex-vault -v "C:\Vault"    # Re-link
```

### Q: Some text is NOT linking but it matches a keyword
**Likely cause**: It's already linked, or it's in the YAML frontmatter
**Behavior**: This is correct. Linker skips already-linked text and YAML.

---

## Backing Up Keywords

Since `keywords_store.json` contains your approved vocabulary:

```bash
# Option 1: Commit to git (recommended)
git add keywords_store.json
git commit -m "Update approved keywords"

# Option 2: Manual backup
copy keywords_store.json keywords_store.backup.json
```

---

## Future Extensions

This system is designed to be extensible. Possible future additions:

- **Keyword scoring**: Track frequency trends over time
- **Synonym groups**: "SMC" → "Smooth Muscle Cells" mapping
- **Category tags**: Organize keywords by research area
- **Auto-approval rules**: Auto-link high-frequency terms
- **Database backend**: Switch from JSON to SQLite for larger vaults

The JSON structure allows easy migration without code changes.

---

## Summary

| Task | Command | Time |
|------|---------|------|
| **Initial setup** | `review-keywords`, then `reindex-vault` | 5-10 min |
| **Monthly refresh** | `scan-new-papers` + `review-keywords` + `reindex-vault` | 2-5 min |
| **Add single paper** | `process-pdfs` + `reindex-vault` | 1 min |
| **Manage keywords** | Edit `keywords_store.json` directly | 1 min |

Your vault is now **maintainable, not one-time-use**.
