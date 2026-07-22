"""Monta a planilha de ocupação (7 dias) a partir das reservas do Cloudbeds.

Só leitura — nenhuma função aqui grava nada no Cloudbeds.

Formato esperado de cada reserva (a resposta detalhada de
`CloudbedsClient.get_reservation`, confirmada contra a API real em
2026-07-22 — o endpoint de lista `getReservations` NÃO traz atribuição de
quarto, só o `getReservation` individual traz o array `assigned`):

    {
        "reservationID": "...",
        "guestName": "Maria Silva",
        "status": "confirmed",
        "assigned": [
            {
                "roomID": "12-1",
                "roomName": "101",
                "startDate": "2026-07-20",
                "endDate": "2026-07-23",
            },
            ...
        ],
    }
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd

CANCELLED_STATUSES = {"canceled", "cancelled", "no_show", "no-show"}


def _daterange(start: date, days: int) -> list[date]:
    return [start + timedelta(days=i) for i in range(days)]


def _parse_date(value: str) -> date:
    return date.fromisoformat(value[:10])


def build_occupancy_grid(
    *,
    reservations: list[dict[str, Any]],
    room_names: list[str],
    start_date: date,
    days: int = 7,
) -> pd.DataFrame:
    """Retorna um DataFrame: linhas = quartos, colunas = datas, célula = hóspede."""
    dates = _daterange(start_date, days)
    columns = [d.strftime("%d/%m (%a)") for d in dates]
    grid = pd.DataFrame("", index=room_names, columns=columns)

    for reservation in reservations:
        if str(reservation.get("status", "")).lower() in CANCELLED_STATUSES:
            continue
        guest_name = reservation.get("guestName", "")
        for room in reservation.get("assigned", []):
            room_name = room.get("roomName")
            if room_name not in grid.index:
                continue
            try:
                check_in = _parse_date(room["startDate"])
                check_out = _parse_date(room["endDate"])
            except (KeyError, ValueError):
                continue
            for i, day in enumerate(dates):
                if check_in <= day < check_out:
                    existing = grid.at[room_name, columns[i]]
                    grid.at[room_name, columns[i]] = (
                        guest_name if not existing else f"{existing} / {guest_name}"
                    )

    return grid.sort_index()


def export_to_excel(grid: pd.DataFrame, output_path: str) -> str:
    grid.to_excel(output_path, sheet_name="Ocupação")
    return output_path
