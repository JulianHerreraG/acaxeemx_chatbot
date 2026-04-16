from app.schemas.action_schema import Reserva
from app.repositories.reservation_repo import reservation_repo
from app.services.table_assignment_service import table_assignment_service
from app.utils.datetime_helper import is_valid_reservation_hour
from app.utils.logger import setup_logger

logger = setup_logger("reservation_service")

HORARIO_MSG = (
    "ACAXEEMX atiende de Lunes a Domingo de 2:00 PM a 10:00 PM. "
    "Las reservaciones estan disponibles de 2:00 PM a 9:00 PM."
)


class ReservationService:
    def create_reservation(self, data: Reserva) -> dict:
        """
        Retorna {exito: bool, mensaje: str}.
        """
        # Validar horario
        if not is_valid_reservation_hour(data.hora):
            logger.info(f"Hora fuera de horario: {data.hora}")
            return {
                "exito": False,
                "mensaje": (
                    f"No es posible hacer una reservacion a las {data.hora}. "
                    f"{HORARIO_MSG}"
                ),
            }

        # Asignar mesa
        assignment = table_assignment_service.assign(
            fecha=data.fecha,
            hora=data.hora,
            num_persons=data.numero_personas,
        )

        if assignment is None:
            # Sin mesa disponible — construir alternativas
            day_avail = table_assignment_service.get_availability_for_date(data.fecha)
            alternatives = self._build_alternatives(
                day_avail, data.numero_personas, data.fecha, data.hora,
            )
            logger.info(f"Sin disponibilidad para {data.numero_personas} personas: {data.fecha} {data.hora}")
            return {
                "exito": False,
                "mensaje": (
                    f"No hay mesas disponibles para {data.numero_personas} persona(s) "
                    f"el {data.fecha} a las {data.hora}.\n\n"
                    f"{alternatives}"
                ),
            }

        # Crear reservacion con schema ADR 0003
        doc_id = reservation_repo.create({
            "customerName": data.nombre,
            "partySize": data.numero_personas,
            "customerPhone": data.telefono,
            "date": data.fecha,
            "time": data.hora,
            "tableId": assignment["table_id"],
            "zone": assignment["zone"],
            "status": "confirmed",
            "source": "chatbot",
            "notes": "",
            "tags": [],
        })

        logger.info(f"Reserva creada: {doc_id} mesa {assignment['table_id']} para {data.nombre}")
        return {
            "exito": True,
            "mensaje": (
                f"Reserva creada exitosamente en ACAXEEMX. "
                f"Nombre: {data.nombre}, "
                f"Fecha: {data.fecha}, "
                f"Hora: {data.hora}, "
                f"Personas: {data.numero_personas}, "
                f"Telefono: {data.telefono}, "
                f"Mesa: {assignment['table_id']} "
                f"(Zona {assignment['zone']} - {assignment['zone_name']}, "
                f"{assignment['seats']} sillas)."
            ),
        }

    def _build_alternatives(
        self, day_avail: dict, num_persons: int, fecha: str, hora_solicitada: str
    ) -> str:
        """Construye sugerencias de horarios donde si hay mesa para el grupo."""
        lines = []
        for hora, avail in day_avail.items():
            if hora == hora_solicitada:
                continue
            seat_rules = avail["seat_rules"]
            suitable = 0
            for seats, count in avail["available_by_capacity"].items():
                rule = seat_rules.get(str(seats))
                if not rule:
                    continue
                if num_persons > seats or num_persons < rule["min_persons"]:
                    continue
                suitable += count
            if suitable > 0:
                lines.append(f"  {hora} — {suitable} mesa(s) disponible(s)")

        if not lines:
            return (
                f"No hay mesas disponibles para {num_persons} persona(s) "
                f"en ninguna hora del {fecha}."
            )

        return (
            f"Horarios con mesa para {num_persons} persona(s) el {fecha}:\n"
            + "\n".join(lines)
            + "\n\n¿Te gustaria reservar en alguno de estos horarios?"
        )


reservation_service = ReservationService()
