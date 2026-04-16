import time
import telebot
from app.utils.config import Config
from app.agents.orchestrator import orchestrator
from app.utils.logger import setup_logger
from app.utils.instance_lock import InstanceLock
from app.utils.shutdown_handler import shutdown_handler

logger = setup_logger("telegram_bot")

bot = telebot.TeleBot(Config.TELEGRAM_API_KEY)
instance_lock = InstanceLock(lock_path="/bot_lock")
shutdown_handler.set_bot_instance(bot)


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = str(message.chat.id)
    user_text = message.text or ""

    logger.info(f"Mensaje recibido de {chat_id}: {user_text[:50]}...")

    try:
        response = orchestrator.process_message(chat_id, user_text)
        # response es None cuando la conversacion esta en modo admin (bot silenciado)
        if response is not None:
            bot.reply_to(message, response)
    except Exception as e:
        logger.error(f"Error manejando mensaje de {chat_id}: {e}", exc_info=True)
        bot.reply_to(message, "Lo siento, ocurrió un error. Por favor intenta de nuevo.")


def start_bot():
    """Inicia el bot asegurando que solo una instancia esté activa."""
    logger.info("Bot de Telegram intentando adquirir lock...")

    # Adquirir lock
    if not instance_lock.acquire(timeout=60):
        logger.error("No se pudo adquirir el lock del bot. Abortando inicio.")
        return

    try:
        logger.info(f"Bot activo (instancia: {instance_lock.instance_id})")

        # Refrescar lock periodicamente mientras el bot corre
        class LockRefresher(telebot.BaseMiddleware):
            def __init__(self, lock_obj, shutdown_handler_obj):
                super().__init__()
                self.lock_obj = lock_obj
                self.shutdown_handler = shutdown_handler_obj

            def pre_process(self, message, data):
                # Intentar refrescar el lock
                if not self.lock_obj.refresh():
                    # Perdio el lock - otra instancia lo tomo
                    logger.error("DETECTADO: Otra instancia tomo el lock. Iniciando shutdown...")
                    self.shutdown_handler.shutdown("Otra instancia detectada - Lock perdido")

        bot.setup_middleware(LockRefresher(instance_lock, shutdown_handler))

        # Iniciar polling bloqueante
        bot.infinity_polling()

    except KeyboardInterrupt:
        logger.info("Bot interrumpido por el usuario")
    except Exception as e:
        logger.error(f"Error fatal en el bot: {e}", exc_info=True)
    finally:
        # Siempre liberar el lock al salir
        instance_lock.release()
        logger.info("Bot detenido. Lock liberado.")
