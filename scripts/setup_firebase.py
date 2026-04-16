"""
OBSOLETO — Este script inicializaba la estructura de Firebase Realtime Database.

Con la migracion a Firestore (ADR 0003), este script ya no es necesario.
El seed ahora se hace con:

    python -m scripts.seed_restaurant_config

Ese script escribe en Firestore:
  - tables/{id}                  → catalogo de mesas
  - restaurant_config/settings   → seat_rules, zonas, metadata
"""

if __name__ == "__main__":
    print("Este script esta obsoleto. Usa: python -m scripts.seed_restaurant_config")
