# Pre-entrega 3: Sistema de recuperación semántica local (RAG)

Sistema RAG de punta a punta: recibe una pregunta, busca los fragmentos relevantes en una base vectorial local (ChromaDB) y genera una respuesta con Claude usando **solo** esa información. Si la respuesta no está en los documentos, responde "No lo sé.".

El dataset de ejemplo es la documentación interna de **Kuntur Pay**, una empresa de pagos ficticia. Al ser ficticia, el modelo no puede responder con lo que ya sabe: si responde bien es porque usó el contexto, y si inventa se nota.

## Estructura

| Archivo | Qué hace |
|---|---|
| `data/` | Dataset de ejemplo: 4 documentos `.md` (arquitectura, despliegues, incidentes, API y seguridad). |
| `config.py` | Configuración compartida: rutas, modelo de embeddings, tamaño de chunk y `top_k`. |
| `ingest.py` | **Ingesta**: lee `data/`, fragmenta con `RecursiveCharacterTextSplitter` y guarda en ChromaDB. |
| `schemas.py` | Modelo Pydantic de la respuesta (texto + referencias). |
| `rag_chain.py` | **Retriever + generación grounded**: cadena LCEL y la función asíncrona `get_rag_response()`. |
| `demo.py` | Las pruebas: una pregunta con respuesta y dos preguntas trampa. |

## Cómo funciona

### 1. Ingesta (`ingest.py`)

- Lee todos los `.txt` y `.md` de `data/`.
- Los fragmenta en chunks de **500 tokens con 50 de solapamiento**. Los tokens se cuentan con el tokenizador del propio modelo de embeddings, así cada chunk entra completo en los 512 tokens que acepta el modelo (si fuera más largo, el final se descartaría sin aviso).
- El splitter corta primero por secciones del Markdown (`##`), después por párrafos y por oraciones, para no partir ideas a la mitad.
- Guarda los chunks en un `PersistentClient` de ChromaDB en `./vectorstore`, con IDs fijos (`archivo:número`).
- **Persistencia**: si la colección ya tiene datos, no vuelve a indexar. Para forzarlo: `python ingest.py --rebuild`.

### 2. Embeddings

Se usa `intfloat/multilingual-e5-small` de HuggingFace, que corre **localmente** (gratis y sin API key) y funciona bien en español. Anthropic no ofrece un modelo de embeddings, por eso el LLM y los embeddings son de proveedores distintos.

Para evitar el error de **embeddings no coincidentes**:
- `ingest.py` y `rag_chain.py` toman el modelo de la misma función `get_embeddings()` en `config.py`.
- Al indexar se guarda el nombre del modelo en los metadatos de la colección, y `rag_chain.py` lo compara antes de consultar. Si no coinciden, frena con un error que indica reindexar.

### 3. Recuperación y generación (`rag_chain.py`)

```python
chain = (
    {"documentos": retriever, "pregunta": RunnablePassthrough()}
    | RunnablePassthrough.assign(contexto=lambda x: formatear_documentos(x["documentos"]))
    | RunnablePassthrough.assign(respuesta=prompt | model | parser)
    | RunnableLambda(validar_referencias)
)
```

1. El **retriever** convierte la pregunta en embedding y trae los `top_k = 4` fragmentos más parecidos (similitud coseno). Se mantiene entre 3 y 5 para no saturar al modelo (*Lost in the Middle*).
2. `formatear_documentos` arma el contexto, marcando cada fragmento con su fuente para que el modelo pueda citarlo.
3. El **prompt de sistema** actúa como filtro de veracidad: responder solo con el CONTEXTO y, si la respuesta no está, decir exactamente "No lo sé.".
4. El **`PydanticOutputParser`** convierte la salida del LLM en un objeto `RespuestaRAG`. Si el JSON es inválido, `with_retry` reintenta hasta 3 veces.
5. `validar_referencias` descarta cualquier referencia que el modelo haya inventado (que no esté entre los fragmentos recuperados).

La función pedida por la consigna es asíncrona y usa `ainvoke`:

```python
async def get_rag_response(query: str) -> RespuestaRAG:
    return await chain.ainvoke(query)
```

Modelo de la respuesta:

```python
class RespuestaRAG(BaseModel):
    respuesta: str
    encontrada_en_contexto: bool
    referencias: list[Referencia]   # cada una con fuente y fragmento
```

## Cómo ejecutarlo

Requiere Python 3.12 (con 3.14 algunas dependencias todavía no tienen versión compatible).

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env      # pegar la ANTHROPIC_API_KEY en .env

python ingest.py            # crea la base vectorial en ./vectorstore
python demo.py              # corre las pruebas
```

La primera vez se descarga el modelo de embeddings (~470 MB). Si se salta `ingest.py`, `demo.py` crea la base automáticamente.

Para hacer una pregunta propia:

```python
import asyncio
from rag_chain import get_rag_response

print(asyncio.run(get_rag_response("¿Cada cuánto se rotan las claves de API?")))
```

## Pruebas

`demo.py` corre tres preguntas y verifica automáticamente el resultado:

1. **Con respuesta en los documentos**: *"¿Cuáles son las etapas del despliegue canario y cuándo se revierte automáticamente?"* → tiene que responder con los datos de `02_despliegues.md` y citarlo.
2. **Trampa, tema relacionado**: *"¿Cuánto dinero se le paga a un ingeniero por cada semana de guardia?"* → las guardias sí aparecen en `03_incidentes.md`, pero el pago no. El retriever trae fragmentos parecidos, y el modelo tiene que darse cuenta de que el dato no está. Es la trampa más difícil.
3. **Trampa, fuera de tema**: *"¿Quién ganó el Mundial de fútbol de 2022?"* → el modelo lo sabe, pero no está en el contexto, así que tiene que decir "No lo sé.".

### Resultados obtenidos

```text
=== Respuesta en los documentos ===
{
  "respuesta": "Las etapas del despliegue canario son:\n1. La nueva versión recibe el 5% del tráfico durante 30 minutos.\n2. Si las métricas son normales, pasa al 25% durante otros 30 minutos.\n3. Luego pasa al 50% durante 15 minutos.\n4. Finalmente recibe el 100% del tráfico.\n\nEl despliegue se revierte automáticamente en cada etapa si la tasa de errores de la versión nueva supera en más de un 0,5% a la de la versión anterior, o si la latencia del percentil 99 aumenta más de un 20%. Esta reversión ocurre sin intervención humana.",
  "encontrada_en_contexto": true,
  "referencias": [{"fuente": "02_despliegues.md", "fragmento": 1}]
}
Resultado: OK

=== Pregunta trampa (tema relacionado) ===
{"respuesta": "No lo sé.", "encontrada_en_contexto": false, "referencias": []}
Resultado: OK

=== Pregunta trampa (fuera de tema) ===
{"respuesta": "No lo sé.", "encontrada_en_contexto": false, "referencias": []}
Resultado: OK
```

En la pregunta del Mundial, Claude conoce la respuesta (Argentina), pero no la da porque no está en el contexto: el filtro de veracidad funciona.

## Seguridad

La API key se lee de `.env` con `python-dotenv`. `.env` y `vectorstore/` están en `.gitignore`, así que no se suben al repositorio.
