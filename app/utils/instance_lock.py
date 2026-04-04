"""
Sistema de locking distribuido para asegurar una sola instancia del bot.

Usa Firebase Realtime Database para coordinar multiples instancias.
Solo la instancia con el lock puede ejecutarse. Las otras esperan o se detienen.
"""

import time
import uuid
from app.repositories.firebase_client import get_db_reference
from app.utils.logger import setup_logger

logger = setup_logger("instance_lock")


class InstanceLock:
    def __init__(self, lock_path: str = "/bot_lock"):
        self.lock_path = lock_path
        self.instance_id = str(uuid.uuid4())[:8]
        self.lock_ref = get_db_reference(lock_path)
        self.has_lock = False

    def acquire(self, timeout: int = 60) -> bool:
        """
        Intenta adquirir el lock.
        Si otra instancia lo tiene, espera y reinenta.
        Si pasa el timeout, fuerza el lock (timeout de inactividad).

        Retorna True si se adquirio el lock, False si timeout sin lograr lock.
        """
        start_time = time.time()

        while True:
            current_lock = self.lock_ref.get()

            # Si no hay lock o la instancia anterior expiro
            if current_lock is None or self._is_expired(current_lock):
                try:
                    self.lock_ref.set({
                        "instance_id": self.instance_id,
                        "acquired_at": int(time.time() * 1000),
                    })
                    # Verificar que realmente escribimos (evitar race condition)
                    time.sleep(0.1)
                    lock_check = self.lock_ref.get()
                    if lock_check and lock_check.get("instance_id") == self.instance_id:
                        self.has_lock = True
                        logger.info(f"Lock adquirido por instancia: {self.instance_id}")
                        return True
                except Exception as e:
                    logger.warning(f"Error adquiriendo lock: {e}")

            # Si expiro el timeout
            if time.time() - start_time > timeout:
                logger.error(f"Timeout adquiriendo lock (instancia: {self.instance_id})")
                return False

            # Esperar y reintentar
            logger.info(f"Lock en uso por {current_lock.get('instance_id')}. Esperando... (instancia: {self.instance_id})")
            time.sleep(5)

    def release(self):
        """Libera el lock si lo tiene esta instancia."""
        if self.has_lock:
            try:
                current_lock = self.lock_ref.get()
                if current_lock and current_lock.get("instance_id") == self.instance_id:
                    self.lock_ref.delete()
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
            current_lock = self.lock_ref.get()

            # Si el lock fue tomado por otra instancia
            if current_lock and current_lock.get("instance_id") != self.instance_id:
                logger.error(f"ALERTA: Lock fue tomado por otra instancia: {current_lock.get('instance_id')}")
                self.has_lock = False
                return False

            # Refrescar timestamp
            self.lock_ref.update({
                "acquired_at": int(time.time() * 1000),
            })
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
        """Context manager support."""
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup."""
        self.release()
