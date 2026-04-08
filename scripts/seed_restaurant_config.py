"""
Sube la configuracion del restaurante (mesas, zonas, reglas de capacidad)
a Firebase Realtime Database desde el JSON fuente de verdad.

Ejecutar una sola vez (o cada vez que cambie el layout):
    python -m scripts.seed_restaurant_config
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.repositories.firebase_client import init_firebase, get_db_reference
from app.utils.logger import setup_logger

logger = setup_logger("seed_restaurant_config")

JSON_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "prompt_engineering", "knowledge", "restaurant_tables.json",
)


def _prefix_numeric_keys(obj: dict, prefix: str) -> dict:
    """
    Firebase convierte objetos con claves numericas a arrays.
    Prefijar con una letra evita esa conversion y preserva los IDs.
    Ejemplo: {"1": {...}} → {"t1": {...}}
    """
    return {f"{prefix}{k}": v for k, v in obj.items()}


def seed():
    logger.info("Cargando JSON de configuracion del restaurante...")
    with open(JSON_PATH, encoding="utf-8") as f:
        config = json.load(f)

    # Prefijar IDs de mesas con "t" para evitar que Firebase los convierta a arrays.
    # seat_rules NO se prefixa: sus claves ("2","4","6","8","10") no son consecutivas
    # desde 0, por lo que Firebase las respeta como dict.
    config["tables"] = _prefix_numeric_keys(config["tables"], "t")

    logger.info("Inicializando Firebase...")
    init_firebase()

    ref = get_db_reference("/restaurant_config")
    ref.set(config)

    total = config["restaurant"]["total_tables"]
    cap = config["restaurant"]["total_capacity"]
    logger.info(f"Configuracion subida: {total} mesas, {cap} sillas")
    logger.info("Nodo: /restaurant_config (tablas prefijadas con 't')")


if __name__ == "__main__":
    seed()
