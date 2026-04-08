import time
from app.repositories.firebase_client import get_db_reference
from app.utils.logger import setup_logger

logger = setup_logger("reservation_repo")


def _hora_to_minutes(hora_str: str) -> int:
    """'HH:MM' → minutos desde medianoche. Solo formato 24h."""
    parts = hora_str.split(":")
    return int(parts[0]) * 60 + int(parts[1])


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
        results.sort(key=lambda x: (x[0], x[2].get("hora", "")))
        return results

    def get_occupied_tables_at_time(
        self, fecha: str, hora_str: str, min_stay_minutes: int
    ) -> set[str]:
        """
        Retorna IDs de mesas bloqueadas en `hora_str` considerando la ventana
        de ocupación: una mesa queda bloqueada si tiene una reserva en el rango
        (hora_str - min_stay_minutes, hora_str + min_stay_minutes), extremos excluidos.
        """
        data = self.get_all_for_date(fecha)
        new_time = _hora_to_minutes(hora_str)
        occupied = set()
        for key, value in data.items():
            existing_hora = value.get("hora", "")
            mesa = value.get("mesa")
            if not existing_hora or not mesa:
                continue
            existing_time = _hora_to_minutes(existing_hora)
            if abs(new_time - existing_time) < min_stay_minutes:
                occupied.add(str(mesa))
        return occupied

    def get_all_occupied_tables_windowed(
        self, fecha: str, hour_slots: list[str], min_stay_minutes: int
    ) -> dict[str, set[str]]:
        """
        Una sola lectura a Firebase, luego calcula las mesas bloqueadas por
        ventana para cada slot. Retorna {hora_slot: set(mesa_ids)}.
        """
        data = self.get_all_for_date(fecha)

        # Extraer (tiempo_minutos, mesa_id) de todas las reservas
        existing: list[tuple[int, str]] = []
        for key, value in data.items():
            hora = value.get("hora", "")
            mesa = value.get("mesa")
            if hora and mesa:
                existing.append((_hora_to_minutes(hora), str(mesa)))

        result: dict[str, set[str]] = {}
        for hora_slot in hour_slots:
            slot_time = _hora_to_minutes(hora_slot)
            blocked = set()
            for existing_time, mesa_id in existing:
                if abs(slot_time - existing_time) < min_stay_minutes:
                    blocked.add(mesa_id)
            result[hora_slot] = blocked

        return result

    def delete(self, fecha: str, key: str):
        ref = get_db_reference(f"/reservaciones/{fecha}/{key}")
        ref.delete()
        logger.info(f"Reservacion eliminada: {key} de {fecha}")

    def get_all_for_date(self, fecha: str) -> dict:
        ref = get_db_reference(f"/reservaciones/{fecha}")
        return ref.get() or {}


reservation_repo = ReservationRepo()
