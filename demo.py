"""Pruebas del sistema: una pregunta con respuesta en los documentos y dos preguntas trampa."""

import asyncio
import logging

from rag_chain import get_rag_response

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
# Silenciamos los logs de las librerías para que se lea mejor la salida.
for nombre in ("httpx", "sentence_transformers", "chromadb"):
    logging.getLogger(nombre).setLevel(logging.WARNING)

pruebas = [
    # 1. La respuesta está en 02_despliegues.md.
    ("Respuesta en los documentos",
     "¿Cuáles son las etapas del despliegue canario y cuándo se revierte automáticamente?"),
    # 2. Trampa: el tema (guardias) sí está en los documentos, pero el dato no.
    ("Pregunta trampa (tema relacionado)",
     "¿Cuánto dinero se le paga a un ingeniero por cada semana de guardia?"),
    # 3. Trampa: nada que ver con los documentos.
    ("Pregunta trampa (fuera de tema)",
     "¿Quién ganó el Mundial de fútbol de 2022?"),
]


async def main():
    for titulo, pregunta in pruebas:
        resultado = await get_rag_response(pregunta)
        print(f"\n=== {titulo} ===\nPregunta: {pregunta}")
        print(resultado.model_dump_json(indent=2))

        # Verificación automática: las trampas tienen que responder "No lo sé" sin referencias.
        if "trampa" in titulo:
            ok = not resultado.encontrada_en_contexto and not resultado.referencias
        else:
            ok = resultado.encontrada_en_contexto and bool(resultado.referencias)
        print("Resultado:", "OK" if ok else "FALLÓ")


asyncio.run(main())
