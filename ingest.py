"""Ingesta: lee los documentos de data/, los divide en fragmentos y los guarda en ChromaDB.

Uso:
    python ingest.py            # indexa solo si la base todavía no existe
    python ingest.py --rebuild  # borra la base y vuelve a indexar todo
"""

import sys
from pathlib import Path

import chromadb
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from transformers import AutoTokenizer

from config import (CHUNK_OVERLAP, CHUNK_SIZE, COLLECTION_NAME, DATA_DIR,
                    EMBEDDING_MODEL, VECTORSTORE_DIR, get_embeddings)


def cargar_documentos():
    """Lee todos los archivos .txt y .md de la carpeta data/."""
    documentos = []
    for archivo in sorted(Path(DATA_DIR).iterdir()):
        if archivo.suffix in (".txt", ".md"):
            texto = archivo.read_text(encoding="utf-8")
            documentos.append(Document(page_content=texto, metadata={"fuente": archivo.name}))
    print(f"Documentos cargados: {len(documentos)}")
    return documentos


def fragmentar(documentos):
    """Divide los documentos en fragmentos de 500 tokens con 50 de solapamiento."""
    # Los tokens se cuentan con el tokenizador del modelo de embeddings,
    # así cada fragmento entra completo en los 512 tokens que acepta el modelo.
    tokenizer = AutoTokenizer.from_pretrained(EMBEDDING_MODEL)
    splitter = RecursiveCharacterTextSplitter.from_huggingface_tokenizer(
        tokenizer, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    )
    fragmentos = splitter.split_documents(documentos)
    print(f"Fragmentos generados: {len(fragmentos)}")
    return fragmentos


def ingestar_documentos(rebuild=False):
    """Devuelve la base vectorial. Solo indexa si la base está vacía."""
    client = chromadb.PersistentClient(path=VECTORSTORE_DIR)  # se guarda en disco

    existe = COLLECTION_NAME in [c.name for c in client.list_collections()]
    if rebuild and existe:
        client.delete_collection(COLLECTION_NAME)
        print("Base anterior eliminada.")

    vectorstore = Chroma(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding_function=get_embeddings(),
        collection_metadata={"hnsw:space": "cosine"},  # similitud coseno
    )

    # Persistencia: si la base ya tiene fragmentos, no se vuelve a indexar.
    if vectorstore._collection.count() > 0:
        print("La base vectorial ya existe. Se omite la ingesta.")
        return vectorstore

    fragmentos = fragmentar(cargar_documentos())
    vectorstore.add_documents(fragmentos)
    print(f"Ingesta completa: {len(fragmentos)} fragmentos guardados en {VECTORSTORE_DIR}/")
    return vectorstore


if __name__ == "__main__":
    ingestar_documentos(rebuild="--rebuild" in sys.argv)
