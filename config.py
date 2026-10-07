"""Configuración compartida entre ingest.py y rag_chain.py.

Los dos archivos usan get_embeddings() de acá, así siempre se usa el mismo modelo
de embeddings para indexar y para consultar.
"""

from langchain_huggingface import HuggingFaceEmbeddings

DATA_DIR = "data"
VECTORSTORE_DIR = "vectorstore"
COLLECTION_NAME = "supermercado_docs"

# Modelo de embeddings local, gratis y multilingüe. Acepta textos de hasta 512 tokens.
EMBEDDING_MODEL = "intfloat/multilingual-e5-small"

CHUNK_SIZE = 500    # tokens por fragmento
CHUNK_OVERLAP = 50  # tokens que se repiten entre un fragmento y el siguiente
TOP_K = 4           # fragmentos que se le pasan al LLM


def get_embeddings():
    # El modelo e5 espera "passage: " delante de los documentos y "query: " delante de las preguntas.
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        encode_kwargs={"prompt": "passage: ", "normalize_embeddings": True},
        query_encode_kwargs={"prompt": "query: ", "normalize_embeddings": True},
    )
