from firebase_admin import firestore
from app.repositories.firebase_client import get_firestore_client
from app.utils.logger import setup_logger

logger = setup_logger("customer_repo")

COL = "customers"

# Campos de lista de IDs por canal (append-only, según ADR 0006).
# WhatsApp no tiene lista propia: su channel_id ES el teléfono (doc ID).
_CHANNEL_IDS_FIELD = {
    "telegram": "telegramIds",
    "instagram": "instagramIds",
}


class CustomerRepo:

    def get(self, phone: str) -> dict | None:
        """
        Retorna el perfil del cliente por teléfono (document ID = phone, ADR 0007 D2).
        Retorna None si no existe.
        """
        db = get_firestore_client()
        doc = db.collection(COL).document(phone).get()
        return doc.to_dict() if doc.exists else None

    def upsert(self, phone: str, name: str, platform: str, channel_id: str) -> None:
        """
        Crea o actualiza el perfil de un cliente con identidad verificada de inmediato.
        Usado por el canal WhatsApp en el primer contacto.

        Reglas de merge (ADR 0006 sección 3):
          - name: last-wins
          - connected_channels: append-only
          - telegram_ids / instagram_ids: append-only
          - El resto de arrays (allergies, preferences, notes, actual_tables)
            no se tocan aquí — los gestiona el panel web al cerrar reservas.
        """
        db = get_firestore_client()
        ref = db.collection(COL).document(phone)
        doc = ref.get()

        ids_field = _CHANNEL_IDS_FIELD.get(platform)

        if not doc.exists:
            data = {
                "phone": phone,
                "name": name,
                "connectedChannels": [platform],
                "telegramIds": [],
                "instagramIds": [],
                "visitCount": 0,
                "actualTables": [],
                "allergies": [],
                "preferences": [],
                "notes": [],
                "createdAt": firestore.SERVER_TIMESTAMP,
                "updatedAt": firestore.SERVER_TIMESTAMP,
            }
            if ids_field:
                data[ids_field] = [channel_id]
            ref.set(data)
            logger.info(f"customer creado: phone={phone} canal={platform}_{channel_id}")
        else:
            updates = {
                "name": name,
                "updatedAt": firestore.SERVER_TIMESTAMP,
                "connectedChannels": firestore.ArrayUnion([platform]),
            }
            if ids_field:
                updates[ids_field] = firestore.ArrayUnion([channel_id])
            ref.update(updates)
            logger.info(f"customer actualizado: phone={phone} canal={platform}_{channel_id}")


customer_repo = CustomerRepo()
