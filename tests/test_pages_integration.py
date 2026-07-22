"""Testes de integração das páginas Streamlit via streamlit.testing.v1.AppTest.

Simulam clique real nos botões (buscar, confirmar) sem precisar de uma
API key real do Cloudbeds nem de uma planilha real — os métodos de leitura
do CloudbedsClient/SheetsClient são substituídos por dados fake. Os métodos
de escrita (put_guest/post_reservation_note) rodam de verdade, mas em
dry-run eles nunca chamam a rede — então o caminho de código real de
"gravação" é exercitado, só sem gravar nada.
"""

from __future__ import annotations

import dataclasses
import json

import pytest
from streamlit.testing.v1 import AppTest

from core import config
from core.cloudbeds_client import CloudbedsClient
from core.sheets_client import SheetsClient


@pytest.fixture
def configured(monkeypatch, tmp_path):
    monkeypatch.setattr(
        config,
        "cloudbeds",
        config.CloudbedsSettings(
            api_key="test_key", property_id="1", api_base="https://cloudbeds.invalid/api/v1.2"
        ),
    )
    monkeypatch.setattr(
        config,
        "sheets",
        config.SheetsSettings(
            credentials_path="fake.json",
            sheet_id="fake_sheet",
            worksheet_name="Hóspedes",
            name_column="nome",
            secondary_field_column="email",
        ),
    )
    set_app_settings(monkeypatch, tmp_path)
    return config


def set_app_settings(monkeypatch, tmp_path, **overrides):
    overrides.setdefault("log_file_path", tmp_path / "log.txt")
    monkeypatch.setattr(config, "app", dataclasses.replace(config.app, **overrides))


def read_log(path):
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def button_labeled(at, label):
    return next(b for b in at.button if b.label == label)


def test_home_page_renders_without_errors(configured):
    at = AppTest.from_file("app.py")
    at.run()
    assert not at.exception


def test_ocupacao_page_loads_grid_after_search(configured, monkeypatch):
    reservations = [
        {
            "status": "confirmed",
            "rooms": [
                {
                    "roomID": "1",
                    "roomName": "101",
                    "checkInDate": "2026-07-20",
                    "checkOutDate": "2026-07-23",
                    "guestName": "Maria Silva",
                }
            ],
        }
    ]
    rooms = [{"roomID": "1", "roomName": "101"}]

    monkeypatch.setattr(CloudbedsClient, "get_reservations", lambda self, **kw: reservations)
    monkeypatch.setattr(CloudbedsClient, "get_rooms", lambda self: rooms)

    at = AppTest.from_file("pages/1_Ocupacao.py")
    at.run()
    at.button[0].click().run()

    assert not at.exception
    assert any("carregadas" in s.value for s in at.success)
    assert len(at.dataframe) == 1


def test_autopreenchimento_confirmed_match_dry_run_writes_log(configured, monkeypatch, tmp_path):
    reservation = {
        "guestID": "g1",
        "guestName": "Joao Pereira",
        "guestEmail": "joao@example.com",
        "guestPhone": "11999990000",
        "guestCPF": "",
    }
    sheet_rows = [
        {"nome": "Joao Pereira", "cpf": "111.222.333-44", "email": "joao@example.com"},
    ]

    monkeypatch.setattr(CloudbedsClient, "get_reservation", lambda self, rid: reservation)
    monkeypatch.setattr(SheetsClient, "fetch_rows", lambda self: sheet_rows)
    set_app_settings(monkeypatch, tmp_path, field_mapping={"cpf": "guestCPF"})

    at = AppTest.from_file("pages/2_Autopreenchimento.py")
    at.run()

    at.text_input[0].set_value("RES1").run()
    button_labeled(at, "Buscar hóspede").click().run()
    assert not at.exception

    # segundo campo já vem preenchido com o e-mail da reserva
    button_labeled(at, "Procurar na planilha").click().run()
    assert not at.exception
    assert any("Match confirmado" in md.value for md in at.markdown)

    button_labeled(at, "Simular alteração").click().run()
    assert not at.exception
    assert any("Simulado com sucesso" in s.value for s in at.success)

    entries = read_log(config.app.log_file_path)
    assert len(entries) == 1
    assert entries[0]["field"] == "guestCPF"
    assert entries[0]["after"] == "111.222.333-44"
    assert entries[0]["dry_run"] is True


def test_autopreenchimento_ambiguous_match_requires_manual_pick(configured, monkeypatch, tmp_path):
    """Dois hóspedes com o mesmo nome — o sistema nunca decide sozinho."""
    reservation = {
        "guestID": "g1",
        "guestName": "Maria da Silva Santos",
        "guestEmail": "",
        "guestPhone": "",
        "guestCPF": "",
    }
    sheet_rows = [
        {"nome": "Maria da Silva Santos", "cpf": "111", "email": "maria1@example.com"},
        {"nome": "Maria da Silva Santos", "cpf": "222", "email": "maria2@example.com"},
    ]

    monkeypatch.setattr(CloudbedsClient, "get_reservation", lambda self, rid: reservation)
    monkeypatch.setattr(SheetsClient, "fetch_rows", lambda self: sheet_rows)
    set_app_settings(monkeypatch, tmp_path, field_mapping={"cpf": "guestCPF"})

    at = AppTest.from_file("pages/2_Autopreenchimento.py")
    at.run()
    at.text_input[0].set_value("RES1").run()
    button_labeled(at, "Buscar hóspede").click().run()
    button_labeled(at, "Procurar na planilha").click().run()

    assert not at.exception
    assert any("escolha manual" in md.value for md in at.markdown)
    assert not any(b.label in ("Simular alteração", "Confirmar alteração") for b in at.button)

    at.radio[0].set_value(0).run()  # primeiro candidato da planilha (cpf "111")

    button_labeled(at, "Simular alteração").click().run()
    assert not at.exception

    entries = read_log(config.app.log_file_path)
    assert len(entries) == 1
    assert entries[0]["after"] == "111"


def test_autopreenchimento_not_found_never_writes(configured, monkeypatch, tmp_path):
    reservation = {
        "guestID": "g1",
        "guestName": "Zzzzz Wwwww Completamente Diferente",
        "guestEmail": "",
        "guestPhone": "",
    }
    sheet_rows = [{"nome": "Joao Pereira", "cpf": "111", "email": "joao@example.com"}]

    monkeypatch.setattr(CloudbedsClient, "get_reservation", lambda self, rid: reservation)
    monkeypatch.setattr(SheetsClient, "fetch_rows", lambda self: sheet_rows)
    set_app_settings(monkeypatch, tmp_path)

    at = AppTest.from_file("pages/2_Autopreenchimento.py")
    at.run()
    at.text_input[0].set_value("RES1").run()
    button_labeled(at, "Buscar hóspede").click().run()
    button_labeled(at, "Procurar na planilha").click().run()

    assert not at.exception
    assert any("Nenhum hóspede parecido encontrado" in w.value for w in at.warning)
    assert not any(b.label in ("Simular alteração", "Confirmar alteração") for b in at.button)
    assert not config.app.log_file_path.exists()


def test_historico_page_dry_run_writes_note_log(configured, monkeypatch, tmp_path):
    reservation = {
        "reservationID": "current",
        "guestName": "Maria Silva",
        "guestEmail": "maria@example.com",
        "guestPhone": "",
    }
    all_reservations = [
        {
            "reservationID": "1",
            "status": "checked_out",
            "guestEmail": "maria@example.com",
            "guestPhone": "",
            "checkInDate": "2025-01-10",
        },
        reservation | {"status": "confirmed", "checkInDate": "2026-07-22"},
    ]

    monkeypatch.setattr(CloudbedsClient, "get_reservation", lambda self, rid: reservation)
    monkeypatch.setattr(CloudbedsClient, "get_reservation_notes", lambda self, rid: [])
    monkeypatch.setattr(CloudbedsClient, "get_reservations", lambda self, **kw: all_reservations)
    set_app_settings(monkeypatch, tmp_path)

    at = AppTest.from_file("pages/3_Historico.py")
    at.run()

    at.text_input[0].set_value("current").run()
    button_labeled(at, "Calcular histórico").click().run()
    assert not at.exception
    assert any("1 estadia" in note.value for note in at.markdown if "estadia" in note.value)

    button_labeled(at, "Simular gravação da nota").click().run()
    assert not at.exception
    assert any("Simulado com sucesso" in s.value for s in at.success)

    entries = read_log(config.app.log_file_path)
    assert len(entries) == 1
    assert entries[0]["field"] == "nota"
    assert "1 estadia" in entries[0]["after"]
    assert entries[0]["dry_run"] is True
