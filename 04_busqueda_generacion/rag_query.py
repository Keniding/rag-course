"""
Etapa 4 · Búsqueda por similitud y generación de respuestas con contexto.

Dado un query del usuario:
  1. Lo vectoriza con el mismo modelo de embeddings de la etapa 3.
  2. Busca en ChromaDB los `k` chunks más similares (retrieval).
  3. Arma un prompt que incluye esos chunks como contexto.
  4. Genera la respuesta final con Claude (Anthropic). Si no hay
     ANTHROPIC_API_KEY configurada, cae a un modo "extractivo" que
     responde solo con los fragmentos recuperados (sin LLM), útil para
     validar la parte de retrieval sin costo ni API key.
"""

import os
import sys
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parent.parent
CHROMA_PATH = BASE_DIR / "data" / "chroma_db"

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
COLLECTION_NAME = "technova_knowledge_base"
TOP_K = 4
# Con embeddings normalizados y espacio "cosine", Chroma devuelve una distancia
# en [0, 2]; similitud = 1 - distancia. Chunks por debajo de este umbral se
# descartan porque probablemente no son relevantes para la pregunta.
SIMILARITY_THRESHOLD = 0.15
CLAUDE_MODEL = "claude-sonnet-5"

# Prompt con etiquetas XML + instrucción anti-alucinación explícita,
# siguiendo el mismo patrón que la Lección 4 del material teórico.
PROMPT_TEMPLATE = """Eres un asistente interno de TechNova S.A. que responde preguntas basándote únicamente en los documentos proporcionados.

<context>
{contexto}
</context>

Instrucciones:
- Responde la pregunta usando solo la información en <context>.
- Cita la fuente (ej. "según manual_producto.md") que respalda cada afirmación importante.
- Si el contexto no contiene información suficiente para responder con confianza, dilo explícitamente. No inventes ni completes con conocimiento externo al contexto.

<question>
{pregunta}
</question>"""


def recuperar_chunks(pregunta: str, k: int = TOP_K, umbral: float = SIMILARITY_THRESHOLD) -> list[dict]:
    if not CHROMA_PATH.exists():
        raise FileNotFoundError(
            f"No existe {CHROMA_PATH}. Ejecuta primero "
            f"03_embeddings_vectorstore/embeddings_vectorstore.py"
        )

    modelo = SentenceTransformer(MODEL_NAME)
    embedding_pregunta = modelo.encode([pregunta], normalize_embeddings=True).tolist()

    cliente = chromadb.PersistentClient(path=str(CHROMA_PATH))
    coleccion = cliente.get_collection(COLLECTION_NAME)

    resultados = coleccion.query(
        query_embeddings=embedding_pregunta,
        n_results=k,
    )

    chunks = []
    for texto, metadata, distancia in zip(
        resultados["documents"][0],
        resultados["metadatas"][0],
        resultados["distances"][0],
    ):
        similitud = 1 - distancia
        if similitud >= umbral:
            chunks.append(
                {"texto": texto, "metadata": metadata, "similitud": similitud}
            )
    return chunks


def construir_prompt(pregunta: str, chunks: list[dict]) -> str:
    bloques = [
        f'<document index="{i}" source="{c["metadata"]["fuente"]}">\n{c["texto"]}\n</document>'
        for i, c in enumerate(chunks, start=1)
    ]
    contexto = "\n\n".join(bloques)
    return PROMPT_TEMPLATE.format(contexto=contexto, pregunta=pregunta)


def generar_respuesta_con_claude(prompt: str) -> str:
    import anthropic

    cliente = anthropic.Anthropic()  # usa ANTHROPIC_API_KEY del entorno
    mensaje = cliente.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    return mensaje.content[0].text


def generar_respuesta_extractiva(chunks: list[dict]) -> str:
    """Fallback sin LLM: concatena los fragmentos más relevantes con su fuente."""
    lineas = [
        "[Modo extractivo - sin LLM, no hay ANTHROPIC_API_KEY configurada]",
        "Fragmentos mas relevantes encontrados:",
        "",
    ]
    for i, c in enumerate(chunks, start=1):
        lineas.append(f"{i}. (fuente: {c['metadata']['fuente']})")
        lineas.append(f"   {c['texto'][:300].strip()}")
        lineas.append("")
    return "\n".join(lineas)


def main():
    if len(sys.argv) < 2:
        print('Uso: python rag_query.py "<tu pregunta>"')
        sys.exit(1)

    pregunta = sys.argv[1]
    print(f"Pregunta: {pregunta}\n")

    chunks = recuperar_chunks(pregunta)
    print(f"Chunks recuperados ({len(chunks)}, umbral de similitud={SIMILARITY_THRESHOLD}):")
    for c in chunks:
        print(f"  - {c['metadata']['fuente']} (similitud={c['similitud']:.4f})")
    print()

    if not chunks:
        print("Respuesta:")
        print("No encontre informacion relevante en la base de conocimiento para responder esta pregunta.")
        return

    if os.environ.get("ANTHROPIC_API_KEY"):
        prompt = construir_prompt(pregunta, chunks)
        respuesta = generar_respuesta_con_claude(prompt)
    else:
        respuesta = generar_respuesta_extractiva(chunks)

    print("Respuesta:")
    print(respuesta)


if __name__ == "__main__":
    main()
