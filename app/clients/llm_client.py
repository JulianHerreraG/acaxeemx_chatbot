from openai import OpenAI
from app.utils.config import Config
from app.utils.logger import setup_logger

logger = setup_logger("llm_client")


class LLMClient:
    def __init__(self):
        self.client = OpenAI(
            base_url=Config.LLM_BASE_URL,
            api_key=Config.GITHUB_TOKEN,
        )
        self.model = Config.LLM_MODEL

    def call(self, messages: list[dict]) -> str:
        logger.info(f"Llamando al LLM ({self.model}) con {len(messages)} mensajes")
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        logger.info("Respuesta recibida del LLM")
        return content
