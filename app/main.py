"""
Punto de entrada principal del chatbot Acaxeemx.

Ejecutar con:
    python -m app.main
"""

from app.utils.logger import setup_logger
from app.repositories.firebase_client import init_firebase
from app.tasks.cleanup import start_cleanup_scheduler
from app.bot.telegram_bot import start_bot

logger = setup_logger("main")


def main():
    logger.info("=== Iniciando Chatbot Acaxeemx ===")

    # Inicializar Firebase
    init_firebase()

    # Iniciar scheduler de limpieza (3 AM diario)
    start_cleanup_scheduler()

    # Iniciar bot de Telegram (bloqueante)
    start_bot()


if __name__ == "__main__":
    main()
