import requests
import re
import os
from pathlib import Path
import fitz # PyMuPDF


def clean_for_filename(text):
    """Limpia el texto para que sea válido como nombre de archivo."""
    text = re.sub(r'[\\/*?:"<>|]', '', text)  # caracteres ilegales
    text = text.replace('\n', ' ').strip()
    return text


def get_metadata_from_doi(doi):
    """Consulta la API de CrossRef y devuelve metadatos esenciales."""
    url = f"https://api.crossref.org/works/{doi}"
    try:
        r = requests.get(url)
        r.raise_for_status()  # Lanza una excepción si la respuesta es un error
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Error de red o DOI {doi} no encontrado: {e}")

    data = r.json()["message"]
    metadata = {
        "title": data.get("title", [""])[0],
        "authors": [f"{a.get('family', '')}, {a.get('given', '')}" for a in data.get("author", [])],
        "year": data.get("issued", {}).get("date-parts", [[None]])[0][0]
    }
    return metadata


def extract_doi_from_pdf(file_path):
    """Intenta encontrar un DOI en el texto del PDF."""
    # Regex estricto para DOI, pero permite prefijos comunes
    doi_pattern = re.compile(
        r"(?:doi\s*[:]?\s*|https?://(?:www\.)?doi\.org/|/doi/)?"
        r"(10\.\d{4,9}/[-._;()/:A-Z0-9]+)",
        re.IGNORECASE
    )
    try:
        with fitz.open(file_path) as pdf:
            # Leer todo el texto del PDF (sin límite de páginas)
            text = "".join(page.get_text() for page in pdf)
             # Unir líneas solo si el salto está justo después de un slash o punto (caso típico de DOI partido)
            text = re.sub(r"/(\r?\n|\r|\n)", "/", text)
            text = re.sub(r"\.(\r?\n|\r|\n)", ".", text)
        match = doi_pattern.search(text)
        if match:
            # El DOI está en el primer grupo de captura
            return match.group(1)
        return None
    except Exception as e:
        print(f"⚠️ No se pudo leer {file_path}: {e}")
        return None


def rename_pdfs_in_folder(folder_path):
    """Procesa y renombra archivos PDF en una carpeta."""
    folder = Path(folder_path)
    if not folder.is_dir():
        print(f"❌ La carpeta no existe: {folder_path}")
        return

    input_folder = folder / "Input"
    error_folder = folder / "Error"
    input_folder.mkdir(exist_ok=True)
    error_folder.mkdir(exist_ok=True)

    for pdf_file in folder.glob("*.pdf"):
        print(f"📄 Procesando: {pdf_file.name}")
        doi = extract_doi_from_pdf(pdf_file)
        if doi and doi[-1] in ".);":
            print(f"   [DEBUG] DOI termina en '{doi[-1]}', se elimina: {doi}")
            doi = doi[:-1]
        print(f"   [DEBUG] DOI extraído: {doi}")
        if not doi:
            print("   ❌ DOI no encontrado en el archivo.")
            # Mover a Error
            dest = error_folder / pdf_file.name
            pdf_file.rename(dest)
            continue

        try:
            metadata = get_metadata_from_doi(doi)
            print(f"   [DEBUG] Metadatos obtenidos: {metadata}")
            first_author = metadata['authors'][0].split(",")[0] if metadata['authors'] else "unknown"
            safe_title = clean_for_filename(metadata['title'])
            new_name = f"{first_author} - {metadata['year']} - {safe_title}.pdf"
            new_path = input_folder / new_name

            # Usar .replace() si quieres sobrescribir archivos con el mismo nombre
            # o .rename() si quieres que falle si el archivo ya existe
            pdf_file.rename(new_path)
            print(f"   ✅ Renombrado a: {new_name} y movido a Input/")

        except ValueError as ve:
            print(f"   ❌ Error de metadatos: {ve}")
            dest = error_folder / pdf_file.name
            pdf_file.rename(dest)
        except FileExistsError:
            print(f"   ⚠️ Ya existe un archivo con el nombre: {new_name}")
            dest = error_folder / pdf_file.name
            pdf_file.rename(dest)
        except OSError as oe:
            print(f"   ❌ Error al renombrar '{pdf_file.name}': {oe}")
            dest = error_folder / pdf_file.name
            pdf_file.rename(dest)
        except Exception as e:
            print(f"   ❌ Error inesperado: {e}")
            dest = error_folder / pdf_file.name
            pdf_file.rename(dest)





if __name__ == "__main__":
    # Cambiar a tu carpeta real
    folder_to_process = r"H:\Mi unidad\IMMF\3 - Bibliografía\Unsorted"
    rename_pdfs_in_folder(folder_to_process)
    #metadata1 = get_metadata_from_doi("10.1161/CIRCRESAHA.116.310091")
    #print(metadata1)
