from app.schemas.action_schema import Reserva
from app.repositories.reservation_repo import reservation_repo
from app.utils.config import Config
from app.utils.logger import setup_logger

logger = setup_logger("reservation_service")


class ReservationService:
    def create_reservation(self, data: Reserva) -> str:
        # Verificar disponibilidad
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
            f"Reserva creada exitosamente. "
            f"Nombre: {data.nombre}, "
            f"Fecha: {data.fecha}, "
            f"Hora: {data.hora}, "
            f"Personas: {data.numero_personas}, "
            f"Teléfono: {data.telefono}."
        )


reservation_service = ReservationService()
