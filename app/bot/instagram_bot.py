"""
Webhook handler para Instagram Messaging API (Meta).

Flujo de activación:
  1. En Meta for Developers: configurar webhook apuntando a
     https://<host>/webhook/instagram con verify_token = META_VERIFY_TOKEN.
  2. Meta hace GET de verificación → verify_webhook() responde con hub.challenge.
  3. Desde ese momento, cada mensaje entrante llega como POST → handle_webhook().

Idempotencia (D5 de ADR 0007):
  - El handler responde 200 de inmediato y despacha el procesamiento en un hilo.
  - Un deque en memoria evita procesar el mismo message_id dos veces.
"""

import threading
from collections import deque

import requests
from flask import request

from app.agents.orchestrator import orchestrator
from app.utils.config import Config
from app.utils.logger import setup_logger

logger = setup_logger("instagram_bot")

# Dedupe en memoria — guarda los message_id ya procesados (máx. 500 entradas).
# collections.deque es thread-safe para append/in bajo el GIL de CPython.
_processed_ids: deque = deque(maxlen=500)

_GRAPH_API_URL = "https://graph.facebook.com/v19.0/me/messages"


def verify_webhook():
    """
    Responde al handshake de verificación inicial de Meta (GET).
    Meta envía hub.mode='subscribe', hub.verify_token y hub.challenge.
    Si el token coincide con META_VERIFY_TOKEN, respondemos con hub.challenge.
    """
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == Config.META_VERIFY_TOKEN:
        logger.info("Verificación de webhook Instagram exitosa")
        return challenge, 200

    logger.warning("Verificación de webhook Instagram fallida — token no coincide")
    return "Forbidden", 403


def handle_webhook():
    """
    Recibe eventos POST de Instagram Messaging API.
    Responde 200 de inmediato y procesa el payload en un hilo separado.
    """
    data = request.get_json(silent=True) or {}
    threading.Thread(target=_process_payload, args=(data,), daemon=True).start()
    return "OK", 200


def _process_payload(data: dict) -> None:
    try:
        for entry in data.get("entry", []):
            for messaging in entry.get("messaging", []):
                msg = messaging.get("message", {})
                message_id = msg.get("mid")
                text = msg.get("text")
                sender_id = messaging.get("sender", {}).get("id")

                # Ignorar eventos que no sean mensajes de texto
                if not text or not sender_id or not message_id:
                    continue

                # D5: dedupe — ignorar si ya procesamos este message_id
                if message_id in _processed_ids:
                    logger.debug(f"Instagram: mensaje duplicado ignorado mid={message_id}")
                    continue
                _processed_ids.append(message_id)

                logger.info(f"Mensaje recibido de instagram_{sender_id}: {text[:50]}...")
                _dispatch(sender_id, text)

    except Exception as e:
        logger.error(f"Error procesando payload Instagram: {e}", exc_info=True)


def _dispatch(sender_id: str, text: str) -> None:
    try:
        response = orchestrator.process_message("instagram", sender_id, text)
        if response:
            _send_message(sender_id, response)
    except Exception as e:
        logger.error(f"Error despachando mensaje Instagram de instagram_{sender_id}: {e}", exc_info=True)


def _send_message(recipient_id: str, text: str) -> None:
    """Envía un mensaje de texto al usuario vía Instagram Messaging API."""
    token = Config.INSTAGRAM_PAGE_ACCESS_TOKEN
    if not token:
        logger.error("INSTAGRAM_PAGE_ACCESS_TOKEN no configurado — no se puede enviar mensaje")
        return

    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text},
    }
    try:
        resp = requests.post(
            _GRAPH_API_URL,
            json=payload,
            params={"access_token": token},
            timeout=10,
        )
        if resp.ok:
            logger.info(f"Mensaje enviado a instagram_{recipient_id}")
        else:
            logger.error(f"Error enviando mensaje Instagram a {recipient_id}: {resp.status_code} {resp.text}")
    except requests.RequestException as e:
        logger.error(f"Excepción enviando mensaje Instagram a {recipient_id}: {e}")
