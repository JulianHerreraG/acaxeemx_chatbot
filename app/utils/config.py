import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Requeridos
    GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
    TELEGRAM_API_KEY = os.environ["TELEGRAM_API_KEY"]
    FIREBASE_DATABASE_URL = os.environ["FIREBASE_DATABASE_URL"]

    # Con defaults
    FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH", "firebase_conection.json")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://models.inference.ai.azure.com")
    RESTAURANT_NAME = os.getenv("RESTAURANT_NAME", "Acaxeemx")
    TIMEZONE = os.getenv("TIMEZONE", "America/Mazatlan")
    MAX_RESERVATIONS_PER_HOUR = int(os.getenv("MAX_RESERVATIONS_PER_HOUR", "10"))
    MAX_CONVERSATION_HISTORY = int(os.getenv("MAX_CONVERSATION_HISTORY", "20"))
    LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "3"))

    # Horarios de apertura (hora entera, formato 24h)
    RESTAURANT_OPEN_HOUR = int(os.getenv("RESTAURANT_OPEN_HOUR", "14"))   # 2:00 PM
    RESTAURANT_CLOSE_HOUR = int(os.getenv("RESTAURANT_CLOSE_HOUR", "22"))  # 10:00 PM
    RESTAURANT_LAST_RESERVATION_HOUR = int(os.getenv("RESTAURANT_LAST_RESERVATION_HOUR", "21"))  # última reserva 9:00 PM
