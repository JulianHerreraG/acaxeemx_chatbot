from app.schemas.action_schema import ModificarReserva
from app.repositories.reservation_repo import reservation_repo
from app.services.table_assignment_service import table_assignment_service
from app.utils.config import Config
from app.utils.datetime_helper import is_valid_reservation_hour, get_today_date_str
from app.utils.logger import setup_logger

logger = setup_logger("modification_service")


class ModificationService:
    """
    Combina cancelar_reserva + reserva para implementar la modificacion.

    Flujo de ejecucion progresiva:
      Fase 1 - Buscar y cancelar:
        - nombre_original + telefono_original -> busca reservas futuras
        - Si hay exactamente 1 -> la cancela
        - Si hay varias y no se especifica fecha/hora original -> pide aclaracion
        - Si hay varias y se especifica fecha/hora -> cancela la correcta
        - Si no hay ninguna -> informa al usuario
      Fase 2 - Crear nueva (si ya vienen todos los datos nuevos):
        - Valida horario de la nueva reserva
        - Asigna mesa disponible
        - Si no hay mesa -> sugiere horarios disponibles
        - Crea la reserva nueva
    """

    def modify_reservation(self, data: ModificarReserva) -> dict:
        """Retorna {exito: bool, mensaje: str}."""
        today = get_today_date_str()

        # --- FASE 1: Buscar reserva original ---
        matches = reservation_repo.find_by_name_and_phone(
            nombre=data.nombre_original,
            telefono=data.telefono_original,
            from_date=today,
        )

        if not matches:
            # Si los datos nuevos estan completos, la cancelacion ya ocurrio
            # en la pasada anterior — ir directo a crear la nueva reserva.
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
            return {
                "exito": False,
                "mensaje": (
                    f"No encontre reservaciones futuras a nombre de {data.nombre_original} "
                    f"con el telefono {data.telefono_original}. "
                    f"Verifica que el nombre y telefono coincidan exactamente con los de la reserva original."
                ),
            }

        # Si hay varias y no se especifico cual
        if len(matches) > 1 and not (data.fecha_original and data.hora_original):
            detalle = "\n".join(
                f"  - {fecha} a las {v.get('hora')} – {v.get('numero_personas')} persona(s)"
                + (f" (Mesa {v.get('mesa')})" if v.get("mesa") else "")
                for fecha, key, v in matches
            )
            logger.info(f"Modificacion: {len(matches)} reservas para {data.nombre_original}")
            return {
                "exito": False,
                "mensaje": (
                    f"Encontre {len(matches)} reservaciones a nombre de {data.nombre_original}:\n"
                    f"{detalle}\n\n"
                    f"¿Cual deseas modificar? Indicame la fecha y hora de la reserva original."
                ),
            }

        # Identificar la reserva a cancelar
        target = None
        if len(matches) == 1:
            target = matches[0]
        else:
            for fecha, key, value in matches:
                if fecha == data.fecha_original and value.get("hora") == data.hora_original:
                    target = (fecha, key, value)
                    break

        if target is None:
            return {
                "exito": False,
                "mensaje": (
                    f"No encontre una reservacion el {data.fecha_original} a las {data.hora_original} "
                    f"a nombre de {data.nombre_original}. Verifica los datos e intenta de nuevo."
                ),
            }

        fecha_orig, key_orig, reserva_orig = target

        # --- Cancelar la reserva original ---
        reservation_repo.delete(fecha_orig, key_orig)
        logger.info(f"Modificacion: reserva {key_orig} cancelada ({fecha_orig})")

        cancel_msg = (
            f"Reservacion original cancelada: "
            f"{data.nombre_original}, {fecha_orig} a las {reserva_orig.get('hora')}"
            + (f" (Mesa {reserva_orig.get('mesa')})" if reserva_orig.get("mesa") else "")
            + "."
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
            return {
                "exito": False,
                "mensaje": (
                    f"{cancel_msg}\n\n"
                    f"Ahora dime los nuevos datos para tu reserva: "
                    f"fecha, hora, numero de personas y telefono de contacto."
                ),
            }

        return self._crear_nueva_reserva(cancel_msg=cancel_msg, data=data)

    def _crear_nueva_reserva(self, cancel_msg: str, data: ModificarReserva) -> dict:
        """Valida horario, asigna mesa y crea la nueva reserva."""
        prefix = f"{cancel_msg}\n\n" if cancel_msg else ""

        if not is_valid_reservation_hour(data.hora_nueva):
            day_avail = table_assignment_service.get_availability_for_date(data.fecha_nueva)
            alt = self._build_alternatives(day_avail, data.numero_personas_nuevo, data.fecha_nueva)
            return {
                "exito": False,
                "mensaje": (
                    f"{prefix}"
                    f"La hora {data.hora_nueva} esta fuera de nuestro horario de reservaciones "
                    f"(2:00 PM - 9:00 PM).\n\n{alt}"
                ),
            }

        # Asignar mesa
        assignment = table_assignment_service.assign(
            fecha=data.fecha_nueva,
            hora=data.hora_nueva,
            num_persons=data.numero_personas_nuevo,
        )

        if assignment is None:
            day_avail = table_assignment_service.get_availability_for_date(data.fecha_nueva)
            alt = self._build_alternatives(day_avail, data.numero_personas_nuevo, data.fecha_nueva)
            return {
                "exito": False,
                "mensaje": (
                    f"{prefix}"
                    f"No hay mesas disponibles para {data.numero_personas_nuevo} persona(s) "
                    f"el {data.fecha_nueva} a las {data.hora_nueva}.\n\n{alt}"
                ),
            }

        new_key = reservation_repo.create({
            "nombre": data.nombre_nuevo,
            "numero_personas": data.numero_personas_nuevo,
            "telefono": data.telefono_nuevo,
            "fecha": data.fecha_nueva,
            "hora": data.hora_nueva,
            "mesa": assignment["table_id"],
            "zona": assignment["zone"],
        })
        logger.info(f"Modificacion: nueva reserva {new_key} mesa {assignment['table_id']} creada ({data.fecha_nueva})")

        return {
            "exito": True,
            "mensaje": (
                f"{prefix}"
                f"Nueva reservacion confirmada en ACAXEEMX:\n"
                f"Nombre: {data.nombre_nuevo}\n"
                f"Fecha: {data.fecha_nueva}\n"
                f"Hora: {data.hora_nueva}\n"
                f"Personas: {data.numero_personas_nuevo}\n"
                f"Telefono: {data.telefono_nuevo}\n"
                f"Mesa: {assignment['table_id']} "
                f"(Zona {assignment['zone']} - {assignment['zone_name']}, "
                f"{assignment['seats']} sillas)."
            ),
        }

    def _build_alternatives(self, day_avail: dict, num_persons: int, fecha: str) -> str:
        lines = []
        for hora, avail in day_avail.items():
            seat_rules = avail["seat_rules"]
            suitable = 0
            for seats, count in avail["available_by_capacity"].items():
                rule = seat_rules.get(str(seats))
                if not rule:
                    continue
                if num_persons > seats or num_persons < rule["min_persons"]:
                    continue
                suitable += count
            if suitable > 0:
                lines.append(f"  {hora} — {suitable} mesa(s) disponible(s)")

        if not lines:
            return (
                f"No hay mesas disponibles para {num_persons} persona(s) "
                f"en ninguna hora del {fecha}."
            )

        return (
            f"Horarios con mesa para {num_persons} persona(s) el {fecha}:\n"
            + "\n".join(lines)
            + "\n\n¿Te gustaria reservar en alguno de estos horarios?"
        )


modification_service = ModificationService()
