import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Requeridos
    GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
    TELEGRAM_API_KEY = os.environ["TELEGRAM_API_KEY"]

    # Opcional (fallback LLM)
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

    # Obsoleto (RTDB). Se mantiene como opcional para no romper entornos
    # que aun tengan la variable definida. Eliminable una vez confirmada la
    # migracion a Firestore.
    FIREBASE_DATABASE_URL = os.getenv("FIREBASE_DATABASE_URL", "")

    # Firebase credentials (JSON completo como string en variable de entorno)
    FIREBASE_CREDENTIALS_JSON = os.environ["FIREBASE_CREDENTIALS_JSON"]
    LLM_MODEL = os.getenv("LLM_MODEL", "claude-sonnet-4-6")
    LLM_AUX_MODEL = os.getenv("LLM_AUX_MODEL", "gpt-4o-mini")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://models.inference.ai.azure.com")
    RESTAURANT_NAME = os.getenv("RESTAURANT_NAME", "Acaxeemx")
    TIMEZONE = os.getenv("TIMEZONE", "America/Mazatlan")
    MAX_CONVERSATION_HISTORY = int(os.getenv("MAX_CONVERSATION_HISTORY", "20"))
    LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "3"))

    # Horarios de apertura (formato 24h)
    RESTAURANT_OPEN_HOUR = int(os.getenv("RESTAURANT_OPEN_HOUR", "14"))          # 2:00 PM
    RESTAURANT_OPEN_MINUTE = int(os.getenv("RESTAURANT_OPEN_MINUTE", "0"))
    RESTAURANT_CLOSE_HOUR = int(os.getenv("RESTAURANT_CLOSE_HOUR", "22"))         # 10:00 PM
    RESTAURANT_LAST_RESERVATION_HOUR = int(os.getenv("RESTAURANT_LAST_RESERVATION_HOUR", "20"))    # 8:30 PM
    RESTAURANT_LAST_RESERVATION_MINUTE = int(os.getenv("RESTAURANT_LAST_RESERVATION_MINUTE", "30"))

    # Ventana de ocupación por reserva (minutos). Dos reservas en la misma
    # mesa tienen conflicto si |T_nueva - T_existente| < MIN_STAY_MINUTES.
    MIN_STAY_MINUTES = int(os.getenv("MIN_STAY_MINUTES", "59"))
