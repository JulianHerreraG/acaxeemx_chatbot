"""
Punto de entrada principal del chatbot Acaxeemx.

Ejecutar con:
    python -m app.main

En producción (Render/Railway), el servidor de WSGI (Gunicorn) puede arrancar
directamente apuntando al objeto `app` de este módulo:
    gunicorn app.main:app
"""

import os
from datetime import datetime
from flask import Flask, request

from app.utils.logger import setup_logger
from app.repositories.firebase_client import init_firebase
from app.tasks.cleanup import start_cleanup_scheduler
from app.bot import telegram_bot, instagram_bot
from app.utils.config import Config

# WhatsApp importado pero sus rutas NO están registradas (canal inactivo).
# Descomentar las rutas de abajo cuando se gestionen las credenciales Meta Business.
# from app.bot import whatsapp_bot

logger = setup_logger("main")

app = Flask(__name__)


# ── Health check ─────────────────────────────────────────────────────────────

@app.route("/")
def home():
    return f"Bot corriendo correctamente - {datetime.now()}"


# ── Telegram webhook ──────────────────────────────────────────────────────────

@app.route("/webhook/telegram", methods=["POST"])
def telegram_webhook():
    # Verificar secret token si está configurado (D5, seguridad)
    secret = Config.TELEGRAM_WEBHOOK_SECRET
    if secret:
        incoming = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if incoming != secret:
            logger.warning("Telegram webhook: secret token inválido")
            return "Forbidden", 403

    update_json = request.get_json(silent=True) or {}
    telegram_bot.process_update(update_json)
    return "OK", 200


# ── Instagram webhook ─────────────────────────────────────────────────────────

@app.route("/webhook/instagram", methods=["GET"])
def instagram_verify():
    return instagram_bot.verify_webhook()


@app.route("/webhook/instagram", methods=["POST"])
def instagram_webhook():
    return instagram_bot.handle_webhook()


# ── WhatsApp webhook (INACTIVO) ───────────────────────────────────────────────
# Descomentar cuando se activen las credenciales Meta Business (ADR 0007 D1).
#
# @app.route("/webhook/whatsapp", methods=["GET"])
# def whatsapp_verify():
#     return whatsapp_bot.verify_webhook()
#
# @app.route("/webhook/whatsapp", methods=["POST"])
# def whatsapp_webhook():
#     return whatsapp_bot.handle_webhook()


# ── Startup ───────────────────────────────────────────────────────────────────

def main():
    logger.info("=== Iniciando Chatbot Acaxeemx ===")

    # Inicializar Firebase
    init_firebase()

    # Iniciar scheduler de limpieza (3 AM diario) en hilo de fondo
    start_cleanup_scheduler()

    # Configurar webhook de Telegram si la URL pública está definida
    webhook_url = Config.TELEGRAM_WEBHOOK_URL
    if webhook_url:
        full_url = f"{webhook_url.rstrip('/')}/webhook/telegram"
        telegram_bot.setup_webhook(full_url)
    else:
        logger.warning(
            "TELEGRAM_WEBHOOK_URL no definida — webhook de Telegram no configurado. "
            "El bot no recibirá mensajes de Telegram hasta que se defina esta variable."
        )

    # Flask como proceso principal (recibe todos los webhooks)
    port = int(os.getenv("PORT", "5000"))
    logger.info(f"Iniciando Flask en puerto {port}")
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    main()
