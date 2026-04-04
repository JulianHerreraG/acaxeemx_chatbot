from app.schemas.action_schema import ConsultarDisponibilidad
from app.repositories.reservation_repo import reservation_repo
from app.utils.config import Config
from app.utils.logger import setup_logger

logger = setup_logger("availability_service")


class AvailabilityService:
    def check_availability(self, data: ConsultarDisponibilidad) -> str:
        count = reservation_repo.count_by_hour(data.fecha, data.hora)
        max_cap = Config.MAX_RESERVATIONS_PER_HOUR
        available = max_cap - count

        logger.info(f"Disponibilidad {data.fecha} {data.hora}: {count}/{max_cap}")

        if available > 0:
            return (
                f"Hay disponibilidad para el {data.fecha} a las {data.hora}. "
                f"Quedan {available} lugares disponibles de {max_cap}."
            )
        else:
            return (
                f"No hay disponibilidad para el {data.fecha} a las {data.hora}. "
                f"Ya se alcanzó el límite de {max_cap} reservaciones para esa hora."
            )


availability_service = AvailabilityService()
