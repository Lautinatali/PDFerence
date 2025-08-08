import requests
import os
from pathlib import Path
import re
import tkinter as tk
from tkinter import simpledialog

def clean_for_filename(text):
    """Limpia el texto para que sea válido como nombre de archivo."""
    text = re.sub(r'[\\/*?:"<>|]', '', text)  # caracteres ilegales en nombres de archivo
    text = text.replace('\n', ' ').strip()
    return text

def get_metadata_from_doi(doi):
    """Consulta la API de CrossRef y devuelve metadatos esenciales."""
    url = f"https://api.crossref.org/works/{doi}"
    r = requests.get(url)
    if r.status_code != 200:
        raise ValueError("DOI no encontrado o error al consultar CrossRef.")
    data = r.json()["message"]

    metadata = {
        "title": data.get("title", [""])[0],
        "authors": [f"{a.get('family', '')}, {a.get('given', '')}" for a in data.get("author", [])],
        "journal": data.get("container-title", [""])[0],
        "year": data.get("issued", {}).get("date-parts", [[None]])[0][0],
        "doi": data.get("DOI", ""),
        "url": data.get("URL", f"https://doi.org/{doi}"),
        "abstract": re.sub("<.*?>", "", data.get("abstract", "No abstract available."))
    }

    return metadata

def format_metadata_as_markdown(metadata):
    """Convierte los metadatos en un string en formato Markdown."""
    md = f"""---
title: "{metadata['title']}"
authors: {metadata['authors']}
journal: "{metadata['journal']}"
year: {metadata['year']}
doi: {metadata['doi']}
url: {metadata['url']}
tags: [paper]
---

# 📄 Resumen

{metadata['abstract']}

# 🧠 Notas personales

- 

# 🔗 Enlaces

[{metadata['url']}]({metadata['url']})
"""
    return md


def save_note_as_markdown(content, metadata, output_dir):
    """Guarda el contenido Markdown como archivo .md"""
    first_author = metadata['authors'][0].split(",")[0] if metadata['authors'] else "unknown"
    safe_title = clean_for_filename(metadata['title'])
    filename = f"{first_author} {metadata['year']} - {safe_title}.md"
    path = Path(output_dir) / filename
    path.write_text(content, encoding='utf-8')
    print(f"✅ Nota guardada en: {path}")
    return path

def open_note(path):
    """Abre la nota con el editor por defecto."""
    try:
        if os.name == 'nt':  # Windows
            os.startfile(path)
        elif os.name == 'posix':  # macOS / Linux
            os.system(f'open "{path}"' if sys.platform == "darwin" else f'xdg-open "{path}"')
    except Exception as e:
        print("⚠️ No se pudo abrir la nota automáticamente:", e)

def main():
    # Use tkinter to request the DOI via a simple GUI window
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    doi = simpledialog.askstring("DOI Input", "🔗 Ingresá el DOI del paper:")
    if not doi:
        print("❌ No DOI ingresado. Saliendo.")
        return
    output_dir = r"G:\Mi unidad\Zettelkasten\Zettelkasten\Rough Notes"  # Hardcoded path

    try:
        metadata = get_metadata_from_doi(doi.strip())
        md_content = format_metadata_as_markdown(metadata)
        note_path = save_note_as_markdown(md_content, metadata, output_dir)
        # open_note(note_path)  # Removed automatic opening
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
