
import os
import re
import csv
from pathlib import Path
from collections import Counter

# --- CONFIGURACIÓN ---
VAULT_PATH = r'G:\Mi unidad\Input_network\Input_network' 
TARGET_HEADER = 'Abstract'
OUTPUT_FILE = 'conceptos_para_revisar.csv' # Archivo que se generará para abrir en Excel
TOP_LIMIT = 100 # Cantidad de términos a exportar

# 1. EXTERMINIO DE PLACEHOLDERS
STRINGS_TO_IGNORE = ["no abstract available", "abstract available", "no abstract"]

# 2. STOP WORDS RECARGADO (Limpieza profunda de ruido académico)
STOP_WORDS = {
    'of', 'in', 'to', 'for', 'with', 'on', 'at', 'by', 'from', 'is', 'are', 'was', 'were', 
    'the', 'a', 'an', 'and', 'or', 'as', 'be', 'been', 'being', 'it', 'its', 'this', 'that',
    'which', 'who', 'these', 'those', 'we', 'our', 'their', 'they', 'into', 'has', 'have', 
    'not', 'but', 'than', 'more', 'also', 'such', 'very', 'can', 'may', 'however', 'during',
    'specific', 'factor', 'identified', 'using', 'well', 'both', 'between', 'through',
    'here', 'there', 'results', 'associated', 'increased', 'decreased', 'showed', 'highly',
    'potential', 'level', 'levels', 'significant', 'role', 'roles', 'expression', 'cells',
    'muscle', 'genes', 'protein', 'response', 'human', 'show', 'shows', 'shown', 'including',
    'study', 'used', 'data', 'analysis', 'clinical', 'molecular'
}

# 3. RUIDO ACADÉMICO (Frases que no queremos como links)
ACADEMIC_NOISE = {
    'role in', 'roles in', 'response to', 'in response', 'understanding of', 
    'we found', 'development of', 'involved in', 'loss of', 'associated with',
    'it is', 'there is', 'due to', 'well as', 'as well as', 'here we', 'shown to',
    'plays a', 'play a', 'the expression', 'expression of', 'levels of'
}

def clean_text(text):
    """Limpia el texto y descarta bloques vacíos o placeholders."""
    if not text or any(placeholder in text.lower() for placeholder in STRINGS_TO_IGNORE):
        return []
    
    # Normalizamos separadores biológicos
    text = re.sub(r'[/\\-]', ' ', text)
    text = re.sub(r'[^a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s]', '', text)
    return text.lower().split()

def is_valid_gram(gram_list):
    """Verifica si un n-grama es un concepto válido."""
    gram_str = " ".join(gram_list)
    
    # Regla 1: No empezar ni terminar con una stop word
    if gram_list[0] in STOP_WORDS or gram_list[-1] in STOP_WORDS:
        return False
    
    # Regla 2: No ser una frase de relleno académico
    if gram_str in ACADEMIC_NOISE:
        return False
    
    # Regla 3: Evitar palabras demasiado cortas o que estén en stop words
    if len(gram_str) < 3 or gram_str in STOP_WORDS:
        return False
        
    return True

def analyze_vault(vault_path, header):
    """Procesa el vault y extrae frecuencias de conceptos (1 a 3 palabras)."""
    all_words = []
    path_obj = Path(vault_path)
    
    if not path_obj.exists():
        print(f"❌ Error: La ruta {vault_path} no existe.")
        return Counter()

    for path in path_obj.rglob('*.md'):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                pattern = rf'^#\s+.*?{re.escape(header)}.*?\n(.*?)(?=\n# |\Z)'
                match = re.search(pattern, content, re.DOTALL | re.MULTILINE | re.IGNORECASE)
                
                if match:
                    cleaned = clean_text(match.group(1))
                    if cleaned:
                        all_words.extend(cleaned)
        except Exception:
            continue

    results = Counter()
    for n in [1, 2, 3]:
        grams = [all_words[i:i+n] for i in range(len(all_words)-n+1)]
        valid_grams = [" ".join(g) for g in grams if is_valid_gram(g)]
        results.update(valid_grams)
    
    return results

if __name__ == "__main__":
    print(f"🧹 Analizando conceptos en la sección '{TARGET_HEADER}'...")
    freqs = analyze_vault(VAULT_PATH, TARGET_HEADER)

    if not freqs:
        print("💀 No se encontraron conceptos relevantes.")
    else:
        print(f"\n--- 💎 PROCESANDO TOP {TOP_LIMIT} CONCEPTOS ---")
        seen = set()
        # PRIORIDAD: Primero los más largos, luego los más frecuentes
        sorted_concepts = sorted(freqs.items(), key=lambda x: (len(x[0]), x[1]), reverse=True)

        concepts_to_export = []
        for concept, count in sorted_concepts:
            # Deduplicación inteligente
            is_redundant = False
            for s in seen:
                if concept in s and freqs[concept] < freqs[s] * 1.5:
                    is_redundant = True
                    break
            
            if not is_redundant and count > 3: # Bajamos un poco el umbral para el Excel
                seen.add(concept)
                concepts_to_export.append((concept.upper(), count))

        # Re-ordenamos por frecuencia para el reporte final
        concepts_to_export.sort(key=lambda x: x[1], reverse=True)
        final_list = concepts_to_export[:TOP_LIMIT]
                # Exportación a CSV
        try:
            with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Concepto', 'Menciones'])
                writer.writerows(final_list)
            print(f"✅ ¡Éxito! Se ha generado '{OUTPUT_FILE}' con {len(final_list)} términos.")
            print(f"📂 Abre este archivo en Excel para seleccionar tus keywords fácilmente.")
        except Exception as e:
            print(f"❌ Error al guardar el CSV: {e}")

        # Vista previa rápida en consola
        print(f"\n--- 📝 VISTA PREVIA (TOP 15) ---")
        for concept, count in final_list[:15]:
            print(f"[{count:3}] {concept}")

    print("\n💡 Sugerencia: Una vez elijas los términos en el Excel, pásamelos para configurar el Auto-Linker.")