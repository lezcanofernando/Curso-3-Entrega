from pydantic import BaseModel, Field


class RespuestaRAG(BaseModel):
    """Forma que debe tener la respuesta del modelo."""

    respuesta: str = Field(
        description='Respuesta a la pregunta, en español. Si no está en el contexto: "No lo sé."',
    )
    referencias: list[str] = Field(
        description="Nombres de los archivos usados para responder. Vacía si la respuesta es 'No lo sé.'",
    )
