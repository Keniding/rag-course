"""
Etapa 7 (extra) · Evaluación del pipeline con RAGAS (Lección 4, sección 6).

Construir un sistema RAG es solo la mitad del trabajo: sin una forma
objetiva de medir su calidad, no se puede saber si un cambio (otro tamaño de
chunk, otro modelo de embeddings, agregar re-ranking) lo mejoró o lo
empeoró. Este script corre el pipeline actual contra un pequeño "dataset
dorado" (`dataset_dorado.json`: preguntas + respuesta esperada + chunk
esperado) y mide:

- **Context Recall** y **Context Precision** (retrieval): ¿se recuperó el
  chunk que realmente contenía la respuesta?
- **Faithfulness** y **Answer Relevancy** (generación): ¿la respuesta
  generada está respaldada por el contexto, y responde lo que se preguntó?

Faithfulness y Answer Relevancy requieren un LLM que actúe como "juez" —
en este taller, Claude vía `ANTHROPIC_API_KEY`. Sin esa key, el script sigue
funcionando pero cae a una versión simplificada de Context Recall/Precision
que no necesita LLM (compara IDs de chunks, no significado), y omite
faithfulness/answer relevancy con un mensaje explícito — el mismo patrón de
fallback que ya usa la etapa 04.
"""

import asyncio
import json
import os
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parent.parent
CHROMA_PATH = BASE_DIR / "data" / "chroma_db"
DATASET_PATH = Path(__file__).resolve().parent / "dataset_dorado.json"

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
COLLECTION_NAME = "technova_knowledge_base"
CLAUDE_MODEL = "claude-sonnet-5"
TOP_K = 4
SIMILARITY_THRESHOLD = 0.15

PROMPT_TEMPLATE = """Eres un asistente interno de TechNova S.A. que responde preguntas basándote únicamente en los documentos proporcionados.

<context>
{contexto}
</context>

Instrucciones:
- Responde la pregunta usando solo la información en <context>.
- Sé breve y directo.
- Si el contexto no contiene información suficiente, dilo explícitamente. No inventes.

<question>
{pregunta}
</question>"""


def recuperar_chunks(modelo: SentenceTransformer, coleccion, pregunta: str) -> list[dict]:
    embedding = modelo.encode([pregunta], normalize_embeddings=True).tolist()
    resultados = coleccion.query(query_embeddings=embedding, n_results=TOP_K)

    chunks = []
    for chunk_id, texto, distancia in zip(
        resultados["ids"][0], resultados["documents"][0], resultados["distances"][0]
    ):
        similitud = 1 - distancia
        if similitud >= SIMILARITY_THRESHOLD:
            chunks.append({"chunk_id": chunk_id, "texto": texto})
    return chunks


def generar_respuesta_extractiva(chunks: list[dict]) -> str:
    return " ".join(c["texto"][:200] for c in chunks)


def generar_respuesta_con_claude(pregunta: str, chunks: list[dict]) -> str:
    import anthropic

    contexto = "\n\n".join(f"<document>{c['texto']}</document>" for c in chunks)
    prompt = PROMPT_TEMPLATE.format(contexto=contexto, pregunta=pregunta)
    cliente = anthropic.Anthropic()
    mensaje = cliente.messages.create(
        model=CLAUDE_MODEL, max_tokens=300, messages=[{"role": "user", "content": prompt}]
    )
    return mensaje.content[0].text


def metricas_sin_llm(chunk_esperado: str, chunks_recuperados: list[dict]) -> dict:
    """
    Aproximación de Context Recall/Precision SIN LLM: en vez de juzgar
    significado, compara directamente si el chunk_id esperado aparece entre
    los recuperados. Es una simplificación (RAGAS con LLM compara contenido,
    no IDs), pero no necesita ninguna API key.
    """
    ids_recuperados = [c["chunk_id"] for c in chunks_recuperados]
    encontrado = chunk_esperado in ids_recuperados

    recall = 1.0 if encontrado else 0.0
    # precision: de los recuperados, que fraccion es "la respuesta correcta"
    # (aqui solo conocemos un chunk relevante por pregunta, es una simplificacion)
    precision = (1.0 / len(ids_recuperados)) if encontrado and ids_recuperados else 0.0

    return {"context_recall_simple": recall, "context_precision_simple": precision}


async def metricas_con_llm(
    pregunta: str, respuesta: str, contextos: list[str], referencia: str, embeddings_ragas
) -> dict:
    import anthropic
    from ragas.embeddings import HuggingfaceEmbeddings
    from ragas.llms import llm_factory
    from ragas.metrics.collections import AnswerRelevancy, ContextPrecisionWithReference, ContextRecall, Faithfulness

    llm = llm_factory(CLAUDE_MODEL, provider="anthropic", client=anthropic.Anthropic())

    faithfulness = Faithfulness(llm=llm)
    answer_relevancy = AnswerRelevancy(llm=llm, embeddings=embeddings_ragas)
    context_precision = ContextPrecisionWithReference(llm=llm)
    context_recall = ContextRecall(llm=llm)

    r_faith = await faithfulness.ascore(user_input=pregunta, response=respuesta, retrieved_contexts=contextos)
    r_rel = await answer_relevancy.ascore(user_input=pregunta, response=respuesta)
    r_prec = await context_precision.ascore(user_input=pregunta, reference=referencia, retrieved_contexts=contextos)
    r_rec = await context_recall.ascore(user_input=pregunta, retrieved_contexts=contextos, reference=referencia)

    return {
        "faithfulness": r_faith.value,
        "answer_relevancy": r_rel.value,
        "context_precision": r_prec.value,
        "context_recall": r_rec.value,
    }


async def evaluar():
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    modelo = SentenceTransformer(MODEL_NAME)
    cliente_chroma = chromadb.PersistentClient(path=str(CHROMA_PATH))
    coleccion = cliente_chroma.get_collection(COLLECTION_NAME)

    hay_api_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    embeddings_ragas = None
    if hay_api_key:
        from ragas.embeddings import HuggingfaceEmbeddings

        embeddings_ragas = HuggingfaceEmbeddings(model_name=MODEL_NAME)

    resultados = []
    for caso in dataset:
        pregunta = caso["pregunta"]
        chunks = recuperar_chunks(modelo, coleccion, pregunta)
        contextos = [c["texto"] for c in chunks]

        fila = {"pregunta": pregunta, **metricas_sin_llm(caso["chunk_esperado"], chunks)}

        if hay_api_key:
            respuesta = generar_respuesta_con_claude(pregunta, chunks)
            metricas_llm = await metricas_con_llm(
                pregunta, respuesta, contextos, caso["respuesta_esperada"], embeddings_ragas
            )
            fila.update(metricas_llm)
            fila["respuesta_generada"] = respuesta

        resultados.append(fila)

    return resultados, hay_api_key


def imprimir_reporte(resultados: list[dict], hay_api_key: bool):
    print(f"Dataset dorado: {len(resultados)} preguntas\n")

    if not hay_api_key:
        print(
            "ANTHROPIC_API_KEY no configurada: se muestran solo metricas de\n"
            "retrieval simplificadas (sin LLM). Faithfulness y Answer Relevancy\n"
            "requieren un LLM como juez y se omiten.\n"
        )
        for r in resultados:
            print(f"- {r['pregunta']}")
            print(
                f"    context_recall_simple={r['context_recall_simple']:.2f}  "
                f"context_precision_simple={r['context_precision_simple']:.2f}"
            )
        recall_prom = sum(r["context_recall_simple"] for r in resultados) / len(resultados)
        precision_prom = sum(r["context_precision_simple"] for r in resultados) / len(resultados)
        print(f"\nPromedio -> context_recall_simple={recall_prom:.2f}  context_precision_simple={precision_prom:.2f}")
        return

    print("Metricas RAGAS completas (Claude como LLM juez):\n")
    for r in resultados:
        print(f"- {r['pregunta']}")
        print(f"    faithfulness={r['faithfulness']:.2f}  answer_relevancy={r['answer_relevancy']:.2f}")
        print(f"    context_precision={r['context_precision']:.2f}  context_recall={r['context_recall']:.2f}")

    for metrica in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]:
        promedio = sum(r[metrica] for r in resultados) / len(resultados)
        print(f"\nPromedio {metrica}: {promedio:.2f}")


def main():
    resultados, hay_api_key = asyncio.run(evaluar())
    imprimir_reporte(resultados, hay_api_key)


if __name__ == "__main__":
    main()
