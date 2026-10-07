"""Pruebas: una pregunta con respuesta en los documentos y dos preguntas trampa."""

import asyncio

from rag_chain import get_rag_response

preguntas = [
    # 1. La respuesta está en 01_recepcion_mercaderia.md.
    "¿Qué hago si llega un camión de lácteos a más de 8 °C?",
    # 2. Trampa: el documento de personal existe, pero no dice nada de sueldos.
    "¿Cuánto cobra un repositor por mes?",
    # 3. Trampa: no tiene nada que ver con los documentos.
    "¿Quién ganó el Mundial de fútbol de 2022?",
]


async def main():
    for pregunta in preguntas:
        resultado = await get_rag_response(pregunta)
        print(f"\nPregunta: {pregunta}")
        print(resultado.model_dump_json(indent=2))


asyncio.run(main())
