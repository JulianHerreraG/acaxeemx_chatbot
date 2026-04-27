from app.clients.llm_client import LLMClient
from app.prompts.system_prompt import SYSTEM_PROMPT
from app.utils.datetime_helper import get_current_datetime
from app.utils.json_parser import parse_llm_response, extract_json
from app.utils.config import Config
from app.utils.logger import setup_logger
from app.repositories.conversation_repo import conversation_repo
from app.services.identity_service import identity_service
from app.services.customer_context_service import customer_context_service
from app.services.reservation_service import reservation_service
from app.services.cancellation_service import cancellation_service
from app.services.availability_service import availability_service
from app.services.modification_service import modification_service
from app.services.lookup_service import lookup_service

logger = setup_logger("orchestrator")

FALLBACK_MESSAGE = "Lo siento, ocurrio un error procesando tu mensaje. Por favor intenta de nuevo."


class Orchestrator:
    def __init__(self):
        self.llm_client = LLMClient()

    def process_message(self, platform: str, channel_id: str, user_message: str) -> str | None:
        """
        Procesa un mensaje del usuario y retorna la respuesta del bot.
        Retorna None si la conversacion esta en modo admin (bot silenciado).

        platform: 'telegram' | 'instagram' | 'whatsapp'
        channel_id: ID unico del canal (chat_id de Telegram, PSID de Instagram, phone de WhatsApp)
        """
        try:
            return self._process(platform, channel_id, user_message)
        except Exception as e:
            conversation_key = f"{platform}_{channel_id}"
            logger.error(f"Error procesando mensaje de {conversation_key}: {e}", exc_info=True)
            return FALLBACK_MESSAGE

    def _process(self, platform: str, channel_id: str, user_message: str) -> str | None:
        conversation_key = f"{platform}_{channel_id}"

        # Paso 0: Garantizar registro en channel_index (C4)
        identity_service.ensure_channel(platform, channel_id)

        # Paso 1: Obtener fecha/hora actual
        datetime_info = get_current_datetime()
        logger.info(f"Procesando mensaje de {conversation_key}: {user_message[:50]}...")

        # Paso 2: Verificar modo admin — si esta activo, guardar el mensaje
        # en Firestore para el monitor y silenciar el bot.
        if conversation_repo.is_admin_mode(conversation_key):
            logger.info(f"Conversacion {conversation_key} en modo admin — mensaje guardado, bot silenciado")
            conversation_repo.save_turn(conversation_key, "user", user_message)
            return None

        # Paso 3: Cargar historial de conversacion
        history = conversation_repo.get_history(conversation_key)

        # Paso 4: Verificar si es mensaje de cierre post-confirmacion
        closure_response = self._try_closure(user_message, history)
        if closure_response:
            conversation_repo.save_turn(conversation_key, "user", user_message)
            conversation_repo.save_turn(conversation_key, "assistant", closure_response)
            return closure_response

        # Paso 5: Construir mensajes para el LLM principal
        context_block = customer_context_service.get_context_block(platform, channel_id)
        system_msg = SYSTEM_PROMPT.format(
            restaurant_name=Config.RESTAURANT_NAME,
            hora_actual=datetime_info["Hora"],
            fecha_actual=datetime_info["fecha"],
        )
        if context_block:
            system_msg = context_block + "\n" + system_msg
        messages = [{"role": "system", "content": system_msg}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        # Paso 6: Primera pasada - llamar al LLM
        raw_response = self._call_llm_with_retry(messages)
        if raw_response is None:
            conversation_repo.mark_needs_human(conversation_key)
            return FALLBACK_MESSAGE

        # Paso 7: Parsear y validar JSON
        action_response = self._parse_with_retry(raw_response, messages)
        if action_response is None:
            conversation_repo.mark_needs_human(conversation_key)
            return FALLBACK_MESSAGE

        # Paso 8: Sobreescribir fecha_hora_actual con valores del sistema
        action_response.fecha_hora_actual.Hora = datetime_info["Hora"]
        action_response.fecha_hora_actual.fecha = datetime_info["fecha"]

        # Paso 8.1: Escalar a asesor humano cuando el JSON lo solicite.
        if action_response.solicitar_asistencia_admin.estado:
            logger.info(f"Escalando conversacion {conversation_key} a atencion humana")
            final_message = (
                action_response.solicitar_asistencia_admin.mensaje_para_usuario
                or "Claro, te apoyo con un asesor para atenderlo mejor. En un momento te contactamos."
            )
            conversation_repo.mark_needs_human(
                conversation_key,
                action_response.solicitar_asistencia_admin.motivo,
            )
            conversation_repo.save_turn(conversation_key, "user", user_message)
            conversation_repo.save_turn(conversation_key, "assistant", final_message)
            return final_message

        # Paso 9: Determinar y ejecutar accion
        action_result = None

        if action_response.reserva.estado:
            logger.info("Ejecutando: crear reserva")
            action_result = reservation_service.create_reservation(
                action_response.reserva, platform=platform, channel_id=channel_id
            )

        elif action_response.cancelar_reserva.estado:
            logger.info("Ejecutando: cancelar reserva")
            action_result = cancellation_service.cancel_reservation(action_response.cancelar_reserva)

        elif action_response.consultar_disponibilidad.estado:
            logger.info("Ejecutando: consultar disponibilidad")
            action_result = availability_service.check_availability(action_response.consultar_disponibilidad)

        elif action_response.consultar_reserva.estado:
            logger.info("Ejecutando: consultar reserva")
            action_result = lookup_service.lookup_reservations(action_response.consultar_reserva)

        elif action_response.modificar_reserva.estado:
            logger.info("Ejecutando: modificar reserva")
            action_result = modification_service.modify_reservation(action_response.modificar_reserva)

        # Paso 10: Determinar respuesta final
        if action_result is not None:
            final_message = self._resolve_action_result(
                action_result, action_response, messages, raw_response,
            )
        else:
            # Respuesta directa (sin accion)
            final_message = action_response.mensaje_respuesta_directo.mensaje
            if not final_message:
                logger.warning("JSON sin accion ni mensaje — ejecutando llamada de recuperacion")
                final_message = self._recovery_pass(messages, raw_response)

        # Si despues de todo no hay respuesta, marcar needsHuman
        if not final_message:
            conversation_repo.mark_needs_human(conversation_key)
            final_message = FALLBACK_MESSAGE

        # Paso 11: Guardar turno en historial
        conversation_repo.save_turn(conversation_key, "user", user_message)
        conversation_repo.save_turn(conversation_key, "assistant", final_message)

        logger.info(f"Respuesta para {conversation_key}: {final_message[:50]}...")
        return final_message

    def _resolve_action_result(
        self, result: dict, action_response, messages: list, raw_response: str
    ) -> str:
        """
        Si la accion fue exitosa y hay mensaje_si_exitoso, usa ese mensaje
        directamente sin Call 2. Si fallo, hace segunda pasada al LLM.
        Para consultar_disponibilidad, siempre devuelve resultado directo.
        """
        # consultar_disponibilidad: respuesta directa de Python siempre
        if action_response.consultar_disponibilidad.estado:
            logger.info("Disponibilidad: respuesta directa sin Call 2")
            return result["mensaje"]

        is_success = result.get("exito", False)

        if is_success:
            # Buscar mensaje_si_exitoso en la accion activa
            pre_message = None
            if action_response.reserva.estado:
                pre_message = action_response.reserva.mensaje_si_exitoso
            elif action_response.cancelar_reserva.estado:
                pre_message = action_response.cancelar_reserva.mensaje_si_exitoso
            elif action_response.modificar_reserva.estado:
                pre_message = action_response.modificar_reserva.mensaje_si_exitoso

            if pre_message:
                logger.info("Accion exitosa: usando mensaje_si_exitoso (sin Call 2)")
                return pre_message

        # Fallback: segunda pasada al LLM (accion fallo o no habia mensaje anticipado)
        logger.info("Ejecutando segunda pasada al LLM")
        return self._second_pass(messages, raw_response, result["mensaje"])

    def _try_closure(self, user_message: str, history: list[dict]) -> str | None:
        """
        Detecta si el mensaje es un cierre/agradecimiento tras confirmacion.
        Usa el modelo auxiliar ligero. Retorna el mensaje de cierre o None.
        """
        if not history:
            return None

        # Verificar que el ultimo mensaje del bot contenga confirmacion exitosa
        last_bot_msg = None
        for msg in reversed(history):
            if msg["role"] == "assistant":
                last_bot_msg = msg["content"]
                break

        if not last_bot_msg:
            return None

        # Indicadores de que el ultimo mensaje fue una confirmacion de accion
        confirmation_markers = [
            "confirmada", "cancelada exitosamente", "creada exitosamente",
            "Nueva reservacion confirmada",
        ]
        is_post_confirmation = any(marker in last_bot_msg for marker in confirmation_markers)
        if not is_post_confirmation:
            return None

        # Llamar al modelo auxiliar
        try:
            aux_response = self.llm_client.call_auxiliary(
                user_message=user_message,
                context_history=history,
            )
            parsed = extract_json(aux_response)
            if parsed.get("tipo") == "cierre":
                logger.info("Modelo auxiliar: detectado cierre, sin Call principal")
                return parsed.get("mensaje", "¡Gracias! Te esperamos en ACAXEEMX.")
            logger.info("Modelo auxiliar: detectada nueva accion, delegando al principal")
            return None
        except Exception as e:
            logger.warning(f"Error en modelo auxiliar, delegando al principal: {e}")
            return None

    def _recovery_pass(self, messages: list, raw_response: str) -> str:
        """
        Llamada de recuperacion cuando el JSON no tiene accion ejecutable ni mensaje.
        """
        recovery_messages = list(messages)
        recovery_messages.append({"role": "assistant", "content": raw_response})
        recovery_messages.append({
            "role": "user",
            "content": (
                "Tu respuesta anterior no pudo procesarse: intentaste activar una accion "
                "pero faltaban datos requeridos, y además apagaste 'mensaje_respuesta_directo'. "
                "Genera una nueva respuesta donde TODAS las acciones operativas tengan "
                "estado=false, y 'mensaje_respuesta_directo' tenga estado=true con un "
                "mensaje amable pidiendo los datos que faltan para completar la solicitud."
            ),
        })

        raw_recovery = self._call_llm_with_retry(recovery_messages)
        if raw_recovery is None:
            return FALLBACK_MESSAGE

        try:
            parsed = parse_llm_response(raw_recovery)
            msg = parsed.mensaje_respuesta_directo.mensaje
            if msg:
                logger.info("Recovery pass exitoso")
                return msg
        except Exception as e:
            logger.warning(f"Error parseando recovery pass: {e}")

        return FALLBACK_MESSAGE

    def _second_pass(self, messages: list, raw_response: str, action_result: str) -> str:
        messages.append({"role": "assistant", "content": raw_response})
        messages.append({"role": "user", "content": f"RESULTADO DE ACCION: {action_result}"})

        raw_response_2 = self._call_llm_with_retry(messages)
        if raw_response_2 is None:
            return action_result

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
