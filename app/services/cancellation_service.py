from app.schemas.action_schema import CancelarReserva
from app.repositories.reservation_repo import reservation_repo
from app.utils.logger import setup_logger

logger = setup_logger("cancellation_service")


class CancellationService:
    def cancel_reservation(self, data: CancelarReserva) -> str:
        result = reservation_repo.find_by_criteria(
            fecha=data.fecha,
            hora=data.hora,
            nombre=data.nombre,
            telefono=data.telefono,
        )

        if result is None:
            logger.info(f"Reservacion no encontrada: {data.nombre} {data.fecha} {data.hora}")
            return (
                f"No se encontró una reservación con esos datos "
                f"(Nombre: {data.nombre}, Fecha: {data.fecha}, Hora: {data.hora}, "
                f"Teléfono: {data.telefono})."
            )

        key, reservation = result
        reservation_repo.delete(data.fecha, key)

        logger.info(f"Reservacion cancelada: {key}")
        return (
            f"La reservación ha sido cancelada exitosamente. "
            f"Nombre: {data.nombre}, "
            f"Fecha: {data.fecha}, "
            f"Hora: {data.hora}."
        )


cancellation_service = CancellationService()
