from openai import OpenAI
import anthropic
from app.utils.config import Config
from app.utils.logger import setup_logger

logger = setup_logger("llm_client")


class LLMClient:
    def __init__(self):
        self.github_client = OpenAI(
            base_url=Config.LLM_BASE_URL,
            api_key=Config.GITHUB_TOKEN,
        )
        self.anthropic_client = anthropic.Anthropic(
            api_key=Config.ANTHROPIC_API_KEY,
        ) if Config.ANTHROPIC_API_KEY else None
        self.model = Config.LLM_MODEL
        self._use_anthropic = False  # Se activa permanentemente si GitHub Models falla

    def call(self, messages: list[dict]) -> str:
        logger.info(f"Llamando al LLM ({self.model}) con {len(messages)} mensajes")

        # Si ya se determinó que GitHub Models no soporta este modelo, ir directo a Anthropic
        if self._use_anthropic:
            return self._call_anthropic(messages)

        # Intentar primero con GitHub Models
        try:
            response = self.github_client.chat.completions.create(
                model=self.model,
                messages=messages,
            )
            logger.info("Respuesta recibida desde GitHub Models")
            return response.choices[0].message.content

        except Exception as e:
            error_str = str(e)
            is_unknown_model = "unknown_model" in error_str or "Unknown model" in error_str

            if not is_unknown_model:
                raise  # Error distinto — propagar normalmente

            # Modelo no encontrado en GitHub Models → activar Anthropic de forma permanente
            logger.warning(
                f"Modelo '{self.model}' no encontrado en GitHub Models. "
                f"Usando Anthropic API de forma permanente para esta sesión."
            )

            if not self.anthropic_client:
                raise RuntimeError(
                    f"El modelo '{self.model}' no está disponible en GitHub Models "
                    f"y no se configuró ANTHROPIC_API_KEY como fallback."
                ) from e

            self._use_anthropic = True
            return self._call_anthropic(messages)

    def _call_anthropic(self, messages: list[dict]) -> str:
        # Separar system prompt del resto (Anthropic lo recibe por separado)
        system_content = ""
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            else:
                chat_messages.append(msg)

        response = self.anthropic_client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system_content,
            messages=chat_messages,
        )
        logger.info("Respuesta recibida desde Anthropic API")
        return response.content[0].text
