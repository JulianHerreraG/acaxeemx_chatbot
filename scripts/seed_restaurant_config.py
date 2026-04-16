"""
Sube la configuracion del restaurante (mesas, zonas, reglas de capacidad)
a Firestore desde el JSON fuente de verdad en acaxee_platform/.

Colecciones / documentos que se crean:
  - tables/{table_number}         → catalogo de mesas (schema ADR 0003)
  - restaurant_config/settings    → seat_rules, zonas, metadata del restaurante

Ejecutar una sola vez (o cada vez que cambie el layout):
    python -m scripts.seed_restaurant_config
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.repositories.firebase_client import init_firebase, get_firestore_client
from app.utils.logger import setup_logger

logger = setup_logger("seed_restaurant_config")

# La fuente de verdad esta en acaxee_platform/ — dos niveles arriba del chatbot
JSON_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "acaxee_platform", "prompt_engineering", "knowledge", "restaurant_tables.json",
)


def seed():
    logger.info(f"Cargando JSON desde: {JSON_PATH}")
    with open(JSON_PATH, encoding="utf-8") as f:
        config = json.load(f)

    logger.info("Inicializando Firestore...")
    init_firebase()
    db = get_firestore_client()

    tables_raw = config["tables"]    # {table_number_str: {zone, seats, shape}}
    zones = config["zones"]          # {zone_code: {name, description}}
    seat_rules = config["seat_rules"]  # {str_seats: {min_persons, max_persons}}
    restaurant_meta = config["restaurant"]

    # --- 1. Seed coleccion tables ---
    # Schema ADR 0003: number, zone, zoneName, capacity, shape, position
    batch = db.batch()
    for table_id, info in tables_raw.items():
        zone_code = info["zone"]
        zone_info = zones.get(zone_code, {})
        doc_ref = db.collection("tables").document(table_id)
        batch.set(doc_ref, {
            "number": int(table_id),
            "zone": zone_code,
            "zoneName": zone_info.get("name", zone_code),
            "capacity": info["seats"],   # ADR 0003 usa "capacity"
            "shape": info["shape"],
            "position": {"x": 0, "y": 0},  # Placeholder; el panel web asignara coords reales
        })

    batch.commit()
    logger.info(f"tables/ seeded: {len(tables_raw)} mesas")

    # --- 2. Seed restaurant_config/settings ---
    db.collection("restaurant_config").document("settings").set({
        "seat_rules": seat_rules,
        "zones": zones,
        "restaurant": restaurant_meta,
    })
    logger.info("restaurant_config/settings seeded (seat_rules, zones, metadata)")

    logger.info("Seed completo.")
    logger.info(f"  Mesas: {restaurant_meta['total_tables']}")
    logger.info(f"  Capacidad total: {restaurant_meta['total_capacity']} sillas")
    logger.info(f"  Zonas: {', '.join(zones.keys())}")


if __name__ == "__main__":
    seed()
