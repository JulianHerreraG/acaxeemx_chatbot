from app.schemas.action_schema import CancelarReserva
from app.repositories.reservation_repo import reservation_repo
from app.utils.logger import setup_logger

logger = setup_logger("cancellation_service")


class CancellationService:
    def cancel_reservation(self, data: CancelarReserva) -> dict:
        """Retorna {exito: bool, mensaje: str}."""
        result = reservation_repo.find_by_criteria(
            fecha=data.fecha,
            hora=data.hora,
            nombre=data.nombre,
            telefono=data.telefono,
        )

        if result is None:
            logger.info(f"Reservacion no encontrada: {data.nombre} {data.fecha} {data.hora}")
            return {
                "exito": False,
                "mensaje": (
                    f"No se encontro una reservacion con esos datos "
                    f"(Nombre: {data.nombre}, Fecha: {data.fecha}, Hora: {data.hora}, "
                    f"Telefono: {data.telefono})."
                ),
            }

        doc_id, reservation = result
        reservation_repo.cancel(doc_id)

        mesa_info = ""
        if reservation.get("tableId"):
            mesa_info = f", Mesa: {reservation['tableId']}"

        logger.info(f"Reservacion cancelada: {doc_id}")
        return {
            "exito": True,
            "mensaje": (
                f"La reservacion ha sido cancelada exitosamente. "
                f"Nombre: {data.nombre}, "
                f"Fecha: {data.fecha}, "
                f"Hora: {data.hora}"
                f"{mesa_info}."
            ),
        }


cancellation_service = CancellationService()
