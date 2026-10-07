"""Cadena RAG: busca los fragmentos relevantes en ChromaDB y genera la respuesta con Claude."""

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

from config import TOP_K
from ingest import ingestar_documentos
from schemas import RespuestaRAG

load_dotenv()  # lee ANTHROPIC_API_KEY del archivo .env

# 1. Base vectorial (si no existe, la crea) y retriever.
#    El retriever convierte la pregunta en embedding y trae los TOP_K fragmentos más parecidos.
vectorstore = ingestar_documentos()
retriever = vectorstore.as_retriever(search_kwargs={"k": TOP_K})

# 2. Parser: convierte la respuesta del modelo en un objeto RespuestaRAG.
parser = PydanticOutputParser(pydantic_object=RespuestaRAG)

# 3. Prompt con el "filtro de veracidad".
prompt = ChatPromptTemplate.from_messages([
    ("system",
     "Eres el asistente interno de las sucursales de Supermercados del Valle.\n"
     "Responde SOLO con la información del CONTEXTO. No uses conocimiento propio.\n"
     'Si la respuesta no está en el CONTEXTO, responde exactamente "No lo sé." '
     "y deja la lista de referencias vacía.\n\n"
     "{instrucciones_formato}"),
    ("human", "CONTEXTO:\n{contexto}\n\nPREGUNTA: {pregunta}"),
]).partial(instrucciones_formato=parser.get_format_instructions())

# 4. Modelo de Anthropic. temperature=0 para respuestas lo más precisas posible.
model = ChatAnthropic(model="claude-sonnet-4-5", temperature=0, max_tokens=1000)


def formatear_documentos(documentos):
    """Une los fragmentos en un solo texto, indicando de qué archivo viene cada uno."""
    return "\n\n".join(f"[fuente: {d.metadata['fuente']}]\n{d.page_content}" for d in documentos)


# 5. Cadena LCEL: pregunta -> retriever -> contexto -> prompt -> modelo -> parser.
chain = (
    {"contexto": retriever | formatear_documentos, "pregunta": RunnablePassthrough()}
    | prompt
    | model
    | parser
)

# 6. Función asíncrona que recibe la pregunta y devuelve la respuesta RAG.
async def get_rag_response(query: str) -> RespuestaRAG:
    return await chain.ainvoke(query)
