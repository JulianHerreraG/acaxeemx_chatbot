from app.schemas.action_schema import Reserva
from app.repositories.reservation_repo import reservation_repo
from app.utils.config import Config
from app.utils.datetime_helper import is_valid_reservation_hour
from app.utils.logger import setup_logger

logger = setup_logger("reservation_service")

HORARIO_MSG = (
    f"ACAXEEMX atiende de Lunes a Domingo de 2:00 PM a 10:00 PM. "
    f"Las reservaciones están disponibles de 2:00 PM a 9:00 PM."
)


class ReservationService:
    def create_reservation(self, data: Reserva) -> str:
        # Validar que la hora esté dentro del horario permitido
        if not is_valid_reservation_hour(data.hora):
            logger.info(f"Hora fuera de horario: {data.hora}")
            return (
                f"No es posible hacer una reservación a las {data.hora}. "
                f"{HORARIO_MSG}"
            )

        # Verificar disponibilidad de mesas
        count = reservation_repo.count_by_hour(data.fecha, data.hora)
        if count >= Config.MAX_RESERVATIONS_PER_HOUR:
            logger.info(f"Sin disponibilidad: {data.fecha} {data.hora} ({count} reservas)")
            return (
                f"Lo sentimos, no hay disponibilidad para el {data.fecha} "
                f"a las {data.hora}. Ya se alcanzó el límite de reservaciones para esa hora."
            )

        # Crear reservacion
        reservation_data = {
            "nombre": data.nombre,
            "numero_personas": data.numero_personas,
            "telefono": data.telefono,
            "fecha": data.fecha,
            "hora": data.hora,
        }
        key = reservation_repo.create(reservation_data)

        logger.info(f"Reserva creada: {key} para {data.nombre}")
        return (
            f"Reserva creada exitosamente en ACAXEEMX. "
            f"Nombre: {data.nombre}, "
            f"Fecha: {data.fecha}, "
            f"Hora: {data.hora}, "
            f"Personas: {data.numero_personas}, "
            f"Teléfono: {data.telefono}."
        )


reservation_service = ReservationService()
