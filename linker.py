import re
from pathlib import Path

# --- CONFIGURACIÓN DEL USUARIO ---
VAULT_PATH = r'G:\Mi unidad\Input_network\Input_network' 
# Lista de palabras clave que quieres convertir en [[links]]
# El script usará EXACTAMENTE como escribas aquí la palabra para el nombre de la nota.
# Te recomiendo usar "Title Case" o como quieras que se llamen tus archivos.
KEYWORDS_TO_LINK = [
    'Smooth Muscle Cells',
    'SMC',
    'METTL3',
    'YTHDF2',
    'YTHDF',
    'Autophagy',
    'm6A',
    'Notch'
]

def apply_links_to_content(content, keywords):
    """
    Aplica los enlaces [[ ]] al contenido evitando YAML, bloques de código
    y palabras que ya estén enlazadas, normalizando el destino del link.
    """
    # 1. Protegemos el YAML Frontmatter (entre --- y ---)
    parts = re.split(r'(^---\n.*?\n---)', content, maxsplit=1, flags=re.DOTALL | re.MULTILINE)
    
    # 2. Ordenamos keywords por longitud (de mayor a menor)
    sorted_keywords = sorted(keywords, key=len, reverse=True)
    
    def process_body(text):
        for word in sorted_keywords:
            if not word.strip(): continue
            
            # Regex que busca la palabra de forma insensible a mayúsculas
            pattern = rf'(?<!\[\[)(?<!\[)\b({re.escape(word)})\b(?!\]\])(?!\]\()'
            
            def replacement_callback(match):
                matched_text = match.group(1)
                # Si la palabra en el texto es idéntica a la keyword (mismo casing), link simple
                if matched_text == word:
                    return f"[[{word}]]"
                # Si el casing es distinto, usamos un alias: [[Keyword|TextoOriginal]]
                # Esto unifica todos los links bajo el mismo nombre de nota
                return f"[[{word}|{matched_text}]]"
            
            text = re.compile(pattern, re.IGNORECASE).sub(replacement_callback, text)
        return text

    # Reconstrucción del archivo
    if len(parts) > 1:
        return parts[0] + parts[1] + process_body(parts[2])
    return process_body(content)

def run_linker():
    print(f"🚀 Iniciando Auto-Linker Unificado en: {VAULT_PATH}")
    print(f"📦 Keywords cargadas: {len(KEYWORDS_TO_LINK)}")
    
    files_processed = 0
    
    path_obj = Path(VAULT_PATH)
    if not path_obj.exists():
        print("❌ Error: La ruta del vault no existe.")
        return

    for path in path_obj.rglob('*.md'):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            new_content = apply_links_to_content(original_content, KEYWORDS_TO_LINK)
            
            if new_content != original_content:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                files_processed += 1
                print(f"🔗 Enlazado y unificado: {path.name}")
        except Exception as e:
            print(f"⚠️ Error procesando {path.name}: {e}")

    print(f"\n✅ ¡Proceso terminado!")
    print(f"📂 Archivos modificados: {files_processed}")
    print(f"💡 Tip: Ahora todos los links apuntan a la versión definida en tu lista.")

if __name__ == "__main__":
    confirm = input("⚠️ ¿Has hecho backup de tu vault? (s/n): ")
    if confirm.lower() == 's':
        run_linker()
    else:
        print("❌ Operación cancelada.")