from app.schemas.action_schema import ConsultarDisponibilidad
from app.services.table_assignment_service import table_assignment_service
from app.utils.datetime_helper import get_current_datetime, hora_to_minutes, is_valid_reservation_hour
from app.utils.logger import setup_logger

logger = setup_logger("availability_service")

HORARIO_MSG = (
    "ACAXEEMX atiende de Lunes a Domingo de 2:00 PM a 10:00 PM. "
    "Las reservaciones estan disponibles de 2:00 PM a 9:00 PM."
)


class AvailabilityService:
    def check_availability(self, data: ConsultarDisponibilidad) -> dict:
        """
        Retorna {exito: bool, mensaje: str}.
        Si viene hora: disponibilidad para esa franja especifica.
        Si no viene hora: resumen de todo el dia.
        Si viene numero_personas: filtra mesas que quepan al grupo.
        """
        if data.hora:
            return self._check_for_hour(data)
        return self._check_for_date(data)

    def _check_for_hour(self, data: ConsultarDisponibilidad) -> dict:
        if not is_valid_reservation_hour(data.hora):
            logger.info(f"Consulta fuera de horario: {data.hora}")
            day_info = self._build_day_summary(data.fecha, data.numero_personas)
            return {
                "exito": True,
                "mensaje": (
                    f"A esa hora ya no estamos tomando reservaciones. {HORARIO_MSG}\n\n"
                    f"{day_info}"
                ),
            }

        # Si es hoy y la hora ya pasó, redirigir a disponibilidad futura
        current_dt = get_current_datetime()
        if data.fecha == current_dt["fecha"]:
            if hora_to_minutes(data.hora) < hora_to_minutes(current_dt["Hora"]):
                logger.info(f"Hora {data.hora} ya pasó hoy, mostrando disponibilidad futura")
                day_info = self._build_day_summary(data.fecha, data.numero_personas)
                return {
                    "exito": True,
                    "mensaje": (
                        f"Esa hora ya pasó hoy. "
                        f"Aquí la disponibilidad para el resto del día:\n\n"
                        f"{day_info}"
                    ),
                }

        avail = table_assignment_service.get_availability_for_hour(data.fecha, data.hora)

        if data.numero_personas:
            return self._check_for_party(data, avail)

        # Sin numero de personas: resumen general de la hora
        if avail["available"] == 0:
            day_info = self._build_day_summary(data.fecha, None)
            return {
                "exito": True,
                "mensaje": (
                    f"En ese horario ya no tenemos disponibilidad.\n\n"
                    f"{day_info}"
                ),
            }

        return {
            "exito": True,
            "mensaje": (
                f"Sí, sí tenemos disponibilidad el {data.fecha} a las {data.hora}.\n\n"
                f"¿Para cuantas personas te gustaria reservar?"
            ),
        }

    def _check_for_party(self, data: ConsultarDisponibilidad, avail: dict) -> dict:
        """Filtra disponibilidad para un grupo especifico."""
        seat_rules = avail["seat_rules"]
        suitable_count = 0
        for seats, count in avail["available_by_capacity"].items():
            rule = seat_rules.get(str(seats))
            if not rule:
                continue
            if data.numero_personas > seats or data.numero_personas < rule["min_persons"]:
                continue
            suitable_count += count

        if data.numero_personas > 10:
            has_group_capacity = table_assignment_service.can_fit_party_in_availability(
                data.numero_personas,
                avail["available_by_capacity"],
                seat_rules,
            )
        else:
            has_group_capacity = suitable_count > 0

        if has_group_capacity:
            return {
                "exito": True,
                "mensaje": (
                    f"Sí, sí tenemos disponibilidad para {data.numero_personas} persona(s) "
                    f"el {data.fecha} a las {data.hora}."
                ),
            }

        # No hay mesa para ese grupo en esa hora — mostrar alternativas
        day_info = self._build_day_summary(data.fecha, data.numero_personas)
        return {
            "exito": True,
            "mensaje": (
                f"En ese horario no tenemos disponibilidad para {data.numero_personas} persona(s). "
                f"el {data.fecha} a las {data.hora}.\n\n"
                f"{day_info}"
            ),
        }

    def _check_for_date(self, data: ConsultarDisponibilidad) -> dict:
        """Resumen de disponibilidad para todo el dia."""
        day_info = self._build_day_summary(data.fecha, data.numero_personas)
        return {
            "exito": True,
            "mensaje": (
                f"Esto es lo que tenemos disponible el {data.fecha}:\n\n"
                f"{day_info}"
            ),
        }

    def _build_day_summary(self, fecha: str, num_persons: int | None) -> str:
        """Construye resumen de horas disponibles para el dia (solo horas vigentes)."""
        all_hours = table_assignment_service.get_availability_for_date(fecha)

        # Si es hoy, filtrar las horas que ya pasaron
        current_dt = get_current_datetime()
        if fecha == current_dt["fecha"]:
            current_mins = hora_to_minutes(current_dt["Hora"])
            all_hours = {
                hora: avail for hora, avail in all_hours.items()
                if hora_to_minutes(hora) >= current_mins
            }

        lines = []
        for hora, avail in all_hours.items():
            if num_persons:
                if table_assignment_service.can_fit_party_in_availability(
                    num_persons,
                    avail["available_by_capacity"],
                    avail["seat_rules"],
                ):
                    lines.append(f"  {hora}")
            else:
                if avail["available"] > 0:
                    lines.append(f"  {hora}")

        if not lines:
            if num_persons:
                return (
                    f"No encontramos disponibilidad para {num_persons} persona(s) "
                    f"en ninguna hora del {fecha}."
                )
            return f"No hay mesas disponibles en ninguna hora del {fecha}."

        header = f"Horarios con disponibilidad el {fecha}:"
        if num_persons:
            header = f"Horarios disponibles para {num_persons} persona(s) el {fecha}:"

        return header + "\n" + "\n".join(lines) + "\n\n¿Te gustaria reservar en alguno de estos horarios?"


availability_service = AvailabilityService()
