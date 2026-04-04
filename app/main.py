"""
Punto de entrada principal del chatbot Acaxeemx.

Ejecutar con:
    python -m app.main
"""

import threading
from datetime import datetime
from flask import Flask
from app.utils.logger import setup_logger
from app.repositories.firebase_client import init_firebase
from app.tasks.cleanup import start_cleanup_scheduler
from app.bot.telegram_bot import start_bot

logger = setup_logger("main")

app = Flask(__name__)


@app.route("/")
def home():
    return f"Bot corriendo correctamente - {datetime.now()}"


def main():
    logger.info("=== Iniciando Chatbot Acaxeemx ===")

    # Inicializar Firebase
    init_firebase()

    # Iniciar scheduler de limpieza (3 AM diario)
    start_cleanup_scheduler()

    # Iniciar Flask en hilo de fondo (health check)
    threading.Thread(
        target=app.run,
        kwargs={"host": "0.0.0.0", "port": 5000},
        daemon=True,
    ).start()
    logger.info("Flask corriendo en puerto 5000")

    # Iniciar bot de Telegram (bloqueante)
    start_bot()


if __name__ == "__main__":
    main()
