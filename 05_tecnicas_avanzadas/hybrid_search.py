"""
Etapa 5 (extra) · Búsqueda híbrida: semántica (vectorial) + léxica (BM25).

La búsqueda vectorial es excelente para capturar significado, pero le cuesta
con términos exactos poco frecuentes (códigos, nombres propios, siglas). La
búsqueda léxica BM25 es fuerte justo ahí. Este script ejecuta ambas sobre la
misma pregunta y combina los rankings con Reciprocal Rank Fusion (RRF), sin
necesitar normalizar puntajes de escalas distintas (coseno vs. BM25).
"""

import json
import re
import sys
from pathlib import Path

import chromadb
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parent.parent
CHUNKS_PATH = BASE_DIR / "data" / "processed" / "02_chunks.json"
CHROMA_PATH = BASE_DIR / "data" / "chroma_db"

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
COLLECTION_NAME = "technova_knowledge_base"

TOP_K_CADA_METODO = 10  # candidatos que aporta cada método antes de fusionar
RRF_K = 60  # constante estándar de Reciprocal Rank Fusion


def tokenizar(texto: str) -> list[str]:
    """Tokenizador simple: minúsculas + solo palabras (suficiente para BM25 aquí)."""
    return re.findall(r"\w+", texto.lower())


def cargar_chunks() -> list[dict]:
    if not CHUNKS_PATH.exists():
        raise FileNotFoundError(
            f"No existe {CHUNKS_PATH}. Ejecuta primero 02_chunking_contenido/chunking.py"
        )
    return json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))


def busqueda_bm25(pregunta: str, chunks: list[dict], k: int) -> list[str]:
    """Devuelve una lista de chunk_id ordenada por relevancia BM25 (léxica)."""
    corpus_tokenizado = [tokenizar(c["texto"]) for c in chunks]
    bm25 = BM25Okapi(corpus_tokenizado)

    puntajes = bm25.get_scores(tokenizar(pregunta))
    orden = sorted(range(len(chunks)), key=lambda i: puntajes[i], reverse=True)
    return [chunks[i]["chunk_id"] for i in orden[:k]]


def busqueda_vectorial(pregunta: str, k: int) -> list[str]:
    """Devuelve una lista de chunk_id ordenada por similitud vectorial (semántica)."""
    modelo = SentenceTransformer(MODEL_NAME)
    embedding_pregunta = modelo.encode([pregunta], normalize_embeddings=True).tolist()

    cliente = chromadb.PersistentClient(path=str(CHROMA_PATH))
    coleccion = cliente.get_collection(COLLECTION_NAME)

    resultados = coleccion.query(query_embeddings=embedding_pregunta, n_results=k)
    return resultados["ids"][0]


def reciprocal_rank_fusion(rankings: list[list[str]], k: int = RRF_K) -> list[tuple[str, float]]:
    """
    Combina varias listas rankeadas de ids en un único ranking fusionado.
    score(id) = suma, sobre cada ranking donde aparece, de 1 / (k + posicion)
    """
    puntajes: dict[str, float] = {}
    for ranking in rankings:
        for posicion, doc_id in enumerate(ranking):
            puntajes[doc_id] = puntajes.get(doc_id, 0.0) + 1.0 / (k + posicion + 1)

    return sorted(puntajes.items(), key=lambda par: par[1], reverse=True)


def main():
    if len(sys.argv) < 2:
        print('Uso: python hybrid_search.py "<tu pregunta>"')
        sys.exit(1)

    pregunta = sys.argv[1]
    chunks = cargar_chunks()
    chunks_por_id = {c["chunk_id"]: c for c in chunks}

    ranking_bm25 = busqueda_bm25(pregunta, chunks, TOP_K_CADA_METODO)
    ranking_vectorial = busqueda_vectorial(pregunta, TOP_K_CADA_METODO)

    print(f"Pregunta: {pregunta}\n")
    print(f"Top-{TOP_K_CADA_METODO} BM25 (lexico):        {ranking_bm25}")
    print(f"Top-{TOP_K_CADA_METODO} vectorial (semantico): {ranking_vectorial}\n")

    fusionado = reciprocal_rank_fusion([ranking_bm25, ranking_vectorial])

    print("Ranking fusionado (Reciprocal Rank Fusion):")
    for chunk_id, score in fusionado[:5]:
        fuente = chunks_por_id[chunk_id]["fuente"]
        texto = chunks_por_id[chunk_id]["texto"][:100].replace("\n", " ")
        print(f"  [{score:.4f}] {chunk_id} ({fuente}) -> {texto}...")


if __name__ == "__main__":
    main()
