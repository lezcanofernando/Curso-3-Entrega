"""Cadena RAG asíncrona: recupera fragmentos de ChromaDB y genera una respuesta grounded."""

import logging
import os

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.documents import Document
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough

from config import EMBEDDING_MODEL, TOP_K
from ingest import ingestar_documentos
from schemas import RespuestaRAG

load_dotenv()  # lee ANTHROPIC_API_KEY del archivo .env

logger = logging.getLogger(__name__)

# 1. Base vectorial. ingestar_documentos() solo indexa si la base todavía no existe.
vectorstore = ingestar_documentos()

# Verificación anti "embeddings no coincidentes": la base tiene que haberse creado
# con el mismo modelo que vamos a usar para convertir las preguntas en vectores.
modelo_indexado = vectorstore._collection.metadata.get("embedding_model")
if modelo_indexado != EMBEDDING_MODEL:
    raise RuntimeError(
        f"La base se indexó con '{modelo_indexado}' pero se consulta con '{EMBEDDING_MODEL}'. "
        "Ejecutá: python ingest.py --rebuild"
    )

# 2. Retriever: convierte la pregunta en embedding y trae los TOP_K fragmentos más parecidos.
retriever = vectorstore.as_retriever(search_kwargs={"k": TOP_K})

# 3. Prompt de sistema que funciona como "filtro de veracidad".
prompt = ChatPromptTemplate.from_messages([
    ("system",
     "Eres un asistente técnico del equipo de ingeniería de Kuntur Pay.\n"
     "Responde ÚNICAMENTE con la información del CONTEXTO. No uses conocimiento propio "
     "ni completes con suposiciones.\n"
     'Si la respuesta no está en el CONTEXTO, responde exactamente "No lo sé.", '
     "con encontrada_en_contexto en false y la lista de referencias vacía.\n"
     "Si la respuesta está, cita en referencias los fragmentos que usaste.\n\n"
     "{instrucciones_formato}"),
    ("human", "CONTEXTO:\n{contexto}\n\nPREGUNTA: {pregunta}"),
])

parser = PydanticOutputParser(pydantic_object=RespuestaRAG)
prompt = prompt.partial(instrucciones_formato=parser.get_format_instructions())

# 4. Modelo de Anthropic. temperature=0 para que no "invente" variantes.
model = ChatAnthropic(
    model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5"),
    temperature=0,
    max_tokens=1000,
)


def formatear_documentos(documentos: list[Document]) -> str:
    """Transforma los fragmentos recuperados en texto, con su fuente para poder citarlos."""
    return "\n\n".join(
        f"[fuente: {d.metadata['fuente']} | fragmento: {d.metadata['fragmento']}]\n{d.page_content}"
        for d in documentos
    )


def validar_referencias(entrada: dict) -> RespuestaRAG:
    """Descarta referencias que el modelo haya inventado (que no estén entre los recuperados)."""
    resultado: RespuestaRAG = entrada["respuesta"]
    recuperados = {(d.metadata["fuente"], d.metadata["fragmento"]) for d in entrada["documentos"]}

    validas = [r for r in resultado.referencias if (r.fuente, r.fragmento) in recuperados]
    if len(validas) < len(resultado.referencias):
        logger.warning("Se descartaron referencias que no estaban en el contexto.")
    if not resultado.encontrada_en_contexto:
        validas = []

    resultado.referencias = validas
    return resultado


# 5. Cadena LCEL:
#    pregunta -> retriever (documentos) -> contexto en texto -> prompt -> LLM -> Pydantic
#    -> validación de referencias.
#    with_retry: si el modelo devuelve un JSON inválido, se reintenta (hasta 3 intentos).
generacion = (prompt | model | parser).with_retry(stop_after_attempt=3)

chain = (
    {"documentos": retriever, "pregunta": RunnablePassthrough()}
    | RunnablePassthrough.assign(contexto=lambda x: formatear_documentos(x["documentos"]))
    | RunnablePassthrough.assign(respuesta=generacion)
    | RunnableLambda(validar_referencias)
)


# 6. Función asíncrona pedida en la consigna.
async def get_rag_response(query: str) -> RespuestaRAG:
    logger.info("Pregunta: %s", query)
    return await chain.ainvoke(query)
