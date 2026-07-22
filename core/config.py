"""Configuração central: tudo vem de variáveis de ambiente, nunca hardcoded."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Coluna da planilha -> campo do hóspede no Cloudbeds. Confirmado contra uma
# chamada real de getReservation em 2026-07-22 (hóspede principal vem dentro
# de guestList — ver core.cloudbeds_client.extract_main_guest). Ajustável via
# FIELD_MAPPING (.env, JSON) se a propriedade usar campo personalizado no lugar.
DEFAULT_FIELD_MAPPING: dict[str, str] = {
    "cpf": "guestDocumentNumber",
    "telefone": "guestPhone",
    "email": "guestEmail",
    "data_nascimento": "guestBirthdate",
    "endereco": "guestAddress",
    "nacionalidade": "guestCountry",
}


def _env_field_mapping() -> dict[str, str]:
    raw = os.getenv("FIELD_MAPPING")
    if not raw:
        return dict(DEFAULT_FIELD_MAPPING)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return dict(DEFAULT_FIELD_MAPPING)


def _env_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "sim", "on"}


def _env_float(name: str, default: float) -> float:
    val = os.getenv(name)
    if val is None or val.strip() == "":
        return default
    return float(val)


def _env_int(name: str, default: int) -> int:
    val = os.getenv(name)
    if val is None or val.strip() == "":
        return default
    return int(val)


@dataclass(frozen=True)
class CloudbedsSettings:
    api_key: str = field(default_factory=lambda: os.getenv("CLOUDBEDS_API_KEY", ""))
    property_id: str = field(default_factory=lambda: os.getenv("CLOUDBEDS_PROPERTY_ID", ""))
    api_base: str = field(
        default_factory=lambda: os.getenv(
            "CLOUDBEDS_API_BASE", "https://hotels.cloudbeds.com/api/v1.2"
        ).rstrip("/")
    )

    def is_configured(self) -> bool:
        return bool(self.api_key and self.property_id)


@dataclass(frozen=True)
class SheetsSettings:
    credentials_path: str = field(
        default_factory=lambda: os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH", "")
    )
    sheet_id: str = field(default_factory=lambda: os.getenv("GOOGLE_SHEET_ID", ""))
    worksheet_name: str = field(
        default_factory=lambda: os.getenv("GOOGLE_SHEET_WORKSHEET_NAME", "Hóspedes")
    )
    name_column: str = field(default_factory=lambda: os.getenv("SHEET_NAME_COLUMN", "nome"))
    secondary_field_column: str = field(
        default_factory=lambda: os.getenv("SHEET_SECONDARY_COLUMN", "cpf")
    )

    def is_configured(self) -> bool:
        return bool(self.credentials_path and self.sheet_id)


@dataclass(frozen=True)
class AppSettings:
    dry_run_default: bool = field(default_factory=lambda: _env_bool("DRY_RUN", True))
    match_score_threshold: float = field(
        default_factory=lambda: _env_float("MATCH_SCORE_THRESHOLD", 0.87)
    )
    history_lookback_years: int = field(
        default_factory=lambda: _env_int("HISTORY_LOOKBACK_YEARS", 5)
    )
    log_file_path: Path = field(
        default_factory=lambda: BASE_DIR / os.getenv("LOG_FILE_PATH", "log.txt")
    )
    field_mapping: dict[str, str] = field(default_factory=_env_field_mapping)


cloudbeds = CloudbedsSettings()
sheets = SheetsSettings()
app = AppSettings()
