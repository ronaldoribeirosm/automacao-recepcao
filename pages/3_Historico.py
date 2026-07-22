"""Função 3 — Histórico de estadias na nota da reserva.

Conta quantas vezes o hóspede já se hospedou (por e-mail/telefone, nunca só
pelo nome) e grava isso como uma nova nota na reserva. Nunca sobrescreve
notas existentes — só adiciona.
"""

from __future__ import annotations

from datetime import date

import streamlit as st

from core import config
from core.audit_log import append_log, make_entry
from core.cloudbeds_client import CloudbedsClient, CloudbedsError
from core.history import count_previous_stays, lookback_start_date
from core.ui import inject_style, render_diff, render_mode_banner

st.set_page_config(page_title="Histórico — Automação Recepção", page_icon="🕓", layout="wide")
inject_style()

st.session_state.setdefault("dry_run", config.app.dry_run_default)
render_mode_banner(st.session_state.dry_run)

st.title("🕓 Histórico de estadias na nota")
st.caption("Só adiciona uma nota — nunca apaga ou sobrescreve notas existentes.")

if not config.cloudbeds.is_configured():
    st.error("Cloudbeds não configurado. Preencha o `.env` antes de usar esta função.")
    st.stop()

reservation_id = st.text_input("ID da reserva no Cloudbeds", placeholder="Ex.: 123456")

if st.button("Calcular histórico", type="primary", disabled=not reservation_id):
    client = CloudbedsClient(settings=config.cloudbeds)
    try:
        with st.spinner("Buscando reserva e histórico no Cloudbeds…"):
            reservation = client.get_reservation(reservation_id)
            existing_notes = client.get_reservation_notes(reservation_id)

            start = lookback_start_date(date.today(), config.app.history_lookback_years)
            all_reservations = client.get_reservations(
                check_in_from=start, check_in_to=date.today()
            )
    except CloudbedsError as exc:
        st.error(f"Erro ao consultar o Cloudbeds: {exc}")
        st.stop()

    if not reservation:
        st.error("Reserva não encontrada.")
        st.stop()

    history = count_previous_stays(
        all_reservations=all_reservations,
        guest_email=reservation.get("guestEmail", ""),
        guest_phone=reservation.get("guestPhone", ""),
        current_reservation_id=reservation_id,
    )

    st.session_state["hist_reservation"] = reservation
    st.session_state["hist_existing_notes"] = existing_notes
    st.session_state["hist_result"] = history

reservation = st.session_state.get("hist_reservation")
history = st.session_state.get("hist_result")

if reservation and history:
    st.subheader("Hóspede")
    col_a, col_b = st.columns(2)
    col_a.metric("Nome", reservation.get("guestName", "—"))
    col_b.metric("Estadias anteriores encontradas", history.previous_stays)

    if history.stay_dates:
        st.write("Datas de check-in das estadias anteriores:")
        st.write(", ".join(history.stay_dates))

    existing_notes = st.session_state.get("hist_existing_notes", [])
    existing_text = (
        "\n".join(n.get("note", "") for n in existing_notes) if existing_notes else ""
    )
    new_note = history.to_note()

    st.subheader("Nota que seria adicionada")
    render_diff(
        "nota da reserva (adiciona, não substitui)",
        existing_text or "(sem notas ainda)",
        new_note,
    )

    button_label = (
        "Simular gravação da nota" if st.session_state.dry_run else "Confirmar gravação da nota"
    )
    confirm = st.button(button_label, type="primary")
    if confirm:
        client = CloudbedsClient(settings=config.cloudbeds)
        result = client.post_reservation_note(
            reservation_id=reservation_id, note=new_note, dry_run=st.session_state.dry_run
        )
        entry = make_entry(
            action="historico_estadias",
            target=f"reserva {reservation_id}",
            field_name="nota",
            before=existing_text,
            after=new_note,
            dry_run=result.dry_run,
        )
        append_log(config.app.log_file_path, entry)

        if result.dry_run:
            st.success("Simulado com sucesso — nada foi gravado (modo teste ligado).")
        else:
            st.success("Nota gravada no Cloudbeds com sucesso.")
