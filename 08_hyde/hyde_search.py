"""
Etapa 8 (extra) · HyDE — Hypothetical Document Embeddings (Lección 4, 5.2).

Una pregunta y su respuesta tienen "formas" de embedding distintas: una
pregunta corta ("¿cuál es la política de reembolsos?") y el párrafo denso
que la responde no siempre quedan tan cerca en el espacio de embeddings
como uno esperaría, porque son tipos de texto distintos.

HyDE resuelve esto de forma indirecta: en vez de buscar con el embedding de
la pregunta, primero le pide a un LLM que genere una respuesta HIPOTÉTICA
(no necesita ser correcta — solo tener la forma y el vocabulario de una
respuesta real), y busca con el embedding de ESA respuesta. La intuición es
que ese documento hipotético se parece más a los documentos reales que la
pregunta original.

Requiere un LLM para generar el documento hipotético — sin ANTHROPIC_API_KEY
no hay forma de demostrar HyDE de verdad (a diferencia de las otras etapas,
acá no existe un "modo sin LLM" razonable, HyDE ES el uso del LLM).
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
CLAUDE_MODEL = "claude-sonnet-5"
TOP_K = 4

PROMPT_GENERAR_HIPOTETICO = """Redacta un párrafo breve (2-3 oraciones) que podría ser la respuesta a la siguiente pregunta, como si fuera un fragmento de la documentación interna de una empresa de software (manuales, políticas de soporte, FAQs). No necesita ser precisa ni tienes información real de la empresa — solo debe sonar como un fragmento de documentación real, con vocabulario técnico plausible.

Pregunta: {pregunta}

Párrafo hipotético:"""


def generar_documento_hipotetico(pregunta: str) -> str:
    import anthropic

    cliente = anthropic.Anthropic()
    mensaje = cliente.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=150,
        messages=[{"role": "user", "content": PROMPT_GENERAR_HIPOTETICO.format(pregunta=pregunta)}],
    )
    return mensaje.content[0].text.strip()


def buscar(modelo: SentenceTransformer, coleccion, texto_para_embeder: str) -> list[dict]:
    embedding = modelo.encode([texto_para_embeder], normalize_embeddings=True).tolist()
    resultados = coleccion.query(query_embeddings=embedding, n_results=TOP_K)
    return [
        {"chunk_id": id_, "fuente": meta["fuente"], "similitud": 1 - dist}
        for id_, meta, dist in zip(
            resultados["ids"][0], resultados["metadatas"][0], resultados["distances"][0]
        )
    ]


def imprimir_resultados(titulo: str, resultados: list[dict]):
    print(f"{titulo}:")
    for r in resultados:
        print(f"  - {r['chunk_id']} ({r['fuente']}) similitud={r['similitud']:.4f}")


def main():
    if len(sys.argv) < 2:
        print('Uso: python hyde_search.py "<tu pregunta>"')
        sys.exit(1)

    pregunta = sys.argv[1]
    modelo = SentenceTransformer(MODEL_NAME)
    cliente_chroma = chromadb.PersistentClient(path=str(CHROMA_PATH))
    coleccion = cliente_chroma.get_collection(COLLECTION_NAME)

    print(f"Pregunta: {pregunta}\n")

    resultados_directos = buscar(modelo, coleccion, pregunta)
    imprimir_resultados("Busqueda directa (embedding de la pregunta)", resultados_directos)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(
            "\nANTHROPIC_API_KEY no configurada: HyDE requiere un LLM para generar\n"
            "el documento hipotetico, no tiene un modo sin LLM razonable (a diferencia\n"
            "de las otras etapas de este taller). No se puede comparar contra HyDE\n"
            "sin una API key."
        )
        return

    documento_hipotetico = generar_documento_hipotetico(pregunta)
    print(f"\nDocumento hipotetico generado por Claude:\n  \"{documento_hipotetico}\"\n")

    resultados_hyde = buscar(modelo, coleccion, documento_hipotetico)
    imprimir_resultados("Busqueda HyDE (embedding del documento hipotetico)", resultados_hyde)


if __name__ == "__main__":
    main()
