"""
Script para generar la estructura inicial de datos en Firebase Realtime Database.

Ejecutar una sola vez:
    python -m scripts.setup_firebase
"""

import sys
import os

# Agregar el directorio raiz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.repositories.firebase_client import init_firebase, get_db_reference
from app.utils.logger import setup_logger

logger = setup_logger("setup_firebase")


def setup_database():
    logger.info("Inicializando Firebase...")
    init_firebase()

    logger.info("Creando estructura inicial en Realtime Database...")

    ref = get_db_reference("/")
    ref.update({
        "conversaciones": {},
        "reservaciones": {},
        "restaurante": {
            "nombre": "Acaxeemx",
            "capacidad_por_hora": 10,
            "horario": {
                "apertura": "12:00",
                "cierre": "22:00",
            },
        },
        "clientes": {},
    })

    logger.info("Estructura de base de datos creada exitosamente:")
    logger.info("  /conversaciones  - Historial temporal de chats (se limpia diariamente)")
    logger.info("  /reservaciones   - Reservaciones persistentes")
    logger.info("  /restaurante     - Datos del restaurante")
    logger.info("  /clientes        - Datos de clientes recurrentes")


if __name__ == "__main__":
    setup_database()
