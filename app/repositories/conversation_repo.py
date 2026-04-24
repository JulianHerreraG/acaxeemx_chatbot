from firebase_admin import firestore
from app.repositories.firebase_client import get_firestore_client
from app.utils.config import Config
from app.utils.logger import setup_logger

logger = setup_logger("conversation_repo")

COL = "conversations"


class ConversationRepo:

    def save_turn(self, chat_id: str, role: str, content: str) -> None:
        """
        Guarda un turno en la subcolleccion messages y actualiza el documento
        padre de la conversacion (lastMessage, lastMessageAt).

        IMPORTANTE: no sobreescribir campos de control (isAdminMode/adminUid),
        ya que los administra el panel web para tomar/devolver control.
        """
        db = get_firestore_client()
        conv_ref = db.collection(COL).document(chat_id)
        messages_ref = conv_ref.collection("messages")

        # Escribir el mensaje en la subcolleccion
        messages_ref.add({
            "role": role,
            "content": content,
            "source": "llm" if role == "assistant" else "user",
            "timestamp": firestore.SERVER_TIMESTAMP,
        })

        # Actualizar / crear el documento padre sin tocar flags de control admin.
        conv_ref.set(
            {
                "lastMessage": content,
                "lastMessageAt": firestore.SERVER_TIMESTAMP,
            },
            merge=True,
        )
        logger.debug(f"Turno guardado: chat={chat_id}, role={role}")

    def get_history(self, chat_id: str) -> list[dict]:
        """
        Retorna el historial de la conversacion como lista de {role, content}.
        Limitado a MAX_CONVERSATION_HISTORY mensajes mas recientes.
        """
        db = get_firestore_client()
        messages_ref = (
            db.collection(COL)
            .document(chat_id)
            .collection("messages")
        )
        # Ordenar por timestamp; limitar a MAX*2 para tener margen antes de truncar
        docs = (
            messages_ref
            .order_by("timestamp")
            .limit_to_last(Config.MAX_CONVERSATION_HISTORY)
            .get()
        )
        return [
            {"role": doc.to_dict()["role"], "content": doc.to_dict()["content"]}
            for doc in docs
        ]

    def is_admin_mode(self, chat_id: str) -> bool:
        """
        Retorna True si la conversacion esta en modo admin (bot silenciado).
        Si el documento no existe, retorna False.
        """
        db = get_firestore_client()
        doc = db.collection(COL).document(chat_id).get()
        if not doc.exists:
            return False
        return bool(doc.to_dict().get("isAdminMode", False))

    def mark_needs_human(self, chat_id: str) -> None:
        """
        Marca que la conversacion requiere atencion de un asesor humano.
        El panel web lo mostrara como alerta en el monitor del bot.
        """
        db = get_firestore_client()
        db.collection(COL).document(chat_id).set(
            {"needsHuman": True},
            merge=True,
        )
        logger.info(f"Conversacion {chat_id} marcada como needsHuman=True")

    def delete_all_for_date(self, date_str: str) -> None:
        """
        Elimina mensajes de conversaciones cuyo lastMessageAt sea anterior a
        date_str. Reemplaza la logica de borrado por ruta de RTDB.
        Se llama desde el scheduler de limpieza diaria.
        """
        import datetime
        import pytz

        tz = pytz.timezone(Config.TIMEZONE)
        cutoff = tz.localize(datetime.datetime.strptime(date_str, "%Y-%m-%d"))

        db = get_firestore_client()
        conversations = db.collection(COL).stream()

        deleted_total = 0
        for conv in conversations:
            data = conv.to_dict()
            last_at = data.get("lastMessageAt")
            # Saltear conversaciones sin actividad registrada o recientes
            if last_at is None:
                continue
            # Firestore timestamps son objetos con atributo .replace()
            try:
                last_dt = last_at.astimezone(tz) if hasattr(last_at, "astimezone") else None
            except Exception:
                last_dt = None

            if last_dt is None or last_dt >= cutoff:
                continue

            # Borrar mensajes de esta conversacion vieja
            msgs_ref = db.collection(COL).document(conv.id).collection("messages")
            old_msgs = list(msgs_ref.stream())
            if not old_msgs:
                continue

            batch = db.batch()
            for msg in old_msgs:
                batch.delete(msg.reference)
            batch.commit()
            deleted_total += len(old_msgs)
            logger.info(
                f"Limpieza: {len(old_msgs)} mensajes borrados de conversacion {conv.id}"
            )

        logger.info(f"Limpieza completada. Total mensajes borrados: {deleted_total}")


conversation_repo = ConversationRepo()
