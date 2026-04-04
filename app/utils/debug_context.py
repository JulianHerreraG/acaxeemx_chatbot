"""
Helper para visualizar el contexto completo del LLM.

Importa en orchestrator.py para ver todos los mensajes enviados al modelo.
"""

import json
from app.utils.logger import setup_logger

logger = setup_logger("debug_context")


def log_llm_context(messages: list[dict], chat_id: str = ""):
    """
    Imprime el contexto completo enviado al LLM de forma legible.

    Uso:
        from app.utils.debug_context import log_llm_context
        log_llm_context(messages, chat_id)
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"CONTEXTO COMPLETO DEL LLM - Chat: {chat_id}")
    logger.info(f"{'='*80}")
    logger.info(f"Total de mensajes: {len(messages)}\n")

    for i, msg in enumerate(messages):
        role = msg.get("role", "unknown").upper()
        content = msg.get("content", "")

        # Limitar longitud para legibilidad
        if len(content) > 500:
            preview = content[:500] + f"\n... [({len(content) - 500} caracteres mas)]"
        else:
            preview = content

        logger.info(f"\n--- Mensaje [{i}] - Role: {role} ---")
        logger.info(preview)

    logger.info(f"\n{'='*80}\n")


def log_llm_response(raw_response: str):
    """Imprime la respuesta JSON del LLM de forma formateada."""
    logger.info("\n" + "="*80)
    logger.info("RESPUESTA DEL LLM (JSON)")
    logger.info("="*80)
    try:
        parsed = json.loads(raw_response)
        logger.info(json.dumps(parsed, indent=2, ensure_ascii=False))
    except json.JSONDecodeError:
        logger.info(raw_response)
    logger.info("="*80 + "\n")
