from typing import List, Dict
from ..llm.client import LLMFactory
from ..database.firebase_client import firebase_client
from ..config import settings

class ChatbotService:
    def __init__(self, llm_provider: str = "openai"):
        self.llm_client = LLMFactory.create_client(
            llm_provider,
            settings.openai_api_key if llm_provider == "openai" else settings.anthropic_api_key
        )

    async def process_message(self, user_id: str, message: str) -> str:
        # Obtener historial de conversación
        history = firebase_client.get_conversation_history(user_id)
        
        # Construir prompt con contexto
        context = self._build_context(history)
        prompt = f"{context}\nUsuario: {message}\nAsistente:"
        
        # Generar respuesta
        response = await self.llm_client.generate_response(prompt)
        
        # Guardar conversación
        firebase_client.save_conversation(user_id, message, response)
        
        return response

    def _build_context(self, history: List[Dict]) -> str:
        context = "Historial de conversación:\n"
        for item in reversed(history[-5:]):  # Últimas 5 interacciones
            context += f"Usuario: {item['message']}\nAsistente: {item['response']}\n"
        return context