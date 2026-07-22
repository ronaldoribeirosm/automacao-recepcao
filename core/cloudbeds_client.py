"""Cliente da API oficial do Cloudbeds.

Regra de ouro: este cliente nunca expõe um método de DELETE. Todo método de
escrita é dry-run por padrão e só grava de verdade quando `dry_run=False` é
passado explicitamente pela camada de UI, depois de confirmação do usuário.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import requests

from core.config import CloudbedsSettings


class CloudbedsError(RuntimeError):
    """Erro de comunicação com a API do Cloudbeds."""


def extract_main_guest(reservation: dict[str, Any]) -> dict[str, Any]:
    """Extrai o hóspede principal de uma reserva vinda de `get_reservation`.

    A resposta de `getReservation` só traz e-mail no nível raiz — telefone,
    documento, data de nascimento, endereço e campos personalizados ficam
    dentro de `guestList`, indexado por guestID. Esta função devolve o
    dict do hóspede principal (isMainGuest=True, ou o primeiro se nenhum
    estiver marcado), já com fallback pro nome/e-mail de nível raiz.
    """
    guest_list = reservation.get("guestList") or {}
    main = next(
        (g for g in guest_list.values() if g.get("isMainGuest")),
        next(iter(guest_list.values()), {}),
    )
    return {
        "guestID": main.get("guestID", ""),
        "guestName": reservation.get("guestName", ""),
        "guestEmail": reservation.get("guestEmail") or main.get("guestEmail", ""),
        "guestPhone": main.get("guestPhone") or main.get("guestCellPhone", ""),
        "guestBirthdate": main.get("guestBirthdate", ""),
        "guestDocumentNumber": main.get("guestDocumentNumber", ""),
        "guestAddress": main.get("guestAddress", ""),
        "guestCountry": main.get("guestCountry", ""),
    }


@dataclass
class WriteResult:
    """Resultado de uma operação de escrita (real ou simulada)."""

    dry_run: bool
    endpoint: str
    payload: dict[str, Any]
    response: dict[str, Any] | None = None

    @property
    def applied(self) -> bool:
        return not self.dry_run and self.response is not None


@dataclass
class CloudbedsClient:
    settings: CloudbedsSettings
    timeout: int = 20
    max_retries: int = 3
    _session: requests.Session = field(default_factory=requests.Session, repr=False)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.settings.api_key}",
            "Accept": "application/json",
        }

    def _request(self, method: str, endpoint: str, **kwargs: Any) -> dict[str, Any]:
        url = f"{self.settings.api_base}/{endpoint}"
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self._session.request(
                    method, url, headers=self._headers(), timeout=self.timeout, **kwargs
                )
            except requests.RequestException as exc:
                last_error = exc
                time.sleep(min(2**attempt, 8))
                continue

            if resp.status_code == 429:
                wait = float(resp.headers.get("Retry-After", 2**attempt))
                time.sleep(wait)
                continue

            if resp.status_code >= 500:
                last_error = CloudbedsError(f"{endpoint}: HTTP {resp.status_code}")
                time.sleep(min(2**attempt, 8))
                continue

            if not resp.ok:
                raise CloudbedsError(
                    f"{endpoint}: HTTP {resp.status_code} — {resp.text[:500]}"
                )

            data = resp.json()
            if data.get("success") is False:
                raise CloudbedsError(f"{endpoint}: {data.get('message', 'falha desconhecida')}")
            return data

        raise CloudbedsError(f"{endpoint}: sem resposta após {self.max_retries} tentativas") from (
            last_error
        )

    # ---------------------------------------------------------------
    # Leitura — reservas
    # ---------------------------------------------------------------

    def get_reservations(
        self,
        *,
        check_in_from: date | None = None,
        check_in_to: date | None = None,
        check_out_from: date | None = None,
        check_out_to: date | None = None,
        status: str | None = None,
        page_size: int = 100,
    ) -> list[dict[str, Any]]:
        """Busca reservas paginando até esgotar os resultados. Só leitura."""
        params: dict[str, Any] = {
            "propertyID": self.settings.property_id,
            "pageSize": page_size,
        }
        if check_in_from:
            params["checkInFrom"] = check_in_from.isoformat()
        if check_in_to:
            params["checkInTo"] = check_in_to.isoformat()
        if check_out_from:
            params["checkOutFrom"] = check_out_from.isoformat()
        if check_out_to:
            params["checkOutTo"] = check_out_to.isoformat()
        if status:
            params["status"] = status

        # A resposta traz "count" (itens nesta página) e "total" (total real
        # da consulta) — confirmado contra a API real em 2026-07-22. Usar
        # "count" como se fosse o total faz a paginação parar cedo demais.
        all_reservations: list[dict[str, Any]] = []
        page = 1
        while True:
            data = self._request("GET", "getReservations", params={**params, "pageNumber": page})
            batch = data.get("data", [])
            all_reservations.extend(batch)
            total = data.get("total", len(all_reservations))
            if len(batch) < page_size or len(all_reservations) >= total:
                break
            page += 1
        return all_reservations

    def get_reservation(self, reservation_id: str) -> dict[str, Any]:
        data = self._request(
            "GET",
            "getReservation",
            params={"reservationID": reservation_id, "propertyID": self.settings.property_id},
        )
        return data.get("data", {})

    def get_reservation_notes(self, reservation_id: str) -> list[dict[str, Any]]:
        data = self._request(
            "GET",
            "getReservationNotes",
            params={"reservationID": reservation_id, "propertyID": self.settings.property_id},
        )
        return data.get("data", [])

    def get_rooms(self) -> list[dict[str, Any]]:
        """Lista os quartos da propriedade.

        A resposta vem agrupada por propriedade (`data: [{propertyID, rooms:
        [...]}]`) mesmo pra uma única propriedade — confirmado contra a API
        real em 2026-07-22. Achata isso pra uma lista simples de quartos.
        """
        data = self._request("GET", "getRooms", params={"propertyID": self.settings.property_id})
        rooms: list[dict[str, Any]] = []
        for property_entry in data.get("data", []):
            rooms.extend(property_entry.get("rooms", []))
        return rooms

    def get_guest_list(
        self, *, email: str = "", phone: str = ""
    ) -> list[dict[str, Any]]:
        """Busca hóspedes por e-mail ou telefone exato via `getGuestList`.

        Confirmado contra a API real em 2026-07-22: este endpoint filtra de
        verdade no servidor por `guestEmail`/`guestPhone` (ao contrário de
        `getReservations`, que ignora esses parâmetros) — é a forma correta e
        rápida de achar o histórico de um hóspede, sem paginar anos de
        reservas da propriedade inteira.

        Passar e-mail e telefone juntos provavelmente filtra em E (mais
        estrito), não OU — pra achar "bate o e-mail OU o telefone", chame
        este método duas vezes (uma só com email, outra só com phone) e
        junte os resultados, em vez de passar os dois de uma vez.
        """
        if not email and not phone:
            return []
        params: dict[str, Any] = {"propertyID": self.settings.property_id}
        if email:
            params["guestEmail"] = email
        if phone:
            params["guestPhone"] = phone
        data = self._request("GET", "getGuestList", params=params)
        return data.get("data", [])

    def get_custom_fields(self) -> list[dict[str, Any]]:
        data = self._request(
            "GET", "getCustomFields", params={"propertyID": self.settings.property_id}
        )
        return data.get("data", [])

    # ---------------------------------------------------------------
    # Escrita — sempre dry-run aware, nunca DELETE
    # ---------------------------------------------------------------

    def put_guest(
        self,
        *,
        guest_id: str,
        reservation_id: str,
        fields: dict[str, Any],
        dry_run: bool,
    ) -> WriteResult:
        """Atualiza campos do hóspede. Em dry-run, só monta o payload."""
        payload = {
            "guestID": guest_id,
            "reservationID": reservation_id,
            "propertyID": self.settings.property_id,
            **fields,
        }
        if dry_run:
            return WriteResult(dry_run=True, endpoint="putGuest", payload=payload)

        response = self._request("PUT", "putGuest", data=payload)
        return WriteResult(dry_run=False, endpoint="putGuest", payload=payload, response=response)

    def post_reservation_note(
        self,
        *,
        reservation_id: str,
        note: str,
        dry_run: bool,
    ) -> WriteResult:
        """Adiciona uma nota à reserva (nunca sobrescreve notas existentes)."""
        payload = {
            "reservationID": reservation_id,
            "propertyID": self.settings.property_id,
            "note": note,
        }
        if dry_run:
            return WriteResult(dry_run=True, endpoint="postReservationNote", payload=payload)

        response = self._request("POST", "postReservationNote", data=payload)
        return WriteResult(
            dry_run=False, endpoint="postReservationNote", payload=payload, response=response
        )
