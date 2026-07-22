"""Conta estadias anteriores de um hóspede pra montar a nota da reserva.

Só leitura em Cloudbeds até o momento de gravar a nota (função 3 do projeto).
Casa hóspedes pelo e-mail ou telefone normalizado, nunca só pelo nome —
mesma preocupação de `core.matching`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from core.matching import normalize_secondary

COMPLETED_STATUSES = {"checked_out", "checked-out", "completed"}


@dataclass
class StayHistory:
    previous_stays: int
    stay_dates: list[str]

    def to_note(self) -> str:
        if self.previous_stays == 0:
            return "Primeira estadia deste hóspede (sem histórico anterior encontrado)."
        plural = "estadias" if self.previous_stays > 1 else "estadia"
        dates_str = ", ".join(self.stay_dates)
        return (
            f"Hóspede com {self.previous_stays} {plural} anterior(es) registrada(s): "
            f"{dates_str}."
        )


def count_previous_stays(
    *,
    all_reservations: list[dict[str, Any]],
    guest_email: str,
    guest_phone: str,
    current_reservation_id: str,
) -> StayHistory:
    """Recebe reservas já buscadas (get_reservations com lookback configurado)
    e conta quantas, além da atual, pertencem ao mesmo hóspede — por e-mail
    OU telefone normalizado, excluindo a reserva em aberto."""
    norm_email = normalize_secondary(guest_email)
    norm_phone = normalize_secondary(guest_phone)

    stay_dates: list[str] = []
    for reservation in all_reservations:
        if str(reservation.get("reservationID")) == str(current_reservation_id):
            continue
        if str(reservation.get("status", "")).lower() not in COMPLETED_STATUSES:
            continue

        res_email = normalize_secondary(str(reservation.get("guestEmail", "")))
        res_phone = normalize_secondary(str(reservation.get("guestPhone", "")))

        is_same_guest = (norm_email and res_email == norm_email) or (
            norm_phone and res_phone == norm_phone
        )
        if is_same_guest:
            check_in = reservation.get("checkInDate", "")
            stay_dates.append(check_in[:10] if check_in else "data desconhecida")

    stay_dates.sort()
    return StayHistory(previous_stays=len(stay_dates), stay_dates=stay_dates)


def lookback_start_date(today: date, years: int) -> date:
    return today.replace(year=today.year - years)
