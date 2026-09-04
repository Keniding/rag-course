"""
Etapa 2 · Chunking para organizar y dividir el contenido.

Lee `data/processed/01_documentos.json` (salida de la etapa de ingesta) y
divide cada documento en fragmentos ("chunks") pequeños y semánticamente
coherentes, listos para ser vectorizados en la etapa 3.

Estrategia usada: "chunking estructural + límite de tokens"
  1. Se divide primero por encabezados Markdown (## Sección) para respetar
     los límites semánticos que el autor del documento ya definió.
  2. Si una sección resultante es demasiado larga, se subdivide por tokens
     con solapamiento (overlap), para no cortar ideas a la mitad y para que
     el modelo de embeddings reciba fragmentos de tamaño consistente.
"""

import json
import re
from pathlib import Path

import tiktoken

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_PATH = BASE_DIR / "data" / "processed" / "01_documentos.json"
OUTPUT_PATH = BASE_DIR / "data" / "processed" / "02_chunks.json"

# Tamaño objetivo de cada chunk y solapamiento, en tokens.
# 220 tokens ~ un párrafo largo o una subsección corta.
MAX_TOKENS = 220
OVERLAP_TOKENS = 40

ENCODER = tiktoken.get_encoding("cl100k_base")


def dividir_por_encabezados(texto: str) -> list[str]:
    """Divide un texto Markdown en secciones usando '## ' como separador."""
    partes = re.split(r"\n(?=## )", texto)
    return [p.strip() for p in partes if p.strip()]


def dividir_por_tokens(texto: str, max_tokens: int, overlap: int) -> list[str]:
    """Divide un texto largo en fragmentos de `max_tokens` con solapamiento."""
    tokens = ENCODER.encode(texto)
    if len(tokens) <= max_tokens:
        return [texto]

    fragmentos = []
    inicio = 0
    while inicio < len(tokens):
        fin = min(inicio + max_tokens, len(tokens))
        fragmento_tokens = tokens[inicio:fin]
        fragmentos.append(ENCODER.decode(fragmento_tokens))
        if fin == len(tokens):
            break
        inicio = fin - overlap  # retrocedemos `overlap` tokens

    return fragmentos


def construir_chunks(documento: dict) -> list[dict]:
    secciones = dividir_por_encabezados(documento["texto"])
    chunks = []
    contador = 0

    for seccion in secciones:
        sub_fragmentos = dividir_por_tokens(seccion, MAX_TOKENS, OVERLAP_TOKENS)
        for fragmento in sub_fragmentos:
            chunks.append(
                {
                    "chunk_id": f"{documento['doc_id']}__{contador:03d}",
                    "doc_id": documento["doc_id"],
                    "fuente": documento["fuente"],
                    "n_tokens": len(ENCODER.encode(fragmento)),
                    "texto": fragmento,
                }
            )
            contador += 1

    return chunks


def main():
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"No existe {INPUT_PATH}. Ejecuta primero 01_ingesta_documentos/ingesta.py"
        )

    documentos = json.loads(INPUT_PATH.read_text(encoding="utf-8"))

    todos_los_chunks = []
    for documento in documentos:
        todos_los_chunks.extend(construir_chunks(documento))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(todos_los_chunks, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"[OK] {len(documentos)} documento(s) -> {len(todos_los_chunks)} chunk(s)")
    tokens_por_chunk = [c["n_tokens"] for c in todos_los_chunks]
    print(
        f"  tokens por chunk -> min={min(tokens_por_chunk)}, "
        f"max={max(tokens_por_chunk)}, "
        f"promedio={sum(tokens_por_chunk) / len(tokens_por_chunk):.1f}"
    )
    print(f"\nGuardado en: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
