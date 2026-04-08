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


def hora_to_minutes(hora: str) -> int:
    """
    Convierte una hora en formato 'HH:MM' a minutos desde medianoche.
    Acepta también 'HH' (asume :00) y formatos 12h como '2:00 PM'.
    """
    hora_clean = hora.strip().upper()
    is_pm = "PM" in hora_clean
    is_am = "AM" in hora_clean
    hora_clean = hora_clean.replace("PM", "").replace("AM", "").strip()

    if ":" in hora_clean:
        parts = hora_clean.split(":")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
    else:
        hour = int(hora_clean)
        minute = 0

    if is_pm and hour != 12:
        hour += 12
    elif is_am and hour == 12:
        hour = 0

    return hour * 60 + minute


def is_valid_reservation_hour(hora: str) -> bool:
    """
    Valida que la hora esté dentro del horario de reservaciones permitido.
    Rango válido: OPEN_HOUR:OPEN_MINUTE – LAST_RESERVATION_HOUR:LAST_RESERVATION_MINUTE
    """
    try:
        total = hora_to_minutes(hora)
        open_total = Config.RESTAURANT_OPEN_HOUR * 60 + Config.RESTAURANT_OPEN_MINUTE
        last_total = Config.RESTAURANT_LAST_RESERVATION_HOUR * 60 + Config.RESTAURANT_LAST_RESERVATION_MINUTE
        return open_total <= total <= last_total
    except (ValueError, IndexError):
        return False
