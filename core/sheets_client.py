"""Cliente Google Sheets — só leitura. Nunca escreve na planilha."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import gspread
from google.oauth2.service_account import Credentials

from core.config import SheetsSettings

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


class SheetsError(RuntimeError):
    """Erro de comunicação com o Google Sheets."""


@dataclass
class SheetsClient:
    settings: SheetsSettings

    def _authorize(self) -> gspread.Client:
        try:
            creds = Credentials.from_service_account_file(
                self.settings.credentials_path, scopes=SCOPES
            )
        except FileNotFoundError as exc:
            raise SheetsError(
                f"Credencial não encontrada em {self.settings.credentials_path}"
            ) from exc
        return gspread.authorize(creds)

    def fetch_rows(self) -> list[dict[str, Any]]:
        """Retorna todas as linhas da planilha como dicts (header -> valor)."""
        client = self._authorize()
        try:
            sheet = client.open_by_key(self.settings.sheet_id)
            worksheet = sheet.worksheet(self.settings.worksheet_name)
        except gspread.exceptions.SpreadsheetNotFound as exc:
            raise SheetsError("Planilha não encontrada — confira GOOGLE_SHEET_ID") from exc
        except gspread.exceptions.WorksheetNotFound as exc:
            raise SheetsError(
                f"Aba '{self.settings.worksheet_name}' não encontrada na planilha"
            ) from exc

        records = worksheet.get_all_records()
        return records


@lru_cache(maxsize=1)
def _cached_fetch(settings: SheetsSettings) -> tuple[dict[str, Any], ...]:
    return tuple(SheetsClient(settings).fetch_rows())


def fetch_rows_cached(settings: SheetsSettings) -> list[dict[str, Any]]:
    """Wrapper cacheado por processo — evita bater na planilha a cada rerun do Streamlit."""
    return list(_cached_fetch(settings))
