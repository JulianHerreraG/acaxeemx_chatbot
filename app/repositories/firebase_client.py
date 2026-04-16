import json
import firebase_admin
from firebase_admin import credentials, firestore
from app.utils.config import Config
from app.utils.logger import setup_logger

logger = setup_logger("firebase")

_initialized = False
_db = None


def init_firebase():
    global _initialized, _db
    if _initialized:
        return
    cred_dict = json.loads(Config.FIREBASE_CREDENTIALS_JSON)
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)
    _db = firestore.client()
    _initialized = True
    logger.info("Firebase Firestore inicializado correctamente")


def get_firestore_client():
    if not _initialized:
        init_firebase()
    return _db
