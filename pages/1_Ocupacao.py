"""Função 1 — Planilha de ocupação (7 dias). Só leitura."""

from __future__ import annotations

from datetime import date, timedelta
from io import BytesIO

import streamlit as st

from core import config
from core.cloudbeds_client import CloudbedsClient, CloudbedsError
from core.occupancy import build_occupancy_grid
from core.ui import inject_style, render_mode_banner

st.set_page_config(page_title="Ocupação — Automação Recepção", page_icon="📊", layout="wide")
inject_style()

st.session_state.setdefault("dry_run", config.app.dry_run_default)
render_mode_banner(st.session_state.dry_run)

st.title("📊 Ocupação — próximos 7 dias")
st.caption("Só leitura. Nenhuma escrita acontece nesta página.")

if not config.cloudbeds.is_configured():
    st.error(
        "Cloudbeds não configurado. Preencha `CLOUDBEDS_API_KEY` e "
        "`CLOUDBEDS_PROPERTY_ID` no `.env`."
    )
    st.stop()

start_date = st.date_input("Início do período", value=date.today())
days = st.slider("Quantos dias mostrar", min_value=3, max_value=14, value=7)

MAX_STAY_LOOKBACK_DAYS = 30  # cobre reservas que já entraram antes da janela e seguem hospedadas
CANCELLED_STATUSES = {"canceled", "cancelled", "no_show", "no-show"}

if st.button("Buscar ocupação", type="primary"):
    client = CloudbedsClient(settings=config.cloudbeds)
    window_end = start_date + timedelta(days=days)
    try:
        with st.spinner("Buscando reservas no Cloudbeds…"):
            candidates = client.get_reservations(
                check_in_from=start_date - timedelta(days=MAX_STAY_LOOKBACK_DAYS),
                check_in_to=window_end,
            )
            rooms = client.get_rooms()
    except CloudbedsError as exc:
        st.error(f"Erro ao consultar o Cloudbeds: {exc}")
        st.stop()

    room_names = [r.get("roomName") for r in rooms if r.get("roomName")]
    if not room_names:
        st.warning("Nenhum quarto retornado pelo Cloudbeds — confira o escopo 'Acomodação (Ler)'.")
        st.stop()

    # getReservations (lista) não traz quarto/datas por quarto — só o
    # getReservation individual traz o array "assigned". Por isso: filtra
    # candidatos relevantes na lista (barato) e só então busca o detalhe
    # de cada um (mais caro), em vez de detalhar as 14 mil reservas da conta.
    relevant = []
    for res in candidates:
        if str(res.get("status", "")).lower() in CANCELLED_STATUSES:
            continue
        try:
            end = date.fromisoformat(res["endDate"][:10])
        except (KeyError, ValueError):
            continue
        if end > start_date:
            relevant.append(res)

    detailed = []
    try:
        with st.spinner(f"Detalhando {len(relevant)} reservas…"):
            for res in relevant:
                detailed.append(client.get_reservation(res["reservationID"]))
    except CloudbedsError as exc:
        st.error(f"Erro ao detalhar reservas: {exc}")
        st.stop()

    grid = build_occupancy_grid(
        reservations=detailed,
        room_names=room_names,
        start_date=start_date,
        days=days,
    )

    st.session_state["occupancy_grid"] = grid
    st.success(f"{len(detailed)} reservas carregadas, {len(room_names)} quartos.")

if "occupancy_grid" in st.session_state:
    grid = st.session_state["occupancy_grid"]
    st.dataframe(grid, width="stretch")

    buffer = BytesIO()
    grid.to_excel(buffer, sheet_name="Ocupação")
    st.download_button(
        "Baixar como Excel",
        data=buffer.getvalue(),
        file_name=f"ocupacao_{start_date.isoformat()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
