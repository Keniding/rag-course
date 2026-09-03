# Sesión 3 — RAG y conocimiento privado

Material práctico del taller: cómo construir un pipeline de **Retrieval-Augmented
Generation (RAG)** de punta a punta usando documentación interna ficticia de
"TechNova S.A." como caso de estudio.

Este material es el complemento práctico de las 4 lecciones teóricas de la
sesión (ingesta, chunking, embeddings/bases vectoriales, y búsqueda +
generación). Cada carpeta numerada corresponde a una lección e implementa,
con código real y validado, las técnicas centrales que esa lección describe.

Todo el código de este taller es funcional y fue validado en esta misma máquina
(ver la sección "Validación" en cada carpeta).

## Arquitectura general

```mermaid
flowchart LR
    subgraph Fuente
        A[("Documentos privados\n(md, txt, pdf)")]
    end

    subgraph "01 · Ingesta"
        B["Cargar y limpiar\ntexto de cada documento"]
    end

    subgraph "02 · Chunking"
        C["Dividir el texto en\nfragmentos (chunks)"]
    end

    subgraph "03 · Embeddings + Vector DB"
        D["Vectorizar cada chunk\n(sentence-transformers)"]
        E[("Base de datos vectorial\nChromaDB")]
    end

    subgraph "04 · Búsqueda + Generación"
        F["Pregunta del usuario"]
        G["Vectorizar la pregunta"]
        H["Búsqueda por similitud\n(top-k chunks)"]
        I["Prompt con contexto\n+ LLM (Claude)"]
        J["Respuesta final"]
    end

    A --> B --> C --> D --> E
    F --> G --> H
    E --> H
    H --> I --> J
```

## Estructura de carpetas

```
s3/
├── pyproject.toml   → manifiesto uv (única fuente de dependencias del taller)
├── uv.lock          → versiones exactas resueltas por uv
├── data/
│   ├── raw/         → documentos privados de ejemplo (fuente de verdad)
│   └── processed/   → salidas intermedias del pipeline (JSON)
├── 01_ingesta_documentos/
├── 02_chunking_contenido/
├── 03_embeddings_vectorstore/
├── 04_busqueda_generacion/
└── 05_tecnicas_avanzadas/   → extra: búsqueda híbrida (BM25) + re-ranking
```

Cada carpeta numerada corresponde a una etapa del pipeline y contiene:

- `README.md` → teoría, diagrama Mermaid y guía paso a paso.
- uno o más scripts `.py` ejecutables de forma independiente.

Las dependencias de **todas** las etapas viven en un único `pyproject.toml`
en la raíz, gestionado con **uv** (no hay `requirements.txt` ni `pip install`
en este proyecto). Las etapas están pensadas para ejecutarse **en orden**,
porque cada una lee la salida de la anterior desde `data/processed/`.

## Cómo ejecutar todo el pipeline

Todos los comandos se corren desde la raíz `s3/` (donde está `pyproject.toml`).
`uv` crea y gestiona el entorno virtual automáticamente — no hace falta crear
uno a mano.

```bash
# sincroniza el entorno con las dependencias de pyproject.toml / uv.lock
uv sync

# ejecutar cada etapa en orden
uv run python 01_ingesta_documentos/ingesta.py
uv run python 02_chunking_contenido/chunking.py
uv run python 03_embeddings_vectorstore/embeddings_vectorstore.py
uv run python 04_busqueda_generacion/rag_query.py "¿Cuál es el SLA para un incidente P1?"

# opcional: búsqueda híbrida + re-ranking (ver 05_tecnicas_avanzadas/README.md)
uv run python 05_tecnicas_avanzadas/hybrid_search.py "¿Cómo se instala el agente de NovaCloud Backup?"
uv run python 05_tecnicas_avanzadas/reranking.py "¿Cómo se instala el agente de NovaCloud Backup?"
```

Si necesitás agregar una dependencia nueva más adelante, usá `uv add <paquete>`
en vez de `pip install` — así queda registrada en `pyproject.toml` y fijada en
`uv.lock` para que el taller siga siendo reproducible.

> **Nota (Windows/PowerShell):** si ves caracteres extraños con tildes en la
> consola, es solo un problema de visualización del terminal (code page).
> Corré `chcp 65001` antes, o antepone `$env:PYTHONIOENCODING="utf-8";` a los
> comandos — el contenido de los archivos generados siempre es UTF-8 correcto.

## Sobre el LLM usado en la etapa 4

El script de generación usa la API de **Anthropic (Claude)**. Si no tienes una
`ANTHROPIC_API_KEY` configurada, el script cae automáticamente a un modo
**extractivo** (sin LLM) que arma la respuesta directamente con los fragmentos
recuperados, para que puedas validar la parte de *retrieval* sin necesitar una
API key. Ver `04_busqueda_generacion/README.md` para más detalle.
