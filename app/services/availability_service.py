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
                    f"No hay servicio a las {data.hora}. {HORARIO_MSG}\n\n"
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
                        f"Las {data.hora} ya pasaron hoy. "
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
                    f"No hay mesas disponibles el {data.fecha} a las {data.hora}.\n\n"
                    f"{day_info}"
                ),
            }

        cap_detail = self._format_capacity(avail["available_by_capacity"], avail["seat_rules"])
        return {
            "exito": True,
            "mensaje": (
                f"Disponibilidad para el {data.fecha} a las {data.hora}:\n"
                f"{avail['available']} mesas disponibles de {avail['total_tables']} totales.\n\n"
                f"{cap_detail}\n\n"
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

        if suitable_count > 0:
            return {
                "exito": True,
                "mensaje": (
                    f"Hay {suitable_count} mesa(s) disponible(s) para "
                    f"{data.numero_personas} persona(s) el {data.fecha} a las {data.hora}."
                ),
            }

        # No hay mesa para ese grupo en esa hora — mostrar alternativas
        day_info = self._build_day_summary(data.fecha, data.numero_personas)
        return {
            "exito": True,
            "mensaje": (
                f"No hay mesas disponibles para {data.numero_personas} persona(s) "
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
                f"Disponibilidad para el {data.fecha}:\n\n"
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
                # Filtrar mesas donde quepa el grupo
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
            else:
                if avail["available"] > 0:
                    lines.append(f"  {hora} — {avail['available']} mesa(s) disponible(s)")

        if not lines:
            if num_persons:
                return (
                    f"No hay mesas disponibles para {num_persons} persona(s) "
                    f"en ninguna hora del {fecha}."
                )
            return f"No hay mesas disponibles en ninguna hora del {fecha}."

        header = f"Horarios con disponibilidad el {fecha}:"
        if num_persons:
            header = f"Horarios con mesa para {num_persons} persona(s) el {fecha}:"

        return header + "\n" + "\n".join(lines) + "\n\n¿Te gustaria reservar en alguno de estos horarios?"

    def _format_capacity(self, available_by_cap: dict, seat_rules: dict) -> str:
        """Formatea detalle de mesas disponibles por capacidad."""
        lines = []
        for seats, count in available_by_cap.items():
            rule = seat_rules.get(str(seats), {})
            min_p = rule.get("min_persons", 1)
            lines.append(f"  Mesa de {seats} sillas ({min_p}-{seats} personas): {count} disponible(s)")
        return "Detalle de mesas:\n" + "\n".join(lines)


availability_service = AvailabilityService()
