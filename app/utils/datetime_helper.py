from datetime import datetime
import pytz
from app.utils.config import Config


def get_current_datetime() -> dict:
    tz = pytz.timezone(Config.TIMEZONE)
    now = datetime.now(tz)
    return {
        "Hora": now.strftime("%H:%M"),
        "fecha": now.strftime("%Y-%m-%d"),
    }


def get_today_date_str() -> str:
    tz = pytz.timezone(Config.TIMEZONE)
    return datetime.now(tz).strftime("%Y-%m-%d")


def is_valid_reservation_hour(hora: str) -> bool:
    """
    Valida que la hora esté dentro del horario de reservaciones permitido.
    Acepta formatos: "14:00", "14", "2:00 PM", etc.
    Retorna True si es válida (entre OPEN_HOUR y LAST_RESERVATION_HOUR).
    """
    try:
        # Normalizar: extraer la hora entera
        hora_clean = hora.strip().upper()

        # Intentar parsear como HH:MM
        if ":" in hora_clean:
            parts = hora_clean.replace("PM", "").replace("AM", "").strip().split(":")
            hour = int(parts[0])
            # Ajustar si viene en formato 12h
            if "PM" in hora.upper() and hour != 12:
                hour += 12
            elif "AM" in hora.upper() and hour == 12:
                hour = 0
        else:
            hour = int(hora_clean.replace("PM", "").replace("AM", "").strip())
            if "PM" in hora.upper() and hour != 12:
                hour += 12

        return Config.RESTAURANT_OPEN_HOUR <= hour <= Config.RESTAURANT_LAST_RESERVATION_HOUR

    except (ValueError, IndexError):
        return False
