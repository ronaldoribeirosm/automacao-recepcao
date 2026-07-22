"""Conta estadias anteriores de um hóspede pra montar a nota da reserva.

Só leitura em Cloudbeds até o momento de gravar a nota (função 3 do projeto).

Descoberta importante contra a API real em 2026-07-22: `getGuestList`
filtra de verdade no servidor por `guestEmail`/`guestPhone` — muito mais
rápido e correto do que paginar anos de `getReservations` (a propriedade
testada tem >10 mil reservas nos últimos 5 anos) e comparar nome/e-mail na
mão. O casamento continua sendo por e-mail OU telefone exato, nunca só
pelo nome — mesma preocupação de `core.matching`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

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
    candidate_reservation_ids: set[str],
    current_reservation_id: str,
    fetch_reservation: Callable[[str], dict[str, Any]],
    lookback_start: date | None = None,
) -> StayHistory:
    """`candidate_reservation_ids` já vem pré-filtrado por e-mail/telefone
    exato (via `CloudbedsClient.get_guest_list`) — aqui só resta excluir a
    reserva atual, manter só estadias concluídas, e opcionalmente cortar
    pelo `lookback_start`.
    """
    stay_dates: list[str] = []
    for reservation_id in candidate_reservation_ids:
        if str(reservation_id) == str(current_reservation_id):
            continue

        reservation = fetch_reservation(reservation_id)
        if str(reservation.get("status", "")).lower() not in COMPLETED_STATUSES:
            continue

        start_raw = reservation.get("startDate", "")
        if not start_raw:
            continue
        start = date.fromisoformat(start_raw[:10])
        if lookback_start and start < lookback_start:
            continue

        stay_dates.append(start.isoformat())

    stay_dates.sort()
    return StayHistory(previous_stays=len(stay_dates), stay_dates=stay_dates)


def lookback_start_date(today: date, years: int) -> date:
    return today.replace(year=today.year - years)
