from firebase_admin import firestore
from app.repositories.firebase_client import get_firestore_client
from app.utils.logger import setup_logger

logger = setup_logger("reservation_repo")

COL = "reservations"


def _hora_to_minutes(hora_str: str) -> int:
    """'HH:MM' → minutos desde medianoche."""
    parts = hora_str.split(":")
    return int(parts[0]) * 60 + int(parts[1])


def _doc_to_dict(doc) -> dict:
    """Convierte un DocumentSnapshot a dict incluyendo el id."""
    data = doc.to_dict()
    data["_doc_id"] = doc.id
    return data


class ReservationRepo:

    def create(self, reservation_data: dict) -> str:
        """
        Crea una reservacion en Firestore.
        reservation_data debe usar los nombres de campo del schema ADR 0003:
          customerName, customerPhone, date, time, partySize, tableId,
          zone, status, source, notes, tags
        Retorna el doc_id generado.
        """
        db = get_firestore_client()
        data = {
            **reservation_data,
            "createdAt": firestore.SERVER_TIMESTAMP,
            "updatedAt": firestore.SERVER_TIMESTAMP,
        }
        # Asegurar valores por defecto si no vienen en reservation_data
        data.setdefault("status", "confirmed")
        data.setdefault("source", "chatbot")
        data.setdefault("notes", "")
        data.setdefault("tags", [])

        _, ref = db.collection(COL).add(data)
        logger.info(f"Reservacion creada: {ref.id} para {reservation_data.get('date')}")
        return ref.id

    def cancel(self, doc_id: str) -> None:
        """Marca una reservacion como cancelada (soft delete)."""
        db = get_firestore_client()
        db.collection(COL).document(doc_id).update({
            "status": "cancelled",
            "updatedAt": firestore.SERVER_TIMESTAMP,
        })
        logger.info(f"Reservacion cancelada: {doc_id}")

    def find_by_criteria(
        self, fecha: str, hora: str, nombre: str, telefono: str
    ) -> tuple[str, dict] | None:
        """
        Busca una reserva activa (confirmed/seated) exacta por fecha, hora,
        nombre y telefono.
        Retorna (doc_id, reservation_dict) o None.
        """
        db = get_firestore_client()
        docs = (
            db.collection(COL)
            .where("date", "==", fecha)
            .where("status", "in", ["confirmed", "seated"])
            .stream()
        )
        for doc in docs:
            r = doc.to_dict()
            if (
                r.get("time") == hora
                and r.get("customerName", "").lower() == nombre.lower()
                and r.get("customerPhone") == telefono
            ):
                return doc.id, r
        return None

    def find_by_name_and_phone(
        self, nombre: str, telefono: str, from_date: str
    ) -> list[tuple[str, str, dict]]:
        """
        Busca reservas activas futuras (>= from_date) por nombre y telefono.
        Retorna lista de (date, doc_id, reservation_dict) ordenada por fecha/hora.
        """
        db = get_firestore_client()
        # Consultar por telefono; filtrar fecha en Python para evitar indice compuesto
        docs = (
            db.collection(COL)
            .where("customerPhone", "==", telefono)
            .where("status", "in", ["confirmed", "seated"])
            .stream()
        )
        results = []
        for doc in docs:
            r = doc.to_dict()
            fecha = r.get("date", "")
            if fecha < from_date:
                continue
            if r.get("customerName", "").lower() != nombre.lower():
                continue
            results.append((fecha, doc.id, r))

        results.sort(key=lambda x: (x[0], x[2].get("time", "")))
        return results

    def get_occupied_tables_at_time(
        self, fecha: str, hora_str: str, min_stay_minutes: int
    ) -> set[str]:
        """
        Retorna IDs de mesas bloqueadas en hora_str considerando la ventana
        de ocupacion: bloquea si |T_nueva - T_existente| < min_stay_minutes.
        Solo considera reservas confirmed o seated.
        """
        data = self._get_active_for_date(fecha)
        new_time = _hora_to_minutes(hora_str)
        occupied = set()
        for r in data:
            existing_hora = r.get("time", "")
            mesa = r.get("tableId")
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
        Una sola lectura a Firestore, luego calcula las mesas bloqueadas por
        ventana para cada slot. Retorna {hora_slot: set(mesa_ids)}.
        """
        data = self._get_active_for_date(fecha)

        # Extraer (tiempo_minutos, mesa_id) de todas las reservas activas
        existing: list[tuple[int, str]] = []
        for r in data:
            hora = r.get("time", "")
            mesa = r.get("tableId")
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

    def _get_active_for_date(self, fecha: str) -> list[dict]:
        """Lee todas las reservas confirmed/seated para una fecha."""
        db = get_firestore_client()
        docs = (
            db.collection(COL)
            .where("date", "==", fecha)
            .where("status", "in", ["confirmed", "seated"])
            .stream()
        )
        return [doc.to_dict() for doc in docs]


reservation_repo = ReservationRepo()
