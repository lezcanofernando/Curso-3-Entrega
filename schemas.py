from pydantic import BaseModel, Field


class Referencia(BaseModel):
    """Fragmento de un documento que se usó para responder."""

    fuente: str = Field(description="Nombre del archivo, tal como aparece en el contexto.")
    fragmento: int = Field(description="Número de fragmento, tal como aparece en el contexto.")


class RespuestaRAG(BaseModel):
    """Forma que debe tener la respuesta del modelo."""

    respuesta: str = Field(
        description='Respuesta a la pregunta, en español. Si no está en el contexto: "No lo sé."',
    )
    encontrada_en_contexto: bool = Field(
        description="true si la respuesta está en el contexto; false si no.",
    )
    referencias: list[Referencia] = Field(
        default_factory=list,
        description="Fragmentos usados para responder. Vacía si la respuesta no está en el contexto.",
    )
