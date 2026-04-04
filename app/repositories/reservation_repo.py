import time
from app.repositories.firebase_client import get_db_reference
from app.utils.logger import setup_logger

logger = setup_logger("reservation_repo")


class ReservationRepo:
    def create(self, reservation_data: dict) -> str:
        fecha = reservation_data["fecha"]
        ref = get_db_reference(f"/reservaciones/{fecha}")
        new_ref = ref.push({
            **reservation_data,
            "created_at": int(time.time() * 1000),
            "estado": "confirmada",
        })
        logger.info(f"Reservacion creada: {new_ref.key} para {fecha}")
        return new_ref.key

    def find_by_criteria(self, fecha: str, hora: str, nombre: str, telefono: str):
        ref = get_db_reference(f"/reservaciones/{fecha}")
        data = ref.get()

        if not data:
            return None

        for key, value in data.items():
            if (
                value.get("hora") == hora
                and value.get("nombre", "").lower() == nombre.lower()
                and value.get("telefono") == telefono
            ):
                return key, value

        return None

    def delete(self, fecha: str, key: str):
        ref = get_db_reference(f"/reservaciones/{fecha}/{key}")
        ref.delete()
        logger.info(f"Reservacion eliminada: {key} de {fecha}")

    def count_by_hour(self, fecha: str, hora: str) -> int:
        ref = get_db_reference(f"/reservaciones/{fecha}")
        data = ref.get()

        if not data:
            return 0

        count = 0
        for key, value in data.items():
            if value.get("hora") == hora:
                count += 1

        return count

    def get_all_for_date(self, fecha: str) -> dict:
        ref = get_db_reference(f"/reservaciones/{fecha}")
        return ref.get() or {}


reservation_repo = ReservationRepo()
