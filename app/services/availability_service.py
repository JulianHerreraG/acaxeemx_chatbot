from app.schemas.action_schema import ConsultarDisponibilidad
from app.repositories.reservation_repo import reservation_repo
from app.utils.config import Config
from app.utils.datetime_helper import is_valid_reservation_hour
from app.utils.logger import setup_logger

logger = setup_logger("availability_service")

HORARIO_MSG = (
    "ACAXEEMX atiende de Lunes a Domingo de 2:00 PM a 10:00 PM. "
    "Las reservaciones están disponibles de 2:00 PM a 9:00 PM."
)


class AvailabilityService:
    def check_availability(self, data: ConsultarDisponibilidad) -> str:
        # Validar que la hora esté dentro del horario permitido
        if not is_valid_reservation_hour(data.hora):
            logger.info(f"Consulta fuera de horario: {data.hora}")
            slots = reservation_repo.get_available_slots_for_date(data.fecha)
            slots_str = self._format_slots(slots, data.fecha)
            return (
                f"No hay servicio a las {data.hora}. {HORARIO_MSG}\n\n"
                f"{slots_str}"
            )

        count = reservation_repo.count_by_hour(data.fecha, data.hora)
        max_cap = Config.MAX_RESERVATIONS_PER_HOUR
        available = max_cap - count

        logger.info(f"Disponibilidad {data.fecha} {data.hora}: {count}/{max_cap}")

        if available > 0:
            return (
                f"Hay disponibilidad para el {data.fecha} a las {data.hora}. "
                f"Quedan {available} mesas disponibles. ¡Es un momento perfecto para reservar!"
            )
        else:
            # Sin disponibilidad → sugerir alternativas en el mismo día
            slots = reservation_repo.get_available_slots_for_date(data.fecha)
            slots_str = self._format_slots(slots, data.fecha)
            return (
                f"No hay disponibilidad para el {data.fecha} a las {data.hora} "
                f"(límite de {max_cap} reservaciones alcanzado para esa hora).\n\n"
                f"{slots_str}"
            )

    def _format_slots(self, slots: list[str], fecha: str) -> str:
        if not slots:
            return f"En este momento no hay horarios disponibles para el {fecha}."
        slots_display = "  •  ".join(slots)
        return (
            f"Horarios disponibles el {fecha}:\n"
            f"  {slots_display}\n\n"
            f"¿Te gustaría reservar en alguno de estos horarios?"
        )


availability_service = AvailabilityService()
