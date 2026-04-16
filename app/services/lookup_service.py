from app.schemas.action_schema import ConsultarReserva
from app.repositories.reservation_repo import reservation_repo
from app.utils.datetime_helper import get_today_date_str
from app.utils.logger import setup_logger

logger = setup_logger("lookup_service")


class LookupService:
    def lookup_reservations(self, data: ConsultarReserva) -> dict:
        """
        Busca todas las reservas futuras (hoy en adelante) por nombre y telefono.
        Retorna {exito, mensaje, reservas?}.
        """
        from_date = get_today_date_str()
        results = reservation_repo.find_by_name_and_phone(
            data.nombre, data.telefono, from_date
        )

        if not results:
            logger.info(f"Sin reservas encontradas para {data.nombre} / {data.telefono}")
            return {
                "exito": False,
                "mensaje": (
                    f"No encontré reservas vigentes a nombre de {data.nombre} "
                    f"con el teléfono {data.telefono}. "
                    f"¿Quieres hacer una nueva reserva?"
                ),
            }

        lines = []
        for fecha, doc_id, res in results:
            hora = res.get("time", "")
            personas = res.get("partySize", "?")
            lines.append(f"  • {fecha} a las {hora} — {personas} persona(s)")

        resumen = "\n".join(lines)
        logger.info(f"Reservas encontradas para {data.nombre}: {len(results)}")
        return {
            "exito": True,
            "reservas": [
                {
                    "fecha": fecha,
                    "hora": res.get("time"),
                    "numero_personas": res.get("partySize"),
                    "nombre": res.get("customerName"),
                    "telefono": res.get("customerPhone"),
                }
                for fecha, doc_id, res in results
            ],
            "mensaje": (
                f"Reservas vigentes a nombre de {data.nombre}:\n"
                f"{resumen}"
            ),
        }


lookup_service = LookupService()
