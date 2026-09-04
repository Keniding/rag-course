"""
Etapa 1 · Ingesta y preparación de documentos.

Lee todos los documentos privados de `data/raw/`, extrae texto plano
(soporta .md, .txt y .pdf) y normaliza el contenido. El resultado se
guarda en `data/processed/01_documentos.json` para que la siguiente
etapa (chunking) lo consuma.
"""

import hashlib
import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
OUTPUT_PATH = BASE_DIR / "data" / "processed" / "01_documentos.json"

SUPPORTED_EXTENSIONS = {".md", ".txt", ".pdf"}

# Detecta bloques de tabla Markdown: una fila de encabezado, la fila
# separadora (---|---|---), y una o más filas de datos.
PATRON_TABLA_MARKDOWN = re.compile(
    r"^\|.+\|\n\|[\s:|-]+\|\n(?:\|.+\|\n?)+", re.MULTILINE
)


def leer_pdf(path: Path) -> str:
    """Extrae texto de un PDF usando pypdfium2 (ya instalado en la máquina)."""
    import pypdfium2 as pdfium

    texto = []
    pdf = pdfium.PdfDocument(str(path))
    for pagina in pdf:
        textpage = pagina.get_textpage()
        texto.append(textpage.get_text_range())
    return "\n".join(texto)


def leer_texto_plano(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def normalizar_texto(texto: str) -> str:
    """Limpieza básica: colapsa espacios/saltos de línea repetidos."""
    texto = texto.replace("\r\n", "\n")
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def parsear_fila_markdown(linea: str) -> list[str]:
    """Convierte '| a | b | c |' en ['a', 'b', 'c'], recortando espacios."""
    celdas = linea.strip().strip("|").split("|")
    return [c.strip() for c in celdas]


def extraer_tablas(texto: str) -> list[dict]:
    """
    Encuentra tablas Markdown en el texto y las devuelve preservando la
    relación fila-columna (a diferencia de aplanarlas a texto plano, que
    perdería qué valor corresponde a qué encabezado — ver Lección 1).
    Cada tabla se devuelve en dos formatos: el bloque Markdown original
    (para insertarlo tal cual en el contexto de un LLM) y una lista de
    filas como diccionarios (para procesamiento programático).
    """
    tablas = []
    for match in PATRON_TABLA_MARKDOWN.finditer(texto):
        bloque = match.group(0).strip()
        lineas = [l for l in bloque.split("\n") if l.strip()]

        encabezados = parsear_fila_markdown(lineas[0])
        filas_datos = lineas[2:]  # se salta encabezado y separador

        filas = [dict(zip(encabezados, parsear_fila_markdown(fila))) for fila in filas_datos]

        tablas.append({"markdown": bloque, "encabezados": encabezados, "filas": filas})

    return tablas


def ingerir_documentos(raw_dir: Path) -> list[dict]:
    documentos = []
    archivos = sorted(p for p in raw_dir.glob("*") if p.suffix.lower() in SUPPORTED_EXTENSIONS)

    if not archivos:
        raise FileNotFoundError(
            f"No se encontraron documentos soportados en {raw_dir}. "
            f"Formatos válidos: {sorted(SUPPORTED_EXTENSIONS)}"
        )

    for path in archivos:
        if path.suffix.lower() == ".pdf":
            texto_crudo = leer_pdf(path)
        else:
            texto_crudo = leer_texto_plano(path)

        texto_limpio = normalizar_texto(texto_crudo)
        content_hash = hashlib.sha256(texto_limpio.encode("utf-8")).hexdigest()
        tablas = extraer_tablas(texto_limpio)

        documentos.append(
            {
                "doc_id": path.stem,
                "fuente": path.name,
                "tipo": path.suffix.lower().lstrip("."),
                "content_hash": content_hash,
                "n_caracteres": len(texto_limpio),
                "texto": texto_limpio,
                "tablas": tablas,
            }
        )

    return documentos


def main():
    print(f"Buscando documentos en: {RAW_DIR}")
    documentos = ingerir_documentos(RAW_DIR)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(documentos, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"[OK] {len(documentos)} documento(s) ingeridos:")
    for doc in documentos:
        hash_corto = doc["content_hash"][:12]
        info_tablas = f", {len(doc['tablas'])} tabla(s)" if doc["tablas"] else ""
        print(f"  - {doc['fuente']} ({doc['n_caracteres']} caracteres, hash={hash_corto}...{info_tablas})")
    print(f"\nGuardado en: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
