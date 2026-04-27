"""
Servicio de contexto de cliente (C5 — ADR 0007).

Lee channel_index y customers para construir el bloque [CONTEXTO CLIENTE]
que el orchestrator inyecta al inicio del system prompt.

Retorna "" si el canal no está verificado (cliente no reconocido).
El LLM ya sabe tratar ese caso como cliente nuevo (ver system_prompt sección J).
"""

from app.repositories.channel_index_repo import channel_index_repo
from app.repositories.customer_repo import customer_repo
from app.utils.logger import setup_logger

logger = setup_logger("customer_context_service")


def _format_list(items: list) -> str:
    if not items:
        return ""
    return ", ".join(str(i) for i in items)


def _format_tables(tables: list) -> str:
    """
    actual_tables es gestionado por el panel web (W1-W4).
    Cada entrada puede ser un dict {zone, date, table} o un string.
    """
    if not tables:
        return ""
    parts = []
    for t in tables:
        if isinstance(t, dict):
            zone = t.get("zone", "")
            date = t.get("date", "")
            parts.append(f"{zone} ({date})" if date else zone)
        else:
            parts.append(str(t))
    return ", ".join(parts)


class CustomerContextService:

    def get_context_block(self, platform: str, channel_id: str) -> str:
        """
        Retorna el bloque [CONTEXTO CLIENTE] listo para prepend al system prompt.
        Retorna "" si el cliente no está verificado o no existe en customers.
        """
        try:
            entry = channel_index_repo.get(platform, channel_id)
            if not entry or not entry.get("phone"):
                return ""

            phone = entry["phone"]
            customer = customer_repo.get(phone)
            if not customer:
                return ""

            name = customer.get("name", "")
            channels = _format_list(customer.get("connectedChannels", []))
            visit_count = customer.get("visitCount", 0)
            tables = _format_tables(customer.get("actualTables", []))
            allergies = _format_list(customer.get("allergies", []))
            preferences = _format_list(customer.get("preferences", []))
            notes = _format_list(customer.get("notes", []))

            block = (
                "[CONTEXTO CLIENTE]\n"
                f"Nombre: {name}\n"
                f"Teléfono: {phone}\n"
                f"Canales verificados: {channels}\n"
                f"Visitas confirmadas: {visit_count}\n"
                f"Mesas donde se ha sentado: {tables}\n"
                f"Alergias: {allergies}\n"
                f"Preferencias conocidas: {preferences}\n"
                f"Notas: {notes}\n"
            )
            logger.info(f"Contexto cliente inyectado para {platform}_{channel_id} (phone={phone})")
            return block

        except Exception as e:
            logger.warning(f"Error construyendo contexto cliente para {platform}_{channel_id}: {e}")
            return ""


customer_context_service = CustomerContextService()
