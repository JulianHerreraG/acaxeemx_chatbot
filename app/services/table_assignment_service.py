from app.repositories.restaurant_config_repo import restaurant_config_repo
from app.repositories.reservation_repo import reservation_repo
from app.utils.config import Config
from app.utils.logger import setup_logger

logger = setup_logger("table_assignment")


def _build_hour_slots() -> list[str]:
    """
    Genera la lista de slots horarios en punto (HH:00) dentro del rango de
    reservaciones. El slot final es el último HH:00 <= LAST_RESERVATION.
    Ej: rango 14:00-20:30 → [14:00, 15:00, ..., 20:00]
    """
    slots = []
    for hour in range(Config.RESTAURANT_OPEN_HOUR, Config.RESTAURANT_LAST_RESERVATION_HOUR + 1):
        slot = f"{hour:02d}:00"
        # Incluir solo si el slot cae dentro del límite
        slot_minutes = hour * 60
        last_minutes = (
            Config.RESTAURANT_LAST_RESERVATION_HOUR * 60
            + Config.RESTAURANT_LAST_RESERVATION_MINUTE
        )
        if slot_minutes <= last_minutes:
            slots.append(slot)
    return slots


class TableAssignmentService:
    """
    Asigna la mesa óptima para un grupo usando la ventana MIN_STAY_MINUTES
    para determinar conflictos entre reservas.
    """

    def assign(self, fecha: str, hora: str, num_persons: int) -> dict | None:
        """
        Retorna {table_id, zone, seats, zone_name} o None si no hay mesa.
        """
        candidates = restaurant_config_repo.get_tables_for_party(num_persons)
        if not candidates:
            logger.info(f"Sin mesas candidatas para {num_persons} personas")
            return None

        occupied = reservation_repo.get_occupied_tables_at_time(
            fecha, hora, Config.MIN_STAY_MINUTES
        )

        zones = restaurant_config_repo.get_zones()
        for table_id, info in candidates:
            if table_id not in occupied:
                zone_info = zones.get(info["zone"], {})
                result = {
                    "table_id": table_id,
                    "zone": info["zone"],
                    "seats": info["seats"],
                    "zone_name": zone_info.get("name", info["zone"]),
                }
                logger.info(
                    f"Mesa asignada: {table_id} (zona {info['zone']}, "
                    f"{info['seats']} sillas) para {num_persons} personas "
                    f"el {fecha} a las {hora}"
                )
                return result

        logger.info(f"Sin mesas disponibles para {num_persons} personas el {fecha} a las {hora}")
        return None

    def get_availability_for_hour(self, fecha: str, hora: str) -> dict:
        """
        Resumen de disponibilidad para una fecha/hora considerando la ventana
        de ocupación.
        """
        all_tables = restaurant_config_repo.get_tables()
        occupied = reservation_repo.get_occupied_tables_at_time(
            fecha, hora, Config.MIN_STAY_MINUTES
        )
        seat_rules = restaurant_config_repo.get_seat_rules()

        available_by_cap: dict[int, int] = {}
        for table_id, info in all_tables.items():
            if table_id not in occupied:
                seats = info["seats"]
                available_by_cap[seats] = available_by_cap.get(seats, 0) + 1

        return {
            "total_tables": len(all_tables),
            "occupied": len(occupied),
            "available": len(all_tables) - len(occupied),
            "available_by_capacity": dict(sorted(available_by_cap.items())),
            "seat_rules": seat_rules,
        }

    def get_availability_for_date(self, fecha: str) -> dict[str, dict]:
        """
        Una sola lectura a Firebase y calcula disponibilidad para todos los
        slots del día considerando la ventana MIN_STAY_MINUTES.
        Retorna {hora: {total_tables, occupied, available, available_by_capacity}}
        """
        all_tables = restaurant_config_repo.get_tables()
        seat_rules = restaurant_config_repo.get_seat_rules()
        total = len(all_tables)

        hour_slots = _build_hour_slots()

        # Una sola lectura a Firebase para todas las horas del día
        occupied_by_slot = reservation_repo.get_all_occupied_tables_windowed(
            fecha, hour_slots, Config.MIN_STAY_MINUTES
        )

        result = {}
        for hora_str in hour_slots:
            occupied = occupied_by_slot.get(hora_str, set())
            occ_count = len(occupied)

            available_by_cap: dict[int, int] = {}
            for table_id, info in all_tables.items():
                if table_id not in occupied:
                    seats = info["seats"]
                    available_by_cap[seats] = available_by_cap.get(seats, 0) + 1

            result[hora_str] = {
                "total_tables": total,
                "occupied": occ_count,
                "available": total - occ_count,
                "available_by_capacity": dict(sorted(available_by_cap.items())),
                "seat_rules": seat_rules,
            }
        return result


table_assignment_service = TableAssignmentService()
