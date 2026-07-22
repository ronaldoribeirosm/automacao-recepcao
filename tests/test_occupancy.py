from datetime import date

from core.occupancy import build_occupancy_grid

RESERVATIONS = [
    {
        "status": "confirmed",
        "guestName": "Maria Silva",
        "assigned": [
            {
                "roomID": "1",
                "roomName": "101",
                "startDate": "2026-07-20",
                "endDate": "2026-07-23",
            }
        ],
    },
    {
        "status": "canceled",
        "guestName": "Reserva Cancelada",
        "assigned": [
            {
                "roomID": "2",
                "roomName": "102",
                "startDate": "2026-07-20",
                "endDate": "2026-07-22",
            }
        ],
    },
]


def test_occupied_room_shows_guest_within_stay_range():
    grid = build_occupancy_grid(
        reservations=RESERVATIONS,
        room_names=["101", "102"],
        start_date=date(2026, 7, 20),
        days=5,
    )
    day1_col = grid.columns[0]
    assert grid.at["101", day1_col] == "Maria Silva"


def test_checkout_day_is_not_occupied():
    grid = build_occupancy_grid(
        reservations=RESERVATIONS,
        room_names=["101"],
        start_date=date(2026, 7, 20),
        days=5,
    )
    checkout_col = grid.columns[3]  # 2026-07-23 == checkout day
    assert grid.at["101", checkout_col] == ""


def test_cancelled_reservation_is_ignored():
    grid = build_occupancy_grid(
        reservations=RESERVATIONS,
        room_names=["102"],
        start_date=date(2026, 7, 20),
        days=5,
    )
    assert (grid.loc["102"] == "").all()


def test_room_not_in_property_list_is_ignored():
    grid = build_occupancy_grid(
        reservations=RESERVATIONS,
        room_names=["999"],
        start_date=date(2026, 7, 20),
        days=5,
    )
    assert (grid.loc["999"] == "").all()
