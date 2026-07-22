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

        all_reservations: list[dict[str, Any]] = []
        page = 1
        while True:
            data = self._request("GET", "getReservations", params={**params, "pageNumber": page})
            batch = data.get("data", [])
            all_reservations.extend(batch)
            total = data.get("count", len(all_reservations))
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
        data = self._request("GET", "getRooms", params={"propertyID": self.settings.property_id})
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
