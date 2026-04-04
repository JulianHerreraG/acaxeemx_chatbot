from app.schemas.action_schema import ConsultarDisponibilidad
from app.repositories.reservation_repo import reservation_repo
from app.utils.config import Config
from app.utils.datetime_helper import is_valid_reservation_hour
from app.utils.logger import setup_logger

logger = setup_logger("availability_service")

HORARIO_MSG = (
    f"ACAXEEMX atiende de Lunes a Domingo de 2:00 PM a 10:00 PM. "
    f"Las reservaciones están disponibles de 2:00 PM a 9:00 PM."
)


class AvailabilityService:
    def check_availability(self, data: ConsultarDisponibilidad) -> str:
        # Validar que la hora esté dentro del horario permitido
        if not is_valid_reservation_hour(data.hora):
            logger.info(f"Consulta fuera de horario: {data.hora}")
            return (
                f"No hay servicio a las {data.hora}. "
                f"{HORARIO_MSG}"
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
            return (
                f"No hay disponibilidad para el {data.fecha} a las {data.hora}. "
                f"Ya se alcanzó el límite de {max_cap} reservaciones para esa hora."
            )


availability_service = AvailabilityService()
