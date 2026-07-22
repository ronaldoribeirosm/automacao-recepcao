from datetime import date

from core.history import count_previous_stays, lookback_start_date

RESERVATIONS = {
    "1": {"reservationID": "1", "status": "checked_out", "startDate": "2025-01-10"},
    "2": {"reservationID": "2", "status": "checked_out", "startDate": "2024-06-01"},
    "3": {"reservationID": "3", "status": "canceled", "startDate": "2023-01-01"},
    "current": {"reservationID": "current", "status": "confirmed", "startDate": "2026-07-20"},
    "old": {"reservationID": "old", "status": "checked_out", "startDate": "2015-03-03"},
}


def fetch(reservation_id):
    return RESERVATIONS[reservation_id]


def test_counts_only_completed_stays_excluding_current():
    history = count_previous_stays(
        candidate_reservation_ids={"1", "2", "3", "current"},
        current_reservation_id="current",
        fetch_reservation=fetch,
    )
    assert history.previous_stays == 2
    assert history.stay_dates == ["2024-06-01", "2025-01-10"]


def test_zero_stays_note_text():
    history = count_previous_stays(
        candidate_reservation_ids=set(),
        current_reservation_id="x",
        fetch_reservation=fetch,
    )
    assert history.previous_stays == 0
    assert "Primeira estadia" in history.to_note()


def test_multiple_stays_note_text_lists_dates():
    history = count_previous_stays(
        candidate_reservation_ids={"1", "2", "current"},
        current_reservation_id="current",
        fetch_reservation=fetch,
    )
    note = history.to_note()
    assert "2 estadias" in note
    assert "2024-06-01" in note and "2025-01-10" in note


def test_lookback_start_excludes_stays_before_it():
    history = count_previous_stays(
        candidate_reservation_ids={"1", "2", "old"},
        current_reservation_id="current",
        fetch_reservation=fetch,
        lookback_start=date(2020, 1, 1),
    )
    assert history.previous_stays == 2
    assert "2015-03-03" not in history.stay_dates


def test_lookback_start_date_subtracts_years():
    assert lookback_start_date(date(2026, 7, 22), 5) == date(2021, 7, 22)
