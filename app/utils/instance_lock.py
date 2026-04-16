"""
Sistema de locking distribuido para asegurar una sola instancia del bot.

Usa Firestore para coordinar multiples instancias.
Solo la instancia con el lock puede ejecutarse. Las otras esperan o se detienen.

Coleccion Firestore: app_state
Documento: bot_lock (o el nombre que se pase en lock_path)
"""

import time
import uuid
from app.repositories.firebase_client import get_firestore_client
from app.utils.logger import setup_logger

logger = setup_logger("instance_lock")

_COLLECTION = "app_state"


class InstanceLock:
    def __init__(self, lock_path: str = "/bot_lock"):
        # Convertir "/bot_lock" → "bot_lock" como ID de documento
        self.doc_id = lock_path.lstrip("/")
        self.instance_id = str(uuid.uuid4())[:8]
        self.has_lock = False

    def _ref(self):
        return get_firestore_client().collection(_COLLECTION).document(self.doc_id)

    def acquire(self, timeout: int = 60) -> bool:
        """
        Intenta adquirir el lock.
        Si otra instancia lo tiene, espera y reintenta.
        Si pasa el timeout, fuerza el lock (timeout de inactividad).

        Retorna True si se adquirio el lock, False si timeout sin lograrlo.
        """
        start_time = time.time()

        while True:
            doc = self._ref().get()
            current_lock = doc.to_dict() if doc.exists else None

            if current_lock is None or self._is_expired(current_lock):
                try:
                    self._ref().set({
                        "instance_id": self.instance_id,
                        "acquired_at": int(time.time() * 1000),
                    })
                    # Breve pausa para detectar race conditions
                    time.sleep(0.1)
                    check_doc = self._ref().get()
                    check = check_doc.to_dict() if check_doc.exists else None
                    if check and check.get("instance_id") == self.instance_id:
                        self.has_lock = True
                        logger.info(f"Lock adquirido por instancia: {self.instance_id}")
                        return True
                except Exception as e:
                    logger.warning(f"Error adquiriendo lock: {e}")

            if time.time() - start_time > timeout:
                logger.error(f"Timeout adquiriendo lock (instancia: {self.instance_id})")
                return False

            owner = current_lock.get("instance_id") if current_lock else "?"
            logger.info(f"Lock en uso por {owner}. Esperando... (instancia: {self.instance_id})")
            time.sleep(5)

    def release(self):
        """Libera el lock si lo tiene esta instancia."""
        if not self.has_lock:
            return
        try:
            doc = self._ref().get()
            current_lock = doc.to_dict() if doc.exists else None
            if current_lock and current_lock.get("instance_id") == self.instance_id:
                self._ref().delete()
                logger.info(f"Lock liberado por instancia: {self.instance_id}")
                self.has_lock = False
        except Exception as e:
            logger.error(f"Error liberando lock: {e}")

    def refresh(self) -> bool:
        """
        Refresca el timestamp del lock para indicar que la instancia sigue activa.
        Llamar periodicamente desde el loop principal.

        Retorna True si el lock aun pertenece a esta instancia.
        Retorna False si se perdio el lock (otra instancia lo tomo).
        """
        if not self.has_lock:
            return False

        try:
            doc = self._ref().get()
            current_lock = doc.to_dict() if doc.exists else None

            if current_lock and current_lock.get("instance_id") != self.instance_id:
                logger.error(f"ALERTA: Lock fue tomado por otra instancia: {current_lock.get('instance_id')}")
                self.has_lock = False
                return False

            self._ref().update({"acquired_at": int(time.time() * 1000)})
            return True

        except Exception as e:
            logger.warning(f"Error refrescando lock: {e}")
            return False

    def _is_expired(self, lock_data: dict, expiry_seconds: int = 30) -> bool:
        """Verifica si el lock expiro (sin refresh en expiry_seconds)."""
        if not lock_data:
            return True
        acquired_at = lock_data.get("acquired_at", 0)
        current_time = int(time.time() * 1000)
        return (current_time - acquired_at) > (expiry_seconds * 1000)

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
