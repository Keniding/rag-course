"""
Etapa 6 (extra) · Visualización de embeddings, en 2D o 3D.

Los embeddings viven en un espacio de 384 dimensiones (el tamaño del vector
del modelo usado en la etapa 3) — imposible de "mirar" directamente. Este
script los proyecta a 2 o 3 dimensiones con UMAP para poder graficarlos, y
genera un HTML interactivo (Plotly) donde cada punto es un chunk, coloreado
por documento de origen.

No hace falta ninguna librería nueva para el modo 3D: `umap-learn` acepta
`n_components=3` de forma nativa, y Plotly tiene `Scatter3d` nativo — las
mismas dos librerías que ya usa el modo 2D.

Si se pasa una pregunta como argumento, también se vectoriza, se agrega al
gráfico como un punto distinto, y se dibujan líneas hacia sus chunks más
cercanos — la MISMA búsqueda por similitud de la etapa 4, pero ahora visible.

Importante (ver README): las distancias en el gráfico (2D o 3D) son
aproximadas. UMAP prioriza preservar vecindarios locales, no distancias
globales exactas; el ranking real de similitud (el que usa el sistema para
responder) siempre se calcula en las 384 dimensiones originales, nunca en
la proyección.
"""

import argparse
from pathlib import Path

import chromadb
import numpy as np
import plotly.graph_objects as go
import umap
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parent.parent
CHROMA_PATH = BASE_DIR / "data" / "chroma_db"
OUTPUT_DIR = BASE_DIR / "data" / "visualizations"

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
COLLECTION_NAME = "technova_knowledge_base"
TOP_K_VECINOS = 3

# Paleta simple y estable por documento fuente.
COLORES = ["#2563eb", "#16a34a", "#dc2626", "#9333ea", "#ea580c", "#0891b2"]


def cargar_embeddings_indexados() -> dict:
    if not CHROMA_PATH.exists():
        raise FileNotFoundError(
            f"No existe {CHROMA_PATH}. Ejecuta primero "
            f"03_embeddings_vectorstore/embeddings_vectorstore.py"
        )
    cliente = chromadb.PersistentClient(path=str(CHROMA_PATH))
    coleccion = cliente.get_collection(COLLECTION_NAME)
    return coleccion.get(include=["embeddings", "documents", "metadatas"])


def similitud_coseno(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """a: vector (dim,); b: matriz (n, dim). Ambos ya vienen normalizados."""
    return b @ a


def construir_figura(
    dim: int,
    coords: np.ndarray,
    fuentes: list[str],
    textos: list[str],
    ids: list[str],
    coords_pregunta: np.ndarray | None,
    vecinos_idx: list[int],
) -> go.Figure:
    es_3d = dim == 3
    Scatter = go.Scatter3d if es_3d else go.Scatter

    def coords_de(indices):
        ejes = dict(x=coords[indices, 0], y=coords[indices, 1])
        if es_3d:
            ejes["z"] = coords[indices, 2]
        return ejes

    def punto_de(vector):
        ejes = dict(x=[vector[0]], y=[vector[1]])
        if es_3d:
            ejes["z"] = [vector[2]]
        return ejes

    def linea_entre(a, b):
        ejes = dict(x=[a[0], b[0]], y=[a[1], b[1]])
        if es_3d:
            ejes["z"] = [a[2], b[2]]
        return ejes

    fig = go.Figure()

    fuentes_unicas = sorted(set(fuentes))
    color_por_fuente = {f: COLORES[i % len(COLORES)] for i, f in enumerate(fuentes_unicas)}

    for fuente in fuentes_unicas:
        indices = [i for i, f in enumerate(fuentes) if f == fuente]
        fig.add_trace(
            Scatter(
                **coords_de(indices),
                mode="markers",
                name=fuente,
                marker=dict(size=8 if es_3d else 14, color=color_por_fuente[fuente], line=dict(width=1, color="white")),
                text=[f"<b>{ids[i]}</b><br>{textos[i][:150]}..." for i in indices],
                hoverinfo="text",
            )
        )

    if coords_pregunta is not None:
        # Líneas hacia los chunks más cercanos (similitud real en 384D, no en la proyección).
        for idx in vecinos_idx:
            fig.add_trace(
                Scatter(
                    **linea_entre(coords_pregunta, coords[idx]),
                    mode="lines",
                    line=dict(color="rgba(120,120,120,0.5)", width=2, dash="dot"),
                    showlegend=False,
                    hoverinfo="skip",
                )
            )
        fig.add_trace(
            Scatter(
                **punto_de(coords_pregunta),
                mode="markers",
                name="Pregunta del usuario",
                marker=dict(size=12 if es_3d else 20, color="black", symbol="diamond" if es_3d else "star"),
                text=["Pregunta"],
                hoverinfo="text",
            )
        )

    layout_ejes = dict(
        xaxis_title="Dimension UMAP 1",
        yaxis_title="Dimension UMAP 2",
    )
    if es_3d:
        fig.update_layout(
            title=f"Embeddings de TechNova S.A. proyectados a 3D (UMAP)",
            scene=dict(
                xaxis_title="Dimension UMAP 1",
                yaxis_title="Dimension UMAP 2",
                zaxis_title="Dimension UMAP 3",
            ),
            template="plotly_white",
            width=900,
            height=700,
        )
    else:
        fig.update_layout(
            title="Embeddings de TechNova S.A. proyectados a 2D (UMAP)",
            template="plotly_white",
            width=900,
            height=650,
            **layout_ejes,
        )
    return fig


def parsear_argumentos():
    parser = argparse.ArgumentParser(description="Visualiza los embeddings del taller en 2D o 3D.")
    parser.add_argument("pregunta", nargs="?", default=None, help="Pregunta opcional a resaltar en el grafico")
    parser.add_argument("--dim", type=int, choices=[2, 3], default=2, help="Dimensiones de la proyeccion (default: 2)")
    return parser.parse_args()


def main():
    args = parsear_argumentos()
    pregunta, dim = args.pregunta, args.dim

    datos = cargar_embeddings_indexados()
    embeddings = np.array(datos["embeddings"])
    textos = datos["documents"]
    ids = datos["ids"]
    fuentes = [meta["fuente"] for meta in datos["metadatas"]]

    embedding_pregunta = None
    if pregunta:
        modelo = SentenceTransformer(MODEL_NAME)
        embedding_pregunta = modelo.encode([pregunta], normalize_embeddings=True)[0]

    n_puntos = len(embeddings) + (1 if pregunta else 0)
    n_neighbors = max(2, min(10, n_puntos - 1))

    matriz = embeddings if embedding_pregunta is None else np.vstack([embeddings, embedding_pregunta])

    print(f"Proyectando {n_puntos} embeddings de 384D a {dim}D con UMAP (n_neighbors={n_neighbors})...")
    reductor = umap.UMAP(n_components=dim, n_neighbors=n_neighbors, min_dist=0.3, random_state=42)
    coords = reductor.fit_transform(matriz)

    coords_chunks = coords[: len(embeddings)]
    coords_pregunta = coords[len(embeddings)] if embedding_pregunta is not None else None

    vecinos_idx = []
    if embedding_pregunta is not None:
        similitudes = similitud_coseno(embedding_pregunta, embeddings)
        vecinos_idx = list(np.argsort(similitudes)[::-1][:TOP_K_VECINOS])
        print(f"\nPregunta: {pregunta}")
        print(f"Top-{TOP_K_VECINOS} chunks mas similares (similitud real en 384D, no en la proyeccion {dim}D):")
        for idx in vecinos_idx:
            print(f"  - {ids[idx]} ({fuentes[idx]}) similitud={similitudes[idx]:.4f}")

    fig = construir_figura(dim, coords_chunks, fuentes, textos, ids, coords_pregunta, vecinos_idx)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"embeddings_{dim}d.html"
    fig.write_html(str(output_path))
    print(f"\n[OK] Visualizacion guardada en: {output_path}")
    print("Abrila en un navegador para explorarla de forma interactiva.")


if __name__ == "__main__":
    main()
