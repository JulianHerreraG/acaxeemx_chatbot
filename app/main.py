"""
Punto de entrada principal del chatbot Acaxeemx.

Ejecutar con:
    python -m app.main
"""

import threading
import time
from datetime import datetime
from flask import Flask
from app.utils.logger import setup_logger
from app.repositories.firebase_client import init_firebase
from app.tasks.cleanup import start_cleanup_scheduler
from app.bot.telegram_bot import start_bot
from app.utils.shutdown_handler import shutdown_handler

logger = setup_logger("main")

app = Flask(__name__)
shutdown_handler.set_flask_app(app)


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
    flask_thread = threading.Thread(
        target=app.run,
        kwargs={"host": "0.0.0.0", "port": 5000, "debug": False},
        daemon=True,
    )
    flask_thread.start()
    logger.info("Flask corriendo en puerto 5000")

    # Pequeña pausa para asegurar que Flask inicio correctamente
    time.sleep(1)

    # Iniciar bot de Telegram (bloqueante)
    # Cuando start_bot() retorne, significa que el bot se detuvo
    start_bot()

    # Si llegamos aqui, el bot se detuvo (por loss de lock o error)
    logger.info("Bot detenido. Finalizando aplicacion...")


if __name__ == "__main__":
    main()
