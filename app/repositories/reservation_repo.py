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
        """Busca una reserva exacta por fecha, hora, nombre y telefono."""
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

    def find_by_name_and_phone(self, nombre: str, telefono: str, from_date: str) -> list:
        """
        Busca todas las reservas futuras (>= from_date) con ese nombre y telefono.
        Retorna lista de (fecha, key, reservation_data).
        """
        ref = get_db_reference("/reservaciones")
        all_dates = ref.get()

        if not all_dates:
            return []

        results = []
        for fecha, reservations in all_dates.items():
            if fecha < from_date:
                continue
            if not isinstance(reservations, dict):
                continue
            for key, value in reservations.items():
                if (
                    value.get("nombre", "").lower() == nombre.lower()
                    and value.get("telefono") == telefono
                ):
                    results.append((fecha, key, value))

        # Ordenar por fecha y hora
        results.sort(key=lambda x: (x[0], x[2].get("hora", "")))
        return results

    def get_available_slots_for_date(self, fecha: str) -> list[str]:
        """
        Retorna los horarios disponibles (HH:00) para una fecha dada,
        entre OPEN_HOUR y LAST_RESERVATION_HOUR.
        """
        from app.utils.config import Config

        ref = get_db_reference(f"/reservaciones/{fecha}")
        data = ref.get() or {}

        # Contar reservas por hora
        counts: dict[str, int] = {}
        for key, value in data.items():
            hora = value.get("hora", "")
            counts[hora] = counts.get(hora, 0) + 1

        # Encontrar slots disponibles
        available = []
        for hour in range(Config.RESTAURANT_OPEN_HOUR, Config.RESTAURANT_LAST_RESERVATION_HOUR + 1):
            hora_str = f"{hour:02d}:00"
            if counts.get(hora_str, 0) < Config.MAX_RESERVATIONS_PER_HOUR:
                available.append(hora_str)

        return available

    def delete(self, fecha: str, key: str):
        ref = get_db_reference(f"/reservaciones/{fecha}/{key}")
        ref.delete()
        logger.info(f"Reservacion eliminada: {key} de {fecha}")

    def count_by_hour(self, fecha: str, hora: str) -> int:
        ref = get_db_reference(f"/reservaciones/{fecha}")
        data = ref.get()

        if not data:
            return 0

        return sum(1 for v in data.values() if v.get("hora") == hora)

    def get_all_for_date(self, fecha: str) -> dict:
        ref = get_db_reference(f"/reservaciones/{fecha}")
        return ref.get() or {}


reservation_repo = ReservationRepo()
