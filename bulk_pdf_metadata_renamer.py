
import requests
import re
import os
from pathlib import Path
import fitz # PyMuPDF
# Import note functions from import_requests.py, use alias to avoid name conflict
from import_requests import get_metadata_from_doi as note_get_metadata_from_doi, format_metadata_as_markdown, save_note_as_markdown


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
    """
    Intenta encontrar un DOI en el texto del PDF de manera más robusta.

    Mejoras:
    1. Preprocesamiento de texto más agresivo para manejar saltos de línea y guiones.
    2. Expresión regular más flexible que maneja una gama más amplia de caracteres
       pero es menos propensa a capturar puntuación final no deseada.
    """
    # Expresión regular más estricta para el DOI.
    # No permite espacios dentro del DOI capturado.
    doi_pattern = re.compile(
        r"(?:doi\s*[:]?\s*|https?://(?:www\.)?doi\.org/|/doi/)?(10\.\d{4,9}/[-._;():/A-Z0-9]+)",
        re.IGNORECASE
    )
    
    try:
        with fitz.open(file_path) as pdf:
            # Leer todo el texto del PDF
            text = "".join(page.get_text() for page in pdf)
            
            # --- Mejoras en el preprocesamiento ---
            
            # 1. Eliminar guiones al final de las líneas para unir palabras partidas.
            text = re.sub(r'-\s*\n', '', text)
            
            # 2. Reemplazar todos los tipos de saltos de línea con un solo espacio.
            # Esto maneja los casos más complejos de DOI partidos en varias líneas.
            text = text.replace('\n', ' ').replace('\r', ' ')
            
            # 3. Eliminar espacios múltiples que puedan haber aparecido
            # después de la sustitución de saltos de línea.
            text = re.sub(r'\s+', ' ', text)
            
            match = doi_pattern.search(text)
            
            if match:
                # El DOI está en el primer grupo de captura
                doi = match.group(1).strip()
                
                # Limpiamos puntuación no deseada al final del DOI
                # Por ejemplo, si el DOI termina con un punto o una coma.
                doi = re.sub(r"[\.,;:]+$", "", doi)
                
                return doi
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


    processed = 0
    success = 0
    failed = 0
    for pdf_file in folder.glob("*.pdf"):
        processed += 1
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
            failed += 1
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

            # Después de procesar el PDF, crear la nota usando la función externa
            try:
                note_metadata = note_get_metadata_from_doi(doi)
                md_content = format_metadata_as_markdown(note_metadata)
                output_dir = r"G:\Mi unidad\Input_network\Input_network"  # Hardcoded path
                save_note_as_markdown(md_content, note_metadata, output_dir)
            except Exception as note_e:
                print(f"   ⚠️ Error al crear la nota Markdown: {note_e}")

            success += 1

        except ValueError as ve:
            print(f"   ❌ Error de metadatos: {ve}")
            if pdf_file.exists():
                dest = error_folder / pdf_file.name
                pdf_file.rename(dest)
            failed += 1
        except FileExistsError:
            print(f"   ⚠️ Ya existe un archivo con el nombre: {new_name}")
            if pdf_file.exists():
                dest = error_folder / pdf_file.name
                pdf_file.rename(dest)
            failed += 1
        except OSError as oe:
            print(f"   ❌ Error al renombrar '{pdf_file.name}': {oe}")
            if pdf_file.exists():
                dest = error_folder / pdf_file.name
                pdf_file.rename(dest)
            failed += 1
        except Exception as e:
            print(f"   ❌ Error inesperado: {e}")
            if pdf_file.exists():
                dest = error_folder / pdf_file.name
                pdf_file.rename(dest)
            failed += 1

    # Logger: append summary to log file
    log_path = folder / "process_log.txt"
    from datetime import datetime
    with open(log_path, "a", encoding="utf-8") as logf:
        logf.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Processed: {processed}, Success: {success}, Failed: {failed}\n")





if __name__ == "__main__":
    # Cambiar a tu carpeta real
    folder_to_process = r"H:\Mi unidad\IMMF\3 - Bibliografía\Unsorted"
    rename_pdfs_in_folder(folder_to_process)
    #metadata1 = get_metadata_from_doi("10.1161/CIRCRESAHA.116.310091")
    #print(metadata1)
