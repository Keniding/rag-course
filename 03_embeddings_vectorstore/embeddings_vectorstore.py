"""
Etapa 3 · Embeddings y almacenamiento en bases vectoriales.

Lee `data/processed/02_chunks.json` (salida de la etapa de chunking),
genera un embedding (vector numérico) por cada chunk usando un modelo
local de `sentence-transformers`, y los guarda en una base de datos
vectorial persistente (ChromaDB) en `data/chroma_db/`.
"""

import json
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_PATH = BASE_DIR / "data" / "processed" / "02_chunks.json"
CHROMA_PATH = BASE_DIR / "data" / "chroma_db"

# Modelo local, liviano (~90 MB) y multilingüe suficiente para español.
# Se descarga una sola vez desde HuggingFace y luego queda en caché local.
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
COLLECTION_NAME = "technova_knowledge_base"


def cargar_chunks() -> list[dict]:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"No existe {INPUT_PATH}. Ejecuta primero 02_chunking_contenido/chunking.py"
        )
    return json.loads(INPUT_PATH.read_text(encoding="utf-8"))


def main():
    chunks = cargar_chunks()
    textos = [c["texto"] for c in chunks]

    print(f"Cargando modelo de embeddings: {MODEL_NAME}")
    modelo = SentenceTransformer(MODEL_NAME)

    print(f"Generando embeddings para {len(textos)} chunk(s)...")
    embeddings = modelo.encode(textos, show_progress_bar=False, normalize_embeddings=True)
    print(f"Dimension de cada embedding: {embeddings.shape[1]}")

    print(f"Guardando en ChromaDB (persistente) en: {CHROMA_PATH}")
    cliente = chromadb.PersistentClient(path=str(CHROMA_PATH))

    # Si ya existía una colección de una corrida anterior, la recreamos
    # para que este script sea idempotente (se pueda ejecutar varias veces).
    if COLLECTION_NAME in [c.name for c in cliente.list_collections()]:
        cliente.delete_collection(COLLECTION_NAME)
    coleccion = cliente.create_collection(
        name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )

    coleccion.add(
        ids=[c["chunk_id"] for c in chunks],
        embeddings=embeddings.tolist(),
        documents=textos,
        metadatas=[{"doc_id": c["doc_id"], "fuente": c["fuente"]} for c in chunks],
    )

    print(f"[OK] {coleccion.count()} chunk(s) indexados en la coleccion '{COLLECTION_NAME}'")


if __name__ == "__main__":
    main()
