"""
Servicio de identidad de canal (C4 — ADR 0007).

Responsabilidad única: garantizar que exista un documento en channel_index
para cada combinación (platform, channel_id) en el primer contacto.

- Telegram / Instagram: se registra como no-verificado (el teléfono llega después
  cuando el cliente hace una reserva y el panel web cierra la visita).
- WhatsApp: el número de teléfono es el propio channel_id, por lo que se registra
  como verificado de inmediato.

Retorna el documento actualizado de channel_index (útil para C5).
"""

from app.repositories.channel_index_repo import channel_index_repo
from app.utils.logger import setup_logger

logger = setup_logger("identity_service")

_VERIFIED_CHANNELS = {"whatsapp"}


class IdentityService:

    def ensure_channel(self, platform: str, channel_id: str) -> dict:
        """
        Verifica que el canal esté registrado en channel_index.
        Si no existe lo crea. Retorna el documento actual.
        """
        entry = channel_index_repo.get(platform, channel_id)
        if entry is not None:
            return entry

        if platform in _VERIFIED_CHANNELS:
            # Para WhatsApp el channel_id ya es el teléfono E.164
            channel_index_repo.create_verified(platform, channel_id, phone=channel_id)
        else:
            channel_index_repo.create_unverified(platform, channel_id)

        return channel_index_repo.get(platform, channel_id) or {}


identity_service = IdentityService()
