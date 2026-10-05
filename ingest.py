"""Módulo de ingesta: lee los documentos de /data, los fragmenta y los guarda en ChromaDB.

Uso:
    python ingest.py            # indexa solo si la base todavía no existe
    python ingest.py --rebuild  # borra la colección y vuelve a indexar todo
"""

import argparse
import logging

import chromadb
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from transformers import AutoTokenizer

from config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    COLLECTION_NAME,
    DATA_DIR,
    EMBEDDING_MODEL,
    VECTORSTORE_DIR,
    get_embeddings,
)

logger = logging.getLogger(__name__)


def cargar_documentos() -> list[Document]:
    """Lee todos los archivos .txt y .md de la carpeta data/."""
    archivos = sorted(p for p in DATA_DIR.iterdir() if p.suffix in (".txt", ".md"))
    if not archivos:
        raise FileNotFoundError(f"No hay archivos .txt o .md en {DATA_DIR}")

    documentos = [
        Document(page_content=p.read_text(encoding="utf-8"), metadata={"fuente": p.name})
        for p in archivos
    ]
    logger.info("Documentos cargados: %d", len(documentos))
    return documentos


def fragmentar(documentos: list[Document]) -> list[Document]:
    """Divide los documentos en fragmentos de 500 tokens con 50 de solapamiento."""
    # El tamaño se mide en tokens del modelo de embeddings, no en caracteres.
    tokenizer = AutoTokenizer.from_pretrained(EMBEDDING_MODEL)
    splitter = RecursiveCharacterTextSplitter.from_huggingface_tokenizer(
        tokenizer,
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        # Primero intenta cortar por secciones del Markdown, después por párrafos, etc.
        separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " ", ""],
    )

    fragmentos = []
    for doc in documentos:
        for i, fragmento in enumerate(splitter.split_documents([doc])):
            fragmento.metadata["fragmento"] = i  # número de fragmento dentro del archivo
            fragmentos.append(fragmento)

    logger.info("Fragmentos generados: %d", len(fragmentos))
    return fragmentos


def ingestar_documentos(rebuild: bool = False) -> Chroma:
    """Devuelve la base vectorial, indexando los documentos solo si hace falta."""
    client = chromadb.PersistentClient(path=str(VECTORSTORE_DIR))

    if rebuild and COLLECTION_NAME in [c.name for c in client.list_collections()]:
        client.delete_collection(COLLECTION_NAME)
        logger.info("Colección anterior eliminada.")

    vectorstore = Chroma(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding_function=get_embeddings(),
        # Guardamos qué modelo de embeddings se usó, para poder verificarlo al consultar.
        # "cosine": los embeddings están normalizados, así que comparamos por coseno.
        collection_metadata={"embedding_model": EMBEDDING_MODEL, "hnsw:space": "cosine"},
    )

    # Persistencia: si la colección ya tiene datos, no se vuelve a indexar.
    cantidad = vectorstore._collection.count()
    if cantidad > 0:
        logger.info("La base vectorial ya existe (%d fragmentos). Se omite la ingesta.", cantidad)
        return vectorstore

    fragmentos = fragmentar(cargar_documentos())
    # IDs fijos (archivo:número) para que una re-ingesta no duplique fragmentos.
    ids = [f"{f.metadata['fuente']}:{f.metadata['fragmento']}" for f in fragmentos]
    vectorstore.add_documents(fragmentos, ids=ids)
    logger.info("Ingesta completa: %d fragmentos guardados en %s", len(fragmentos), VECTORSTORE_DIR)
    return vectorstore


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    # Silenciamos los logs de las librerías para que se lea mejor la salida.
    for nombre in ("httpx", "sentence_transformers"):
        logging.getLogger(nombre).setLevel(logging.WARNING)
    parser = argparse.ArgumentParser(description="Indexa los documentos de data/ en ChromaDB.")
    parser.add_argument("--rebuild", action="store_true", help="borra la base y reindexa todo")
    ingestar_documentos(rebuild=parser.parse_args().rebuild)
