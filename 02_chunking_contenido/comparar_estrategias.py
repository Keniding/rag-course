"""
Extra · Comparación de estrategias de chunking (Lección 2, sección 3).

Corre tres estrategias sobre el MISMO documento (`manual_producto.md`, que
tiene títulos, listas, prosa y una tabla) para ver en números y en texto real
la diferencia entre "cortar a ciegas" y "cortar respetando estructura":

1. Fixed-size: corta cada `CHUNK_SIZE_CHARS` caracteres, sin mirar el
   contenido en absoluto. Es la estrategia más simple y la más citada en la
   Lección 2 como punto de partida "rara vez usado en producción".
2. Recursive: reimplementación simplificada de `RecursiveCharacterTextSplitter`
   (LangChain) — prueba separadores de mayor a menor jerarquía
   (`\n\n`, `\n`, ". ", " ") para no cortar a mitad de palabra u oración.
3. Structure-aware + límite de tokens: la estrategia que ya usa este taller
   en `chunking.py` (corta por encabezados Markdown, luego por tokens).

No agrega LangChain como dependencia nueva: las estrategias 1 y 2 son
reimplementaciones livianas con el mismo comportamiento conceptual, para no
introducir un framework grande solo para esta comparación.
"""

import json
from pathlib import Path

from chunking import MAX_TOKENS, OVERLAP_TOKENS, dividir_por_encabezados, dividir_por_tokens

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_PATH = BASE_DIR / "data" / "processed" / "01_documentos.json"
DOC_ID_A_COMPARAR = "manual_producto"

CHUNK_SIZE_CHARS = 250
OVERLAP_CHARS = 30
SEPARADORES = ["\n\n", "\n", ". ", " ", ""]


def fixed_size_chunking(texto: str, chunk_size: int, overlap: int) -> list[str]:
    """Corta el texto en bloques de tamaño fijo, sin mirar el contenido."""
    chunks = []
    inicio = 0
    while inicio < len(texto):
        fin = min(inicio + chunk_size, len(texto))
        chunks.append(texto[inicio:fin])
        if fin == len(texto):
            break
        inicio = fin - overlap
    return chunks


def recursive_chunking(texto: str, chunk_size: int, separadores: list[str]) -> list[str]:
    """
    Reimplementación simplificada de un recursive character splitter:
    intenta el separador más "grande" primero (parrafos), y si un fragmento
    resultante sigue siendo muy largo, retrocede a un separador más fino.
    """
    if len(texto) <= chunk_size:
        return [texto]

    separador, resto_separadores = separadores[0], separadores[1:]

    if separador == "":
        # último recurso: cortar por caracteres, sin más separadores que probar
        return fixed_size_chunking(texto, chunk_size, overlap=0)

    partes = texto.split(separador)
    chunks: list[str] = []
    actual = ""

    for parte in partes:
        candidato = f"{actual}{separador}{parte}" if actual else parte

        if len(candidato) <= chunk_size:
            actual = candidato
            continue

        if actual:
            chunks.append(actual)

        if len(parte) > chunk_size:
            chunks.extend(recursive_chunking(parte, chunk_size, resto_separadores))
            actual = ""
        else:
            actual = parte

    if actual:
        chunks.append(actual)

    return chunks


def structure_aware_chunking(texto: str) -> list[str]:
    """La estrategia que ya usa este taller: encabezados + límite de tokens."""
    chunks = []
    for seccion in dividir_por_encabezados(texto):
        chunks.extend(dividir_por_tokens(seccion, MAX_TOKENS, OVERLAP_TOKENS))
    return chunks


def tabla_queda_completa_en_un_chunk(chunks: list[str]) -> bool:
    """Heurística: ¿las 3 filas de la tabla de planes caen en el MISMO chunk?"""
    filas_clave = ["Starter", "Business", "Enterprise"]
    for chunk in chunks:
        if all(fila in chunk for fila in filas_clave):
            return True
    return False


def main():
    documentos = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    documento = next(d for d in documentos if d["doc_id"] == DOC_ID_A_COMPARAR)
    texto = documento["texto"]

    print(f"Comparando estrategias sobre: {documento['fuente']} ({len(texto)} caracteres)\n")

    estrategias = {
        f"1. Fixed-size ({CHUNK_SIZE_CHARS} caracteres, overlap {OVERLAP_CHARS})": fixed_size_chunking(
            texto, CHUNK_SIZE_CHARS, OVERLAP_CHARS
        ),
        f"2. Recursive ({CHUNK_SIZE_CHARS} caracteres, jerarquia de separadores)": recursive_chunking(
            texto, CHUNK_SIZE_CHARS, SEPARADORES
        ),
        f"3. Structure-aware ({MAX_TOKENS} tokens, overlap {OVERLAP_TOKENS})": structure_aware_chunking(texto),
    }

    print(f"{'Estrategia':<65} {'#chunks':>8} {'tabla intacta':>14}")
    print("-" * 90)
    for nombre, chunks in estrategias.items():
        tabla_ok = "SI" if tabla_queda_completa_en_un_chunk(chunks) else "NO (se corto)"
        print(f"{nombre:<65} {len(chunks):>8} {tabla_ok:>14}")

    print("\n--- Ejemplo: el chunk que contiene 'Enterprise' con cada estrategia ---\n")
    for nombre, chunks in estrategias.items():
        chunk_con_enterprise = next((c for c in chunks if "Enterprise" in c), None)
        print(f"[{nombre}]")
        if chunk_con_enterprise:
            preview = chunk_con_enterprise.replace("\n", " ")[:200]
            print(f"  {preview}...\n")
        else:
            print("  (no encontrado)\n")


if __name__ == "__main__":
    main()
