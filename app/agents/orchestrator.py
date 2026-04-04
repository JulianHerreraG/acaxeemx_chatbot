from app.clients.llm_client import LLMClient
from app.prompts.system_prompt import SYSTEM_PROMPT
from app.utils.datetime_helper import get_current_datetime
from app.utils.json_parser import parse_llm_response
from app.utils.config import Config
from app.utils.logger import setup_logger
from app.repositories.conversation_repo import conversation_repo
from app.services.reservation_service import reservation_service
from app.services.cancellation_service import cancellation_service
from app.services.availability_service import availability_service

logger = setup_logger("orchestrator")

FALLBACK_MESSAGE = "Lo siento, ocurrió un error procesando tu mensaje. Por favor intenta de nuevo."


class Orchestrator:
    def __init__(self):
        self.llm_client = LLMClient()

    def process_message(self, chat_id: str, user_message: str) -> str:
        try:
            return self._process(chat_id, user_message)
        except Exception as e:
            logger.error(f"Error procesando mensaje de {chat_id}: {e}", exc_info=True)
            return FALLBACK_MESSAGE

    def _process(self, chat_id: str, user_message: str) -> str:
        # Paso 1: Obtener fecha/hora actual
        datetime_info = get_current_datetime()
        logger.info(f"Procesando mensaje de {chat_id}: {user_message[:50]}...")

        # Paso 2: Cargar historial de conversacion
        history = conversation_repo.get_history(chat_id)

        # Paso 3: Construir mensajes para el LLM
        system_msg = SYSTEM_PROMPT.format(
            restaurant_name=Config.RESTAURANT_NAME,
            hora_actual=datetime_info["Hora"],
            fecha_actual=datetime_info["fecha"],
        )
        messages = [{"role": "system", "content": system_msg}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        # Logging del contexto completo (descomenta para debug)
        # logger.info(f"=== CONTEXTO COMPLETO DEL LLM ===")
        # for i, msg in enumerate(messages):
        #     preview = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
        #     logger.info(f"[{i}] {msg['role']}: {preview}")

        # Paso 4: Primera pasada - llamar al LLM
        raw_response = self._call_llm_with_retry(messages)
        if raw_response is None:
            return FALLBACK_MESSAGE

        # Paso 5: Parsear y validar JSON
        action_response = self._parse_with_retry(raw_response, messages)
        if action_response is None:
            return FALLBACK_MESSAGE

        # Paso 6: Sobreescribir fecha_hora_actual con valores del sistema
        action_response.fecha_hora_actual.Hora = datetime_info["Hora"]
        action_response.fecha_hora_actual.fecha = datetime_info["fecha"]

        # Paso 7: Determinar y ejecutar accion
        action_result = None

        if action_response.reserva.estado:
            logger.info("Ejecutando: crear reserva")
            action_result = reservation_service.create_reservation(action_response.reserva)

        elif action_response.cancelar_reserva.estado:
            logger.info("Ejecutando: cancelar reserva")
            action_result = cancellation_service.cancel_reservation(action_response.cancelar_reserva)

        elif action_response.consultar_disponibilidad.estado:
            logger.info("Ejecutando: consultar disponibilidad")
            action_result = availability_service.check_availability(action_response.consultar_disponibilidad)

        # Paso 8: Si se ejecuto una accion, segunda pasada al LLM
        if action_result is not None:
            final_message = self._second_pass(messages, raw_response, action_result)
        else:
            # Respuesta directa
            final_message = action_response.mensaje_respuesta_directo.mensaje
            if not final_message:
                final_message = "¿En qué puedo ayudarte?"

        # Paso 9: Guardar turno en historial
        conversation_repo.save_turn(chat_id, "user", user_message)
        conversation_repo.save_turn(chat_id, "assistant", final_message)

        logger.info(f"Respuesta para {chat_id}: {final_message[:50]}...")
        return final_message

    def _second_pass(self, messages: list, raw_response: str, action_result: str) -> str:
        # Agregar la respuesta del modelo y el resultado de la accion
        messages.append({"role": "assistant", "content": raw_response})
        messages.append({"role": "user", "content": f"RESULTADO DE ACCION: {action_result}"})

        raw_response_2 = self._call_llm_with_retry(messages)
        if raw_response_2 is None:
            return action_result  # Devolver el resultado crudo como fallback

        action_response_2 = self._parse_with_retry(raw_response_2, messages)
        if action_response_2 is None:
            return action_result

        return action_response_2.mensaje_respuesta_directo.mensaje or action_result

    def _call_llm_with_retry(self, messages: list) -> str | None:
        for attempt in range(Config.LLM_MAX_RETRIES):
            try:
                return self.llm_client.call(messages)
            except Exception as e:
                logger.warning(f"Error en llamada LLM (intento {attempt + 1}): {e}")
        logger.error("Se agotaron los reintentos para la llamada al LLM")
        return None

    def _parse_with_retry(self, raw_response: str, messages: list):
        # Primer intento de parseo
        try:
            return parse_llm_response(raw_response)
        except Exception as e:
            logger.warning(f"Error parseando JSON (intento 1): {e}")

        # Reintentos con mensaje de correccion
        for attempt in range(2, Config.LLM_MAX_RETRIES + 1):
            messages.append({"role": "assistant", "content": raw_response})
            messages.append({
                "role": "user",
                "content": (
                    "Tu respuesta anterior no fue un JSON valido. "
                    "Por favor responde UNICAMENTE con el JSON en el formato requerido."
                ),
            })

            raw_response = self._call_llm_with_retry(messages)
            if raw_response is None:
                return None

            try:
                return parse_llm_response(raw_response)
            except Exception as e:
                logger.warning(f"Error parseando JSON (intento {attempt}): {e}")

        logger.error("Se agotaron los reintentos para parsear JSON")
        return None


orchestrator = Orchestrator()
