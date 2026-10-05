"""Configuración compartida entre la ingesta (ingest.py) y la consulta (rag_chain.py).

Las dos partes importan el modelo de embeddings desde este archivo, para que siempre sea
el mismo: si se indexa con un modelo y se consulta con otro, las distancias no tienen sentido.
"""

from pathlib import Path

from langchain_huggingface import HuggingFaceEmbeddings

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
VECTORSTORE_DIR = BASE_DIR / "vectorstore"
COLLECTION_NAME = "kuntur_docs"

# Modelo de embeddings local (no necesita API key). Es multilingüe, así que funciona bien
# con documentos en español, y acepta textos de hasta 512 tokens.
EMBEDDING_MODEL = "intfloat/multilingual-e5-small"

# Chunking: 500 tokens con 50 de solapamiento, medidos con el tokenizador del propio
# modelo de embeddings. Así cada fragmento entra completo en los 512 tokens que acepta.
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# Cantidad de fragmentos que se le pasan al LLM (entre 3 y 5 para evitar "Lost in the Middle").
TOP_K = 4


def get_embeddings() -> HuggingFaceEmbeddings:
    # Los modelos e5 se entrenaron con los prefijos "passage: " para los documentos
    # y "query: " para las preguntas. Sin ellos, la búsqueda empeora bastante.
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        encode_kwargs={"prompt": "passage: ", "normalize_embeddings": True},
        query_encode_kwargs={"prompt": "query: ", "normalize_embeddings": True},
    )
