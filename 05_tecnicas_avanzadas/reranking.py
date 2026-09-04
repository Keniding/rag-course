"""
Etapa 5 (extra) · Re-ranking con cross-encoder.

El retrieval inicial (BM25 y/o vectorial) usa un "bi-encoder": la pregunta y
cada chunk se vectorizan por separado y se comparan después. Es rápido, pero
no captura interacciones finas entre pregunta y texto. Un "cross-encoder"
recibe pregunta + chunk juntos en una sola pasada y produce un puntaje de
relevancia mucho más preciso para ese par específico — a costa de ser lento,
por lo que solo se aplica sobre un conjunto ya reducido de candidatos.
"""

import json
import sys
from pathlib import Path

import chromadb
from sentence_transformers import CrossEncoder, SentenceTransformer

BASE_DIR = Path(__file__).resolve().parent.parent
CHUNKS_PATH = BASE_DIR / "data" / "processed" / "02_chunks.json"
CHROMA_PATH = BASE_DIR / "data" / "chroma_db"

EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
# Cross-encoder multilingüe (incluye español), entrenado sobre MS MARCO.
CROSS_ENCODER_MODEL = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
COLLECTION_NAME = "technova_knowledge_base"

TOP_K_RETRIEVAL = 8  # candidatos iniciales, amplios, antes de re-rankear
TOP_N_FINAL = 3  # cuántos quedan después del re-ranking


def cargar_chunks_por_id() -> dict:
    chunks = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))
    return {c["chunk_id"]: c for c in chunks}


def recuperar_candidatos(pregunta: str, k: int) -> list[dict]:
    modelo = SentenceTransformer(EMBEDDING_MODEL)
    embedding_pregunta = modelo.encode([pregunta], normalize_embeddings=True).tolist()

    cliente = chromadb.PersistentClient(path=str(CHROMA_PATH))
    coleccion = cliente.get_collection(COLLECTION_NAME)
    resultados = coleccion.query(query_embeddings=embedding_pregunta, n_results=k)

    return [
        {"chunk_id": id_, "texto": texto, "fuente": meta["fuente"]}
        for id_, texto, meta in zip(
            resultados["ids"][0], resultados["documents"][0], resultados["metadatas"][0]
        )
    ]


def rerankear(pregunta: str, candidatos: list[dict], top_n: int) -> list[dict]:
    cross_encoder = CrossEncoder(CROSS_ENCODER_MODEL)
    pares = [(pregunta, c["texto"]) for c in candidatos]
    puntajes = cross_encoder.predict(pares)

    for candidato, puntaje in zip(candidatos, puntajes):
        candidato["score_cross_encoder"] = float(puntaje)

    return sorted(candidatos, key=lambda c: c["score_cross_encoder"], reverse=True)[:top_n]


def main():
    if len(sys.argv) < 2:
        print('Uso: python reranking.py "<tu pregunta>"')
        sys.exit(1)

    pregunta = sys.argv[1]
    print(f"Pregunta: {pregunta}\n")

    candidatos = recuperar_candidatos(pregunta, TOP_K_RETRIEVAL)
    print(f"Candidatos iniciales (bi-encoder, top-{TOP_K_RETRIEVAL}):")
    for c in candidatos:
        print(f"  - {c['chunk_id']} ({c['fuente']})")

    finales = rerankear(pregunta, candidatos, TOP_N_FINAL)
    print(f"\nDespues de re-ranking con cross-encoder (top-{TOP_N_FINAL}):")
    for c in finales:
        texto_corto = c["texto"][:100].replace("\n", " ")
        print(f"  [{c['score_cross_encoder']:.4f}] {c['chunk_id']} ({c['fuente']}) -> {texto_corto}...")


if __name__ == "__main__":
    main()
