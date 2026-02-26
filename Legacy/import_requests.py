import requests
import os
from pathlib import Path
import re
import tkinter as tk
from tkinter import simpledialog
from bs4 import BeautifulSoup

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



def get_abstract_from_api(doi, email="lnatali@immf.uncor.edu"):
    """
    Fetches ONLY the abstract text from PubMed using XML parsing.
    """
    # 1. Search for the PMID using the DOI
    search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": doi,
        "retmode": "json",
        "email": email
    }
    
    try:
        # Step A: Get the ID (PMID)
        r = requests.get(search_url, params=params, timeout=10)
        if r.status_code != 200: return None
        
        data = r.json()
        id_list = data.get("esearchresult", {}).get("idlist", [])
        
        if not id_list:
            return None # DOI not found in PubMed
        
        pmid = id_list[0]
        
        # Step B: Fetch the XML record for that PMID
        fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        fetch_params = {
            "db": "pubmed",
            "id": pmid,
            "retmode": "xml",  # <--- This is the key change!
            "email": email
        }
        
        xml_resp = requests.get(fetch_url, params=fetch_params, timeout=10)
        
        if xml_resp.status_code == 200:
            # Parse XML with BeautifulSoup
            soup = BeautifulSoup(xml_resp.content, "xml")
            
            # Extract text from <AbstractText> tags
            # Sometimes abstracts are split into sections (Background, Methods, etc.)
            abstract_tags = soup.find_all("AbstractText")
            
            if abstract_tags:
                # Join all sections with a space
                full_abstract = " ".join([tag.get_text(strip=True) for tag in abstract_tags])
                return full_abstract
            
    except Exception as e:
        print(f"⚠️ API Error: {e}")
        
    return None

def get_metadata_from_openalex(doi, email="lnatali@immf.uncor.edu"):
    """Fetch metadata from OpenAlex and rebuild the abstract."""
    # Ensure the DOI is just the identifier
    clean_doi = doi.replace("https://doi.org/", "")
    url = f"https://api.openalex.org/works/https://doi.org/{clean_doi}?mailto={email}"
    
    r = requests.get(url)
    if r.status_code != 200:
        return {"error": f"Error {r.status_code}: Could not find DOI or API error."}
    
    data = r.json()

    metadata = {
        "title": data.get("display_name", ""),
        "authors": [a.get("author", {}).get("display_name", "") for a in data.get("authorships", [])],
        "journal": data.get("primary_location", {}).get("source", {}).get("display_name", ""),
        "year": data.get("publication_year"),
        "doi": data.get("doi", ""),
        "url": data.get("doi", f"https://doi.org/{clean_doi}"),
        "abstract": data.get("abstract"),
        "topics": [t.get("display_name") for t in data.get("topics", [])] # Bonus: OpenAlex tags
    }

    # Helper to rebuild abstract from inverted index
    def rebuild_abstract(index):
        if not index:
            return "No abstract available."
        # Create a list with enough space for all words
        # The index is { "Word": [pos1, pos2], ... }
        word_positions = []
        for word, positions in index.items():
            for pos in positions:
                word_positions.append((pos, word))
        
        # Sort by position and join
        word_positions.sort()
        return " ".join([word for pos, word in word_positions])
    
    # 1. Try OpenAlex Abstract
    abstract = rebuild_abstract(data.get("abstract_inverted_index"))

    # 2. Plan B: PubMed (High success rate for Bio/Med)
    if not abstract or "No abstract available" in abstract:
        print(f"🔍 Abstract missing in OpenAlex. Trying Plan B (PubMed)...")
        abstract = get_abstract_from_api(clean_doi)

    # Final fallback
    if not abstract:
        abstract = "Abstract truly unavailable."

    metadata["abstract"] = abstract
    return metadata


def format_metadata_as_markdown(metadata):
    """Convierte los metadatos en un string en formato Markdown."""
    md = f"""---
title: "{metadata['title']}"
authors: {metadata['authors']}
journal: "{metadata['journal']}"
year: {metadata['year']}
doi: {metadata['doi']}
topics: {metadata.get('topics', [])}
tags: [unread]

---

# 📄 Abstract

{metadata['abstract']}

# 🧠 Personal Notes

- 

# 🔗 Why does it matter?
"""
    return md


def save_note_as_markdown(content, metadata, output_dir):
    """Guarda el contenido Markdown como archivo .md"""
    first_author = metadata['authors'][0].split()[-1]
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
    output_dir = r"G:\Mi unidad\Input_network\Input_network"  # Hardcoded path

    try:
        metadata = get_metadata_from_doi(doi.strip())
        md_content = format_metadata_as_markdown(metadata)
        note_path = save_note_as_markdown(md_content, metadata, output_dir)
        # open_note(note_path)  # Removed automatic opening
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
