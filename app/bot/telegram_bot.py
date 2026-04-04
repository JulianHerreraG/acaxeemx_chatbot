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

    logger.info(f"Mensaje recibido de {chat_id}: {user_text[:50]}...")

    try:
        response = orchestrator.process_message(chat_id, user_text)
        bot.reply_to(message, response)
    except Exception as e:
        logger.error(f"Error manejando mensaje de {chat_id}: {e}", exc_info=True)
        bot.reply_to(message, "Lo siento, ocurrió un error. Por favor intenta de nuevo.")


def start_bot():
    logger.info("Iniciando bot de Telegram...")
    bot.infinity_polling()
