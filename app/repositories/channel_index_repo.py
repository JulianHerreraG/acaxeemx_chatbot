from firebase_admin import firestore
from app.repositories.firebase_client import get_firestore_client
from app.utils.logger import setup_logger

logger = setup_logger("channel_index_repo")

COL = "channel_index"


class ChannelIndexRepo:

    def _key(self, platform: str, channel_id: str) -> str:
        return f"{platform}_{channel_id}"

    def get(self, platform: str, channel_id: str) -> dict | None:
        """
        Retorna el documento de channel_index para (platform, channel_id), o None si no existe.
        """
        db = get_firestore_client()
        doc = db.collection(COL).document(self._key(platform, channel_id)).get()
        return doc.to_dict() if doc.exists else None

    def create_unverified(self, platform: str, channel_id: str) -> None:
        """
        Registra el primer contacto de un canal Telegram o Instagram.
        verified=False — la identidad queda confirmada hasta que el panel web
        cierre la primera reserva de este canal.
        Idempotente: no sobreescribe si el documento ya existe.
        """
        db = get_firestore_client()
        ref = db.collection(COL).document(self._key(platform, channel_id))
        if ref.get().exists:
            return
        ref.set({
            "platform": platform,
            "channel_id": channel_id,
            "phone": None,
            "pending_phone": None,
            "verified": False,
            "created_at": firestore.SERVER_TIMESTAMP,
            "verified_at": None,
        })
        logger.info(f"channel_index creado (no verificado): {platform}_{channel_id}")

    def create_verified(self, platform: str, channel_id: str, phone: str) -> None:
        """
        Registra el primer contacto de un canal WhatsApp.
        El teléfono está disponible desde el primer mensaje (campo 'from' del webhook de Meta),
        por lo que verified=True de inmediato.
        Idempotente: no sobreescribe si ya está verificado.
        """
        db = get_firestore_client()
        ref = db.collection(COL).document(self._key(platform, channel_id))
        doc = ref.get()
        if doc.exists and doc.to_dict().get("verified"):
            return
        ref.set({
            "platform": platform,
            "channel_id": channel_id,
            "phone": phone,
            "pending_phone": None,
            "verified": True,
            "created_at": firestore.SERVER_TIMESTAMP,
            "verified_at": firestore.SERVER_TIMESTAMP,
        })
        logger.info(f"channel_index creado (verificado): {platform}_{channel_id} → {phone}")

    def set_pending_phone(self, platform: str, channel_id: str, phone: str) -> None:
        """
        Guarda el teléfono que el cliente entregó al hacer una reserva desde Telegram o Instagram.
        No toca customers/{phone} — la vinculación ocurre cuando el panel web cierra la reserva.
        No hace nada si el canal ya está verificado (la identidad ya está confirmada).
        """
        db = get_firestore_client()
        ref = db.collection(COL).document(self._key(platform, channel_id))
        doc = ref.get()
        if not doc.exists:
            logger.warning(
                f"set_pending_phone: no hay channel_index para {platform}_{channel_id}; "
                "el canal debió registrarse al primer contacto"
            )
            return
        if doc.to_dict().get("verified"):
            return
        ref.update({"pending_phone": phone})
        logger.info(f"pending_phone registrado: {platform}_{channel_id} → {phone}")


channel_index_repo = ChannelIndexRepo()
