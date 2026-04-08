from openai import OpenAI
import anthropic
from app.utils.config import Config
from app.utils.logger import setup_logger

logger = setup_logger("llm_client")

# Prompt del modelo auxiliar: clasificador de cierre vs nueva intencion
AUX_SYSTEM_PROMPT = """Eres un clasificador de mensajes para el restaurante ACAXEEMX.
Tu unica funcion es analizar el mensaje del usuario y determinar si:
1. Es un mensaje de cierre/agradecimiento (gracias, ok, perfecto, adios, etc.)
2. Contiene una nueva intencion o solicitud que requiere atencion.

Responde UNICAMENTE con JSON:
{"tipo": "cierre", "mensaje": "<respuesta breve, calida y con la personalidad del restaurante>"}
o
{"tipo": "nueva_accion"}

Si es cierre, genera un mensaje breve de despedida mencionando ACAXEEMX.
Si detectas cualquier intencion adicional (reservar, preguntar, cancelar, etc.), responde nueva_accion."""


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
        self.aux_model = Config.LLM_AUX_MODEL
        self._use_anthropic = False

    def call(self, messages: list[dict]) -> str:
        """Llamada al modelo principal."""
        logger.info(f"Llamando al LLM principal ({self.model}) con {len(messages)} mensajes")

        if self._use_anthropic:
            return self._call_anthropic(messages, self.model)

        try:
            response = self.github_client.chat.completions.create(
                model=self.model,
                messages=messages,
            )
            logger.info("Respuesta recibida desde GitHub Models (principal)")
            return response.choices[0].message.content

        except Exception as e:
            error_str = str(e)
            is_unknown_model = "unknown_model" in error_str or "Unknown model" in error_str
            is_auth_error = "401" in error_str or "unauthorized" in error_str.lower() or "Bad credentials" in error_str

            if not is_unknown_model and not is_auth_error:
                raise

            if is_auth_error:
                logger.warning(
                    "Error de autenticacion en GitHub Models (token invalido o vencido). "
                    "Intentando con Anthropic API..."
                )
            else:
                logger.warning(
                    f"Modelo '{self.model}' no encontrado en GitHub Models. "
                    f"Usando Anthropic API de forma permanente para esta sesion."
                )

            if not self.anthropic_client:
                raise RuntimeError(
                    "GitHub Models fallo (auth o modelo no disponible) "
                    "y no se configuro ANTHROPIC_API_KEY como fallback. "
                    "Verifica GITHUB_TOKEN o agrega ANTHROPIC_API_KEY."
                ) from e

            self._use_anthropic = True
            return self._call_anthropic(messages, self.model)

    def call_auxiliary(self, user_message: str, context_history: list[dict] | None = None) -> str:
        """
        Llamada al modelo auxiliar (ligero) para clasificar mensajes de cierre.
        Siempre usa GitHub Models (gpt-4o-mini es nativo ahi).
        """
        logger.info(f"Llamando al LLM auxiliar ({self.aux_model})")
        messages = [{"role": "system", "content": AUX_SYSTEM_PROMPT}]
        if context_history:
            # Enviar solo los ultimos 2 turnos para contexto minimo
            messages.extend(context_history[-2:])
        messages.append({"role": "user", "content": user_message})

        try:
            response = self.github_client.chat.completions.create(
                model=self.aux_model,
                messages=messages,
            )
            logger.info("Respuesta recibida desde LLM auxiliar")
            return response.choices[0].message.content
        except Exception as e:
            # Si el auxiliar falla por auth o modelo, lanzar para que el
            # orquestador lo maneje como si no hubiera cierre detectado.
            logger.warning(f"Error en modelo auxiliar ({type(e).__name__}): {e}. Delegando al principal.")
            raise

    def _call_anthropic(self, messages: list[dict], model: str) -> str:
        system_content = ""
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            else:
                chat_messages.append(msg)

        response = self.anthropic_client.messages.create(
            model=model,
            max_tokens=1024,
            system=system_content,
            messages=chat_messages,
        )
        logger.info("Respuesta recibida desde Anthropic API")
        return response.content[0].text
