# Pre-entrega 3: Sistema de recuperación semántica local (RAG)

Asistente interno para las sucursales de **Supermercados del Valle**, una cadena de supermercados ficticia. El personal hace una pregunta sobre los procedimientos de la empresa, el sistema busca la información en los documentos y Claude responde usando **solo** esa información. Si la respuesta no está, responde "No lo sé.".

## Archivos

| Archivo | Qué hace |
|---|---|
| `data/` | Dataset: 4 documentos `.md` con procedimientos de la empresa (recepción de mercadería, reposición y stock, cajas y atención, personal y seguridad). |
| `config.py` | Configuración compartida: modelo de embeddings, tamaño de los fragmentos y `top_k`. |
| `ingest.py` | **Ingesta**: lee `data/`, divide los documentos en fragmentos y los guarda en ChromaDB. |
| `schemas.py` | Modelo Pydantic de la respuesta: texto + referencias. |
| `rag_chain.py` | **Retriever + generación**: la cadena LCEL y la función asíncrona `get_rag_response()`. |
| `demo.py` | Las pruebas: una pregunta con respuesta y dos preguntas trampa. |

## Cómo funciona

### 1. Ingesta (`ingest.py`)

1. Lee los archivos `.txt` y `.md` de `data/`.
2. Los divide con `RecursiveCharacterTextSplitter` en fragmentos de **500 tokens con 50 de solapamiento**. Los tokens se cuentan con el tokenizador del modelo de embeddings, que acepta hasta 512.
3. Convierte cada fragmento en un embedding y lo guarda en ChromaDB, en la carpeta `./vectorstore` (`PersistentClient`). La búsqueda usa similitud coseno.
4. Si la base ya tiene datos, **no vuelve a indexar**. Para forzarlo: `python ingest.py --rebuild`.

### 2. Embeddings

Se usa `intfloat/multilingual-e5-small`, un modelo que corre **localmente** (gratis y sin API key) y funciona bien en español. La ingesta y la consulta toman el modelo de la misma función, `get_embeddings()` en `config.py`, así que siempre se usa el mismo para indexar y para consultar.

### 3. Cadena RAG (`rag_chain.py`)

```python
chain = (
    {"contexto": retriever | formatear_documentos, "pregunta": RunnablePassthrough()}
    | prompt
    | model
    | parser
)
```

1. **Retriever**: convierte la pregunta en embedding y trae los 4 fragmentos más parecidos.
2. **formatear_documentos**: une los fragmentos en un texto, indicando de qué archivo viene cada uno.
3. **Prompt**: le indica a Claude que responda solo con el CONTEXTO y que diga "No lo sé." si la respuesta no está.
4. **Modelo**: Claude (`claude-sonnet-4-5`) con `temperature=0`.
5. **PydanticOutputParser**: convierte la respuesta en un objeto `RespuestaRAG` con `respuesta` y `referencias`.

La función asíncrona que pide la consigna:

```python
async def get_rag_response(query: str) -> RespuestaRAG:
    return await chain.ainvoke(query)
```

## Cómo ejecutarlo

Requiere Python 3.12. Los comandos se ejecutan desde la carpeta del proyecto.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env      # pegar la ANTHROPIC_API_KEY en .env

python ingest.py            # crea la base vectorial
python demo.py              # corre las pruebas
```

La primera vez se descarga el modelo de embeddings (~470 MB).

## Pruebas y resultados

```text
Pregunta: ¿Qué hago si llega un camión de lácteos a más de 8 °C?
{
  "respuesta": "Si un producto llega por encima de su temperatura máxima, se rechaza la entrega completa de ese producto. El receptor debe anotar en el remito la temperatura medida y el motivo del rechazo, y avisar al encargado. Nunca se acepta mercadería fuera de temperatura \"para venderla rápido\". Además, cuando se rechaza mercadería, se saca una foto que se envía al grupo de compras de la oficina central.",
  "referencias": ["01_recepcion_mercaderia.md"]
}

Pregunta: ¿Cuánto cobra un repositor por mes?
{"respuesta": "No lo sé.", "referencias": []}

Pregunta: ¿Quién ganó el Mundial de fútbol de 2022?
{"respuesta": "No lo sé.", "referencias": []}
```

- **Pregunta 1**: la respuesta está en los documentos. Claude la responde y cita el archivo correcto.
- **Pregunta 2 (trampa)**: hay un documento sobre el personal, pero no dice nada de sueldos. Claude no inventa un monto.
- **Pregunta 3 (trampa)**: Claude sabe quién ganó, pero no está en los documentos, así que responde "No lo sé.".

## Seguridad

La API key se lee de `.env`, que está en `.gitignore` y no se sube al repositorio.
