from datetime import date

from core.history import count_previous_stays, lookback_start_date

ALL_RESERVATIONS = [
    {
        "reservationID": "1",
        "status": "checked_out",
        "guestEmail": "maria@example.com",
        "guestPhone": "",
        "checkInDate": "2025-01-10",
    },
    {
        "reservationID": "2",
        "status": "checked_out",
        "guestEmail": "maria@example.com",
        "guestPhone": "",
        "checkInDate": "2024-06-01",
    },
    {
        "reservationID": "3",
        "status": "cancelled",
        "guestEmail": "maria@example.com",
        "guestPhone": "",
        "checkInDate": "2023-01-01",
    },
    {
        "reservationID": "current",
        "status": "confirmed",
        "guestEmail": "maria@example.com",
        "guestPhone": "",
        "checkInDate": "2026-07-20",
    },
    {
        "reservationID": "4",
        "status": "checked_out",
        "guestEmail": "outra@example.com",
        "guestPhone": "",
        "checkInDate": "2025-05-05",
    },
]


def test_counts_only_completed_stays_of_same_guest_excluding_current():
    history = count_previous_stays(
        all_reservations=ALL_RESERVATIONS,
        guest_email="maria@example.com",
        guest_phone="",
        current_reservation_id="current",
    )
    assert history.previous_stays == 2
    assert history.stay_dates == ["2024-06-01", "2025-01-10"]


def test_zero_stays_note_text():
    history = count_previous_stays(
        all_reservations=[],
        guest_email="ninguem@example.com",
        guest_phone="",
        current_reservation_id="x",
    )
    assert history.previous_stays == 0
    assert "Primeira estadia" in history.to_note()


def test_multiple_stays_note_text_lists_dates():
    history = count_previous_stays(
        all_reservations=ALL_RESERVATIONS,
        guest_email="maria@example.com",
        guest_phone="",
        current_reservation_id="current",
    )
    note = history.to_note()
    assert "2 estadias" in note
    assert "2024-06-01" in note and "2025-01-10" in note


def test_lookback_start_date_subtracts_years():
    assert lookback_start_date(date(2026, 7, 22), 5) == date(2021, 7, 22)
