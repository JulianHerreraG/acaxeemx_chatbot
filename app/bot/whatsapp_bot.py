"""
Webhook handler para WhatsApp Business Cloud API (Meta).

ESTADO: INACTIVO — las rutas de este módulo NO están registradas en main.py.
Se activa cuando se gestionen las credenciales Meta Business (System User Token,
número de teléfono registrado como WhatsApp Business).
Ver ADR 0007 D1 para el proceso de activación.

Diferencias con instagram_bot:
  - Payload: entry[0].changes[0].value.messages[0]
  - sender_id: msg["from"] (número de teléfono E.164, ej. "521234567890")
  - El teléfono es a la vez channel_id e identificador del cliente → verified=True inmediato.
  - Envío vía Cloud API: POST /<phone_number_id>/messages
"""

import threading
from collections import deque

import requests
from flask import request

from app.agents.orchestrator import orchestrator
from app.utils.config import Config
from app.utils.logger import setup_logger

logger = setup_logger("whatsapp_bot")

_processed_ids: deque = deque(maxlen=500)


def verify_webhook():
    """Handshake de verificación Meta (GET) — mismo mecanismo que Instagram."""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == Config.META_VERIFY_TOKEN:
        logger.info("Verificación de webhook WhatsApp exitosa")
        return challenge, 200

    logger.warning("Verificación de webhook WhatsApp fallida — token no coincide")
    return "Forbidden", 403


def handle_webhook():
    """Recibe eventos POST de WhatsApp Cloud API. Responde 200 inmediato + hilo."""
    data = request.get_json(silent=True) or {}
    threading.Thread(target=_process_payload, args=(data,), daemon=True).start()
    return "OK", 200


def _process_payload(data: dict) -> None:
    try:
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for msg in value.get("messages", []):
                    if msg.get("type") != "text":
                        continue

                    message_id = msg.get("id")
                    text = msg.get("text", {}).get("body")
                    sender_phone = msg.get("from")

                    if not text or not sender_phone or not message_id:
                        continue

                    if message_id in _processed_ids:
                        logger.debug(f"WhatsApp: mensaje duplicado ignorado id={message_id}")
                        continue
                    _processed_ids.append(message_id)

                    logger.info(f"Mensaje recibido de whatsapp_{sender_phone}: {text[:50]}...")
                    _dispatch(sender_phone, text)

    except Exception as e:
        logger.error(f"Error procesando payload WhatsApp: {e}", exc_info=True)


def _dispatch(sender_phone: str, text: str) -> None:
    try:
        response = orchestrator.process_message("whatsapp", sender_phone, text)
        if response:
            _send_message(sender_phone, response)
    except Exception as e:
        logger.error(f"Error despachando mensaje WhatsApp de whatsapp_{sender_phone}: {e}", exc_info=True)


def _send_message(recipient_phone: str, text: str) -> None:
    """
    Envía un mensaje vía WhatsApp Cloud API.
    Requiere WHATSAPP_PHONE_NUMBER_ID y WHATSAPP_ACCESS_TOKEN en variables de entorno.
    Estas variables aún no están en Config porque el canal está inactivo.
    """
    import os
    phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    access_token = os.getenv("WHATSAPP_ACCESS_TOKEN", "")

    if not phone_number_id or not access_token:
        logger.error("WHATSAPP_PHONE_NUMBER_ID o WHATSAPP_ACCESS_TOKEN no configurados")
        return

    url = f"https://graph.facebook.com/v19.0/{phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient_phone,
        "type": "text",
        "text": {"body": text},
    }
    try:
        resp = requests.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        if resp.ok:
            logger.info(f"Mensaje enviado a whatsapp_{recipient_phone}")
        else:
            logger.error(f"Error enviando mensaje WhatsApp a {recipient_phone}: {resp.status_code} {resp.text}")
    except requests.RequestException as e:
        logger.error(f"Excepción enviando mensaje WhatsApp a {recipient_phone}: {e}")
