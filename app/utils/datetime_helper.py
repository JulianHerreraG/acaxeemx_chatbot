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
