from app.repositories.firebase_client import get_db_reference
from app.utils.logger import setup_logger

logger = setup_logger("restaurant_config_repo")


class RestaurantConfigRepo:
    """
    Lee /restaurant_config de Firebase y lo cachea en memoria.
    Se carga una vez al arrancar la app; no cambia en runtime.
    """

    def __init__(self):
        self._tables: dict | None = None
        self._zones: dict | None = None
        self._seat_rules: dict | None = None

    def _load(self):
        if self._tables is not None:
            return
        logger.info("Cargando configuracion del restaurante desde Firebase...")
        ref = get_db_reference("/restaurant_config")
        data = ref.get()
        if not data:
            raise RuntimeError(
                "No se encontro /restaurant_config en Firebase. "
                "Ejecuta: python -m scripts.seed_restaurant_config"
            )
        self._tables = self._normalize(data.get("tables", {}))
        self._zones = self._normalize(data.get("zones", {}))
        self._seat_rules = self._normalize(data.get("seat_rules", {}))
        logger.info(f"Config cargada: {len(self._tables)} mesas, {len(self._zones)} zonas")

    @staticmethod
    def _normalize(value) -> dict:
        """
        Firebase RTDB convierte objetos con claves numericas consecutivas a listas.
        Este metodo revierte esa conversion: list[i] → {"i": list[i]}.
        Los None que Firebase inserta en gaps se descartan.
        """
        if isinstance(value, dict):
            return value
        if isinstance(value, list):
            return {str(i): v for i, v in enumerate(value) if v is not None}
        return {}

    def get_tables(self) -> dict:
        """Retorna dict {table_id: {zone, seats, shape}}."""
        self._load()
        return self._tables

    def get_zones(self) -> dict:
        self._load()
        return self._zones

    def get_seat_rules(self) -> dict:
        """Retorna dict {str(seats): {min_persons, max_persons}}."""
        self._load()
        return self._seat_rules

    def get_tables_for_party(self, num_persons: int) -> list[tuple[str, dict]]:
        """
        Retorna mesas donde el grupo cabe segun seat_rules:
          - mesa.seats >= num_persons
          - num_persons >= seat_rules[mesa.seats].min_persons

        Ordenadas por seats ASC (asignar la mesa mas chica que quepa).
        """
        self._load()
        result = []
        for table_id, info in self._tables.items():
            seats = info["seats"]
            rule = self._seat_rules.get(str(seats))
            if not rule:
                continue
            if num_persons > seats:
                continue
            if num_persons < rule["min_persons"]:
                continue
            result.append((table_id, info))
        result.sort(key=lambda x: x[1]["seats"])
        return result


restaurant_config_repo = RestaurantConfigRepo()
