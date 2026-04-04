"""
Gestor de shutdown para detener Flask y el bot de Telegram.
"""

import os
import sys
import signal
from app.utils.logger import setup_logger

logger = setup_logger("shutdown_handler")


class ShutdownHandler:
    def __init__(self):
        self.flask_app = None
        self.bot_instance = None

    def set_flask_app(self, app):
        """Registra la instancia de Flask para poder detenerla."""
        self.flask_app = app

    def set_bot_instance(self, bot):
        """Registra la instancia del bot para poder detenerla."""
        self.bot_instance = bot

    def shutdown(self, reason: str = "Unknown"):
        """
        Detiene Flask y el bot, y termina el proceso.

        Uso:
            shutdown_handler.shutdown("Lock perdido")
        """
        logger.warning(f"=== INICIANDO SHUTDOWN: {reason} ===")

        # Detener bot
        if self.bot_instance:
            try:
                logger.info("Deteniendo bot de Telegram...")
                self.bot_instance.stop_polling()
                logger.info("Bot detenido")
            except Exception as e:
                logger.error(f"Error deteniendo bot: {e}")

        # Detener Flask (enviar SIGTERM a si mismo para salir del thread)
        if self.flask_app:
            try:
                logger.info("Deteniendo servidor Flask...")
                # Enviar señal para detener el thread de Flask
                os.kill(os.getpid(), signal.SIGTERM)
            except Exception as e:
                logger.error(f"Error deteniendo Flask: {e}")

        logger.warning("=== SHUTDOWN COMPLETADO ===")
        sys.exit(0)


shutdown_handler = ShutdownHandler()
