from uuid import uuid4

from app.schemas.action_schema import Reserva
from app.repositories.reservation_repo import reservation_repo
from app.services.table_assignment_service import table_assignment_service
from app.utils.datetime_helper import is_valid_reservation_hour
from app.utils.logger import setup_logger

logger = setup_logger("reservation_service")

HORARIO_MSG = (
    "ACAXEEMX atiende de Lunes a Domingo de 2:00 PM a 10:00 PM. "
    "Las reservaciones estan disponibles de 2:00 PM a 9:00 PM."
)


class ReservationService:
    def create_reservation(self, data: Reserva) -> dict:
        """
        Retorna {exito: bool, mensaje: str}.
        """
        # Validar horario
        if not is_valid_reservation_hour(data.hora):
            logger.info(f"Hora fuera de horario: {data.hora}")
            return {
                "exito": False,
                "mensaje": (
                    f"No es posible hacer una reservacion a las {data.hora}. "
                    f"{HORARIO_MSG}"
                ),
            }

        return self.create_split_or_single_reservation(
            nombre=data.nombre,
            numero_personas=data.numero_personas,
            telefono=data.telefono,
            fecha=data.fecha,
            hora=data.hora,
            source="chatbot",
            notes="",
            tags=[],
        )

    def create_split_or_single_reservation(
        self,
        *,
        nombre: str,
        numero_personas: int,
        telefono: str,
        fecha: str,
        hora: str,
        source: str,
        notes: str,
        tags: list[str],
    ) -> dict:
        """
        Crea una reservacion simple o, si el grupo supera 10 personas,
        la divide automaticamente en varias mesas ligadas entre si.
        """
        if numero_personas <= 10:
            assignment = table_assignment_service.assign(
                fecha=fecha,
                hora=hora,
                num_persons=numero_personas,
            )

            if assignment is None:
                day_avail = table_assignment_service.get_availability_for_date(fecha)
                alternatives = self._build_alternatives(
                    day_avail, numero_personas, fecha, hora,
                )
                logger.info(f"Sin disponibilidad para {numero_personas} personas: {fecha} {hora}")
                return {
                    "exito": False,
                    "mensaje": (
                        f"No hay disponibilidad para {numero_personas} persona(s) "
                        f"el {fecha} a las {hora}.\n\n"
                        f"{alternatives}"
                    ),
                }

            doc_id = reservation_repo.create({
                "customerName": nombre,
                "partySize": numero_personas,
                "customerPhone": telefono,
                "date": fecha,
                "time": hora,
                "tableId": assignment["table_id"],
                "zone": assignment["zone"],
                "status": "confirmed",
                "source": source,
                "notes": notes,
                "tags": tags,
            })

            logger.info(f"Reserva creada: {doc_id} mesa {assignment['table_id']} para {nombre}")
            return {
                "exito": True,
                "mensaje": (
                    f"Reserva creada exitosamente en ACAXEEMX. "
                    f"Nombre: {nombre}, "
                    f"Fecha: {fecha}, "
                    f"Hora: {hora}, "
                    f"Personas: {numero_personas}, "
                    f"Telefono: {telefono}, "
                    f"Mesa: {assignment['table_id']} "
                    f"(Zona {assignment['zone']} - {assignment['zone_name']}, "
                    f"{assignment['seats']} sillas)."
                ),
            }

        group_plan = table_assignment_service.assign_group(
            fecha=fecha,
            hora=hora,
            num_persons=numero_personas,
        )

        if group_plan is None:
            day_avail = table_assignment_service.get_availability_for_date(fecha)
            alternatives = self._build_alternatives(
                day_avail, numero_personas, fecha, hora,
            )
            logger.info(f"Sin disponibilidad grupal para {numero_personas} personas: {fecha} {hora}")
            return {
                "exito": False,
                "mensaje": (
                    f"No hay disponibilidad para un grupo de {numero_personas} personas "
                    f"el {fecha} a las {hora}.\n\n"
                    f"{alternatives}"
                ),
            }

        group_id = f"grp_{uuid4().hex[:10]}"
        doc_ids: list[str] = []
        for index, assignment in enumerate(group_plan, start=1):
            doc_id = reservation_repo.create({
                "customerName": nombre,
                "partySize": assignment["assigned_people"],
                "customerPhone": telefono,
                "date": fecha,
                "time": hora,
                "tableId": assignment["table_id"],
                "zone": assignment["zone"],
                "status": "confirmed",
                "source": source,
                "notes": (
                    f"Reserva grupal de {numero_personas} personas · segmento {index}/{len(group_plan)}"
                ),
                "tags": [*tags, "grupo", f"group:{group_id}"],
                "groupId": group_id,
                "groupTotalPartySize": numero_personas,
                "groupSplitIndex": index,
                "groupSplitCount": len(group_plan),
            })
            doc_ids.append(doc_id)

        mesas = ", ".join(
            f"Mesa {assignment['table_id']} ({assignment['assigned_people']} personas)"
            for assignment in group_plan
        )
        logger.info(
            f"Reserva grupal creada: {group_id} para {nombre} ({numero_personas} personas)"
        )
        return {
            "exito": True,
            "grouped_assignment": True,
            "mensaje": (
                f"Reserva grupal creada exitosamente en ACAXEEMX. "
                f"Nombre: {nombre}, Fecha: {fecha}, Hora: {hora}, "
                f"Personas totales: {numero_personas}, Telefono: {telefono}. "
                f"Se asignaron {len(group_plan)} mesas dentro de la misma reserva: {mesas}."
            ),
            "doc_ids": doc_ids,
            "group_id": group_id,
        }

    def _build_alternatives(
        self, day_avail: dict, num_persons: int, fecha: str, hora_solicitada: str
    ) -> str:
        """Construye sugerencias de horarios donde si hay mesa para el grupo."""
        lines = []
        for hora, avail in day_avail.items():
            if hora == hora_solicitada:
                continue
            if table_assignment_service.can_fit_party_in_availability(
                num_persons,
                avail["available_by_capacity"],
                avail["seat_rules"],
            ):
                lines.append(f"  {hora}")

        if not lines:
            return (
                f"No hay disponibilidad para {num_persons} persona(s) "
                f"en ninguna hora del {fecha}."
            )

        return (
            f"Horarios disponibles para {num_persons} persona(s) el {fecha}:\n"
            + "\n".join(lines)
            + "\n\n¿Te gustaria reservar en alguno de estos horarios?"
        )


reservation_service = ReservationService()
