import firebase_admin
from firebase_admin import credentials, db
from app.utils.config import Config
from app.utils.logger import setup_logger

logger = setup_logger("firebase")

_initialized = False


def init_firebase():
    global _initialized
    if _initialized:
        return
    cred = credentials.Certificate(Config.FIREBASE_CREDENTIALS_PATH)
    firebase_admin.initialize_app(cred, {
        "databaseURL": Config.FIREBASE_DATABASE_URL,
    })
    _initialized = True
    logger.info("Firebase inicializado correctamente")


def get_db_reference(path: str):
    init_firebase()
    return db.reference(path)
