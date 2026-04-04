from app.schemas.action_schema import ModificarReserva
from app.repositories.reservation_repo import reservation_repo
from app.utils.config import Config
from app.utils.datetime_helper import is_valid_reservation_hour, get_today_date_str
from app.utils.logger import setup_logger

logger = setup_logger("modification_service")


class ModificationService:
    """
    Combina cancelar_reserva + reserva para implementar la modificacion.

    Flujo de ejecucion progresiva:
      Fase 1 - Buscar y cancelar:
        - nombre_original + telefono_original → busca reservas futuras
        - Si hay exactamente 1 → la cancela
        - Si hay varias y no se especifica fecha/hora original → pide aclaracion
        - Si hay varias y se especifica fecha/hora → cancela la correcta
        - Si no hay ninguna → informa al usuario
      Fase 2 - Crear nueva (si ya vienen todos los datos nuevos):
        - Valida horario de la nueva reserva
        - Verifica disponibilidad
        - Si no hay disponibilidad → sugiere slots disponibles en la misma fecha
        - Crea la reserva nueva
    """

    def modify_reservation(self, data: ModificarReserva) -> str:
        today = get_today_date_str()

        # --- FASE 1: Buscar reserva original ---
        matches = reservation_repo.find_by_name_and_phone(
            nombre=data.nombre_original,
            telefono=data.telefono_original,
            from_date=today,
        )

        if not matches:
            # Si los datos nuevos están completos, la cancelación ya ocurrió en la
            # pasada anterior — ir directo a crear la nueva reserva.
            campos_nuevos = [
                data.nombre_nuevo,
                data.numero_personas_nuevo,
                data.telefono_nuevo,
                data.fecha_nueva,
                data.hora_nueva,
            ]
            if all(campos_nuevos):
                logger.info(f"Modificacion: cancelacion ya confirmada, creando nueva reserva para {data.nombre_nuevo}")
                return self._crear_nueva_reserva(cancel_msg="", data=data)

            # No hay reserva y no hay datos nuevos: genuinamente no encontrada
            logger.info(f"Modificacion: sin reservas para {data.nombre_original} / {data.telefono_original}")
            return (
                f"No encontré reservaciones futuras a nombre de {data.nombre_original} "
                f"con el teléfono {data.telefono_original}. "
                f"Verifica que el nombre y teléfono coincidan exactamente con los de la reserva original."
            )

        # Si hay varias y no se especificó cuál
        if len(matches) > 1 and not (data.fecha_original and data.hora_original):
            detalle = "\n".join(
                f"  • {fecha} a las {v.get('hora')} – {v.get('numero_personas')} persona(s)"
                for fecha, key, v in matches
            )
            logger.info(f"Modificacion: {len(matches)} reservas para {data.nombre_original}")
            return (
                f"Encontré {len(matches)} reservaciones a nombre de {data.nombre_original}:\n"
                f"{detalle}\n\n"
                f"¿Cuál deseas modificar? Indícame la fecha y hora de la reserva original."
            )

        # Identificar la reserva a cancelar
        target = None
        if len(matches) == 1:
            target = matches[0]
        else:
            # Varias → buscar por fecha y hora
            for fecha, key, value in matches:
                if fecha == data.fecha_original and value.get("hora") == data.hora_original:
                    target = (fecha, key, value)
                    break

        if target is None:
            return (
                f"No encontré una reservación el {data.fecha_original} a las {data.hora_original} "
                f"a nombre de {data.nombre_original}. Verifica los datos e intenta de nuevo."
            )

        fecha_orig, key_orig, reserva_orig = target

        # --- Cancelar la reserva original ---
        reservation_repo.delete(fecha_orig, key_orig)
        logger.info(f"Modificacion: reserva {key_orig} cancelada ({fecha_orig})")

        cancel_msg = (
            f"Reservación original cancelada: "
            f"{data.nombre_original}, {fecha_orig} a las {reserva_orig.get('hora')}."
        )

        # --- FASE 2: Crear nueva reserva si ya vienen todos los datos ---
        campos_nuevos = [
            data.nombre_nuevo,
            data.numero_personas_nuevo,
            data.telefono_nuevo,
            data.fecha_nueva,
            data.hora_nueva,
        ]
        if not all(campos_nuevos):
            return (
                f"{cancel_msg}\n\n"
                f"Ahora dime los nuevos datos para tu reserva: "
                f"fecha, hora, número de personas y teléfono de contacto."
            )

        return self._crear_nueva_reserva(cancel_msg=cancel_msg, data=data)

    def _crear_nueva_reserva(self, cancel_msg: str, data: "ModificarReserva") -> str:
        """Valida horario, disponibilidad y crea la nueva reserva."""
        prefix = f"{cancel_msg}\n\n" if cancel_msg else ""

        if not is_valid_reservation_hour(data.hora_nueva):
            slots = reservation_repo.get_available_slots_for_date(data.fecha_nueva)
            return self._horario_invalido_msg(prefix.rstrip(), data.hora_nueva, data.fecha_nueva, slots)

        count = reservation_repo.count_by_hour(data.fecha_nueva, data.hora_nueva)
        if count >= Config.MAX_RESERVATIONS_PER_HOUR:
            slots = reservation_repo.get_available_slots_for_date(data.fecha_nueva)
            return self._sin_disponibilidad_msg(prefix.rstrip(), data.fecha_nueva, data.hora_nueva, slots)

        new_key = reservation_repo.create({
            "nombre": data.nombre_nuevo,
            "numero_personas": data.numero_personas_nuevo,
            "telefono": data.telefono_nuevo,
            "fecha": data.fecha_nueva,
            "hora": data.hora_nueva,
        })
        logger.info(f"Modificacion: nueva reserva {new_key} creada ({data.fecha_nueva})")

        return (
            f"{prefix}"
            f"Nueva reservación confirmada en ACAXEEMX:\n"
            f"Nombre: {data.nombre_nuevo}\n"
            f"Fecha: {data.fecha_nueva}\n"
            f"Hora: {data.hora_nueva}\n"
            f"Personas: {data.numero_personas_nuevo}\n"
            f"Teléfono: {data.telefono_nuevo}."
        )

    def _horario_invalido_msg(self, cancel_msg: str, hora: str, fecha: str, slots: list[str]) -> str:
        slots_str = self._format_slots(slots, fecha)
        return (
            f"{cancel_msg}\n\n"
            f"La hora {hora} está fuera de nuestro horario de reservaciones "
            f"(2:00 PM – 9:00 PM).\n"
            f"{slots_str}"
        )

    def _sin_disponibilidad_msg(self, cancel_msg: str, fecha: str, hora: str, slots: list[str]) -> str:
        slots_str = self._format_slots(slots, fecha)
        return (
            f"{cancel_msg}\n\n"
            f"Lo sentimos, no hay disponibilidad el {fecha} a las {hora}.\n"
            f"{slots_str}"
        )

    def _format_slots(self, slots: list[str], fecha: str) -> str:
        if not slots:
            return f"No hay horarios disponibles para el {fecha}."
        slots_display = "  •  ".join(slots)
        return (
            f"Horarios disponibles el {fecha}:\n"
            f"  {slots_display}\n\n"
            f"¿Te gustaría reservar en alguno de estos horarios?"
        )


modification_service = ModificationService()
