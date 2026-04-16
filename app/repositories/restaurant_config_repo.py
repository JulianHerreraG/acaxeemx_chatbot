from app.repositories.firebase_client import get_firestore_client
from app.utils.logger import setup_logger

logger = setup_logger("restaurant_config_repo")

# Valores por defecto en caso de que restaurant_config/settings no este seeded.
# Coinciden con restaurant_tables.json — fuente de verdad en acaxee_platform/.
_DEFAULT_SEAT_RULES = {
    "2":  {"min_persons": 1, "max_persons": 2},
    "4":  {"min_persons": 1, "max_persons": 4},
    "6":  {"min_persons": 3, "max_persons": 6},
    "8":  {"min_persons": 6, "max_persons": 8},
    "10": {"min_persons": 6, "max_persons": 10},
}

_DEFAULT_ZONES = {
    "A": {"name": "Barra lateral izquierda", "description": "Mesas intimas y medianas"},
    "B": {"name": "Rectangulares centro-izquierda", "description": "Grupos y familias"},
    "C": {"name": "Redondas grandes superiores", "description": "Grupos grandes, celebraciones"},
    "D": {"name": "Centro del salon", "description": "Mesas para 2, intimas"},
    "E": {"name": "Centro-derecha", "description": "Mesas para 2, intimas"},
    "F": {"name": "Columna rectangulares derecha", "description": "Mesas para 2-4"},
    "G": {"name": "Redondas extremo derecho", "description": "Desde intimas hasta eventos"},
}


class RestaurantConfigRepo:
    """
    Lee la configuracion del restaurante desde Firestore y la cachea en memoria.
    Coleccion 'tables' para el catalogo de mesas (schema ADR 0003).
    Documento 'restaurant_config/settings' para seat_rules y zonas.
    Se carga una vez al arrancar la app; no cambia en runtime.
    """

    def __init__(self):
        self._tables: dict | None = None
        self._zones: dict | None = None
        self._seat_rules: dict | None = None

    def _load(self):
        if self._tables is not None:
            return

        db = get_firestore_client()
        logger.info("Cargando configuracion del restaurante desde Firestore...")

        # --- Mesas ---
        table_docs = db.collection("tables").stream()
        tables = {}
        for doc in table_docs:
            data = doc.to_dict()
            # ADR 0003 usa 'capacity'; internamente mantenemos 'seats' para
            # no cambiar table_assignment_service.
            table_id = str(data.get("number", doc.id))
            tables[table_id] = {
                "zone": data.get("zone", ""),
                "seats": data.get("capacity", data.get("seats", 0)),
                "shape": data.get("shape", ""),
            }

        if not tables:
            raise RuntimeError(
                "No se encontraron mesas en Firestore (coleccion 'tables' vacia). "
                "Ejecuta: python -m scripts.seed_restaurant_config"
            )
        self._tables = tables
        logger.info(f"Config cargada: {len(self._tables)} mesas")

        # --- Seat rules y zonas ---
        config_doc = db.collection("restaurant_config").document("settings").get()
        if config_doc.exists:
            config_data = config_doc.to_dict()
            self._seat_rules = config_data.get("seat_rules", _DEFAULT_SEAT_RULES)
            self._zones = config_data.get("zones", _DEFAULT_ZONES)
            logger.info("Seat rules y zonas cargadas desde restaurant_config/settings")
        else:
            logger.warning(
                "Documento restaurant_config/settings no encontrado. "
                "Usando valores por defecto hardcodeados."
            )
            self._seat_rules = _DEFAULT_SEAT_RULES
            self._zones = _DEFAULT_ZONES

    def get_tables(self) -> dict:
        """Retorna {table_id: {zone, seats, shape}}."""
        self._load()
        return self._tables

    def get_zones(self) -> dict:
        """Retorna {zone_code: {name, description}}."""
        self._load()
        return self._zones

    def get_seat_rules(self) -> dict:
        """Retorna {str(seats): {min_persons, max_persons}}."""
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
