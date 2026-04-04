import time
from app.repositories.firebase_client import get_db_reference
from app.utils.datetime_helper import get_today_date_str
from app.utils.config import Config
from app.utils.logger import setup_logger

logger = setup_logger("conversation_repo")


class ConversationRepo:
    def save_turn(self, chat_id: str, role: str, content: str):
        date_str = get_today_date_str()
        ref = get_db_reference(f"/conversaciones/{date_str}/{chat_id}/mensajes")
        ref.push({
            "role": role,
            "content": content,
            "timestamp": int(time.time() * 1000),
        })
        logger.info(f"Turno guardado: chat={chat_id}, role={role}")

    def get_history(self, chat_id: str) -> list[dict]:
        date_str = get_today_date_str()
        ref = get_db_reference(f"/conversaciones/{date_str}/{chat_id}/mensajes")
        data = ref.get()

        if not data:
            return []

        messages = []
        for key in data:
            item = data[key]
            messages.append({
                "role": item["role"],
                "content": item["content"],
            })

        # Limitar al maximo configurado
        return messages[-Config.MAX_CONVERSATION_HISTORY:]

    def delete_all_for_date(self, date_str: str):
        ref = get_db_reference(f"/conversaciones/{date_str}")
        ref.delete()
        logger.info(f"Conversaciones eliminadas para fecha: {date_str}")


conversation_repo = ConversationRepo()
