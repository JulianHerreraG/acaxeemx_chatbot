import firebase_admin
from firebase_admin import credentials, firestore
from ..config import settings

class FirebaseClient:
    def __init__(self):
        cred = credentials.Certificate(settings.firebase_credentials_path)
        firebase_admin.initialize_app(cred)
        self.db = firestore.client()

    def save_conversation(self, user_id: str, message: str, response: str):
        doc_ref = self.db.collection('conversations').document(user_id)
        doc_ref.set({
            'user_id': user_id,
            'message': message,
            'response': response,
            'timestamp': firestore.SERVER_TIMESTAMP
        })

    def get_conversation_history(self, user_id: str, limit: int = 10):
        docs = self.db.collection('conversations')\
            .where('user_id', '==', user_id)\
            .order_by('timestamp', direction=firestore.Query.DESCENDING)\
            .limit(limit)\
            .stream()
        return [doc.to_dict() for doc in docs]

firebase_client = FirebaseClient()