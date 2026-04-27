import telebot
from app.utils.config import Config
from app.agents.orchestrator import orchestrator
from app.utils.logger import setup_logger

logger = setup_logger("telegram_bot")

bot = telebot.TeleBot(Config.TELEGRAM_API_KEY)


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = str(message.chat.id)
    user_text = message.text or ""

    logger.info(f"Mensaje recibido de telegram_{chat_id}: {user_text[:50]}...")

    try:
        response = orchestrator.process_message("telegram", chat_id, user_text)
        # response es None cuando la conversacion esta en modo admin (bot silenciado)
        if response is not None:
            bot.reply_to(message, response)
    except Exception as e:
        logger.error(f"Error manejando mensaje de telegram_{chat_id}: {e}", exc_info=True)
        bot.reply_to(message, "Lo siento, ocurrió un error. Por favor intenta de nuevo.")


def process_update(update_json: dict) -> None:
    """Procesa un update de Telegram recibido vía webhook."""
    update = telebot.types.Update.de_json(update_json)
    bot.process_new_updates([update])


def setup_webhook(webhook_url: str) -> None:
    """
    Registra el webhook de Telegram al arrancar el servidor.
    webhook_url debe ser la URL completa del endpoint, ej.:
      https://acaxee-bot.onrender.com/webhook/telegram
    """
    secret = Config.TELEGRAM_WEBHOOK_SECRET
    if secret:
        bot.set_webhook(url=webhook_url, secret_token=secret)
    else:
        bot.set_webhook(url=webhook_url)
    logger.info(f"Telegram webhook configurado: {webhook_url}")
