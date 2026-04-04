import threading
import time
from datetime import datetime, timedelta
import pytz
import schedule
from app.repositories.conversation_repo import conversation_repo
from app.utils.config import Config
from app.utils.logger import setup_logger

logger = setup_logger("cleanup")


def cleanup_old_conversations():
    """Elimina conversaciones del dia anterior."""
    tz = pytz.timezone(Config.TIMEZONE)
    yesterday = datetime.now(tz) - timedelta(days=1)
    date_str = yesterday.strftime("%Y-%m-%d")

    logger.info(f"Ejecutando limpieza de conversaciones: {date_str}")
    try:
        conversation_repo.delete_all_for_date(date_str)
        logger.info(f"Limpieza completada para {date_str}")
    except Exception as e:
        logger.error(f"Error en limpieza de conversaciones: {e}", exc_info=True)


def _run_scheduler():
    """Loop del scheduler en hilo de fondo."""
    while True:
        schedule.run_pending()
        time.sleep(60)


def start_cleanup_scheduler():
    """Programa la limpieza diaria a las 3:00 AM hora Sinaloa."""
    schedule.every().day.at("03:00").do(cleanup_old_conversations)
    logger.info("Scheduler de limpieza programado para las 3:00 AM (America/Mazatlan)")

    thread = threading.Thread(target=_run_scheduler, daemon=True)
    thread.start()
