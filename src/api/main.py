from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from ..chatbot.service import ChatbotService

app = FastAPI(title="AcaxeeMX Chatbot API")

class ChatRequest(BaseModel):
    user_id: str
    message: str
    llm_provider: str = "openai"

class ChatResponse(BaseModel):
    response: str

chatbot_service = ChatbotService()

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        response = await chatbot_service.process_message(
            request.user_id, 
            request.message
        )
        return ChatResponse(response=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}