import pytest
from src.chatbot.service import ChatbotService

@pytest.mark.asyncio
async def test_chatbot_response():
    service = ChatbotService()
    response = await service.process_message("test_user", "Hola")
    assert isinstance(response, str)
    assert len(response) > 0