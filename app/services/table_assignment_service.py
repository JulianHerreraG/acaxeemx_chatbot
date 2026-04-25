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

    def assign_group(self, fecha: str, hora: str, num_persons: int) -> list[dict] | None:
        """
        Divide grupos grandes en varias mesas cercanas a nivel lógico.
        Retorna una lista de asignaciones con personas por mesa o None.
        """
        if num_persons <= 10:
            single = self.assign(fecha, hora, num_persons)
            return [
                {
                    **single,
                    "assigned_people": num_persons,
                }
            ] if single else None

        all_tables = restaurant_config_repo.get_tables()
        occupied = reservation_repo.get_occupied_tables_at_time(
            fecha, hora, Config.MIN_STAY_MINUTES
        )
        seat_rules = restaurant_config_repo.get_seat_rules()
        zones = restaurant_config_repo.get_zones()

        available_by_seats: dict[int, list[tuple[str, dict]]] = {}
        for table_id, info in all_tables.items():
            if table_id in occupied:
                continue
            available_by_seats.setdefault(info["seats"], []).append((table_id, info))

        combo = self._find_combo_from_counts(
            num_persons,
            {seats: len(tables) for seats, tables in available_by_seats.items()},
            seat_rules,
        )
        if combo is None:
            logger.info(f"Sin combinacion de mesas para {num_persons} personas el {fecha} a las {hora}")
            return None

        selected_tables: list[tuple[str, dict]] = []
        for seats in sorted(combo.keys(), reverse=True):
            selected_tables.extend(available_by_seats[seats][:combo[seats]])

        plan = self._distribute_people_across_tables(
            num_persons,
            selected_tables,
            seat_rules,
            zones,
        )
        if plan is None:
            logger.warning(f"No se pudo distribuir el grupo de {num_persons} personas aunque existia combinacion")
        return plan

    def can_fit_party_in_availability(self, num_persons: int, available_by_capacity: dict, seat_rules: dict) -> bool:
        """
        Determina si un grupo cabe en la disponibilidad actual.
        Para grupos de hasta 10 exige una sola mesa; para grupos grandes permite split.
        """
        if num_persons <= 10:
            for seats, count in available_by_capacity.items():
                rule = seat_rules.get(str(seats))
                if not rule or count <= 0:
                    continue
                if num_persons <= seats and num_persons >= rule["min_persons"]:
                    return True
            return False

        combo = self._find_combo_from_counts(num_persons, available_by_capacity, seat_rules)
        return combo is not None

    def _find_combo_from_counts(
        self,
        num_persons: int,
        available_by_capacity: dict,
        seat_rules: dict,
    ) -> dict[int, int] | None:
        """
        Busca una combinacion de mesas que cubra al grupo minimizando primero
        el numero de mesas y luego el desperdicio de asientos.
        Retorna {seats: count} o None.
        """
        seat_types = sorted(
            [int(seats) for seats, count in available_by_capacity.items() if count > 0],
            reverse=True,
        )
        if not seat_types:
            return None

        total_tables = sum(int(count) for count in available_by_capacity.values())
        for table_count in range(1, total_tables + 1):
            best_for_count: tuple[int, dict[int, int]] | None = None

            def search(index: int, remaining_tables: int, combo: dict[int, int], min_total: int, max_total: int) -> None:
                nonlocal best_for_count
                if remaining_tables == 0:
                    if min_total <= num_persons <= max_total:
                        spare = max_total - num_persons
                        candidate = {seat: count for seat, count in combo.items() if count > 0}
                        if best_for_count is None or spare < best_for_count[0]:
                            best_for_count = (spare, candidate)
                    return

                if index >= len(seat_types):
                    return

                seats = seat_types[index]
                rule = seat_rules.get(str(seats))
                if not rule:
                    search(index + 1, remaining_tables, combo, min_total, max_total)
                    return

                max_available = min(int(available_by_capacity.get(seats, 0)), remaining_tables)
                for count in range(max_available, -1, -1):
                    if count > 0:
                        combo[seats] = count
                    else:
                        combo.pop(seats, None)

                    search(
                        index + 1,
                        remaining_tables - count,
                        combo,
                        min_total + count * int(rule["min_persons"]),
                        max_total + count * seats,
                    )

                combo.pop(seats, None)

            search(0, table_count, {}, 0, 0)
            if best_for_count is not None:
                return best_for_count[1]

        return None

    def _distribute_people_across_tables(
        self,
        total_people: int,
        selected_tables: list[tuple[str, dict]],
        seat_rules: dict,
        zones: dict,
    ) -> list[dict] | None:
        allocations: list[dict] = []
        min_total = 0

        for table_id, info in sorted(selected_tables, key=lambda item: item[1]["seats"], reverse=True):
            rule = seat_rules.get(str(info["seats"]))
            if not rule:
                return None
            min_people = int(rule["min_persons"])
            min_total += min_people
            zone_info = zones.get(info["zone"], {})
            allocations.append({
                "table_id": table_id,
                "zone": info["zone"],
                "seats": info["seats"],
                "zone_name": zone_info.get("name", info["zone"]),
                "assigned_people": min_people,
            })

        remaining = total_people - min_total
        if remaining < 0:
            return None

        for allocation in allocations:
            extra_capacity = allocation["seats"] - allocation["assigned_people"]
            if extra_capacity <= 0:
                continue
            add = min(extra_capacity, remaining)
            allocation["assigned_people"] += add
            remaining -= add
            if remaining == 0:
                break

        if remaining != 0:
            return None

        return allocations

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
