"""Função 2 — Autopreenchimento de hóspede.

Leitura na planilha do Google Sheets + escrita só nos campos do hóspede no
Cloudbeds, e só depois de confirmação manual. Nunca decide sozinho quando há
mais de um candidato plausível.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from core import config
from core.audit_log import append_log, make_entry
from core.cloudbeds_client import CloudbedsClient, CloudbedsError, extract_main_guest
from core.matching import MatchStatus, find_guest_match
from core.sheets_client import SheetsClient, SheetsError
from core.ui import inject_style, render_diff, render_match_badge, render_mode_banner

st.set_page_config(
    page_title="Autopreenchimento — Automação Recepção", page_icon="🧾", layout="wide"
)
inject_style()

st.session_state.setdefault("dry_run", config.app.dry_run_default)
render_mode_banner(st.session_state.dry_run)

st.title("🧾 Autopreenchimento de hóspede")
st.caption(
    "Busca o hóspede da reserva na planilha e sugere os dados que faltam. "
    "Só grava depois que você confirmar."
)

if not config.cloudbeds.is_configured() or not config.sheets.is_configured():
    st.error(
        "Configure o Cloudbeds e o Google Sheets no `.env` antes de usar esta função "
        "(veja a página inicial → Status da configuração)."
    )
    st.stop()

reservation_id = st.text_input("ID da reserva no Cloudbeds", placeholder="Ex.: 123456")

if st.button("Buscar hóspede", type="primary", disabled=not reservation_id):
    client = CloudbedsClient(settings=config.cloudbeds)
    try:
        with st.spinner("Buscando reserva no Cloudbeds…"):
            reservation = client.get_reservation(reservation_id)
    except CloudbedsError as exc:
        st.error(f"Erro ao buscar a reserva: {exc}")
        st.stop()

    if not reservation:
        st.error("Reserva não encontrada.")
        st.stop()

    st.session_state["af_reservation"] = reservation
    st.session_state.pop("af_match", None)

reservation = st.session_state.get("af_reservation")

if reservation:
    main_guest = extract_main_guest(reservation)
    guest_name = main_guest["guestName"]
    guest_email = main_guest["guestEmail"]
    guest_phone = main_guest["guestPhone"]
    guest_id = main_guest["guestID"]

    st.subheader("Hóspede na reserva")
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Nome", guest_name or "—")
    col_b.metric("E-mail", guest_email or "—")
    col_c.metric("Telefone", guest_phone or "—")

    secondary_label = config.sheets.secondary_field_column
    secondary_cb_field = config.app.field_mapping.get(secondary_label)
    secondary_from_cloudbeds = main_guest.get(secondary_cb_field, "") if secondary_cb_field else ""
    secondary_default = secondary_from_cloudbeds or guest_email or guest_phone
    typed_secondary = st.text_input(
        f"Segundo dado pra confirmar o match (planilha usa a coluna '{secondary_label}')",
        value=secondary_default,
        help="Precisa bater exatamente com a planilha — senão o sistema não decide sozinho.",
    )

    if st.button("Procurar na planilha"):
        try:
            with st.spinner("Lendo a planilha do Google Sheets…"):
                rows = SheetsClient(settings=config.sheets).fetch_rows()
        except SheetsError as exc:
            st.error(f"Erro ao ler a planilha: {exc}")
            st.stop()

        result = find_guest_match(
            typed_name=guest_name,
            typed_secondary=typed_secondary,
            sheet_rows=rows,
            name_column=config.sheets.name_column,
            secondary_column=config.sheets.secondary_field_column,
            score_threshold=config.app.match_score_threshold,
        )
        st.session_state["af_match"] = result

    match = st.session_state.get("af_match")
    if match is not None:
        st.markdown(render_match_badge(match.status.value), unsafe_allow_html=True)

        chosen_row: dict[str, Any] | None = None

        if match.status == MatchStatus.NOT_FOUND:
            st.warning("Nenhum hóspede parecido encontrado na planilha. Nada será alterado.")

        elif match.status == MatchStatus.CONFIRMED:
            chosen_row = match.confirmed_row
            st.success(
                f"1 candidato confirmado (similaridade de nome: "
                f"{match.candidates[0].name_score:.0%})."
            )

        elif match.status == MatchStatus.AMBIGUOUS:
            st.warning(
                "Mais de uma possibilidade — escolha manualmente qual hóspede é o certo, "
                "ou nenhum se não for nenhum deles."
            )
            def _describe(index: int) -> str:
                if index == -1:
                    return "Nenhum destes"
                c = match.candidates[index]
                secondary_note = ", segundo dado bate" if c.secondary_match else ""
                nome = c.row.get(config.sheets.name_column, "?")
                return (
                    f"{nome} (similaridade {c.name_score:.0%}{secondary_note}) "
                    f"— linha {index + 1} da planilha"
                )

            picked_index = st.radio(
                "Candidatos",
                options=[-1, *range(len(match.candidates))],
                format_func=_describe,
            )
            if picked_index != -1:
                chosen_row = match.candidates[picked_index].row

        if chosen_row:
            fields_to_write: dict[str, Any] = {}
            st.subheader("O que seria alterado")
            for sheet_col, cb_field in config.app.field_mapping.items():
                new_value = str(chosen_row.get(sheet_col, "")).strip()
                if not new_value:
                    continue
                current_value = main_guest.get(cb_field, "")
                if str(current_value).strip() == new_value:
                    continue
                fields_to_write[cb_field] = new_value
                render_diff(cb_field, current_value, new_value)

            if not fields_to_write:
                st.info("Nada a atualizar — todos os campos já estão preenchidos igual à planilha.")
            else:
                confirm = st.button(
                    "Confirmar alteração" if not st.session_state.dry_run else "Simular alteração",
                    type="primary",
                )
                if confirm:
                    client = CloudbedsClient(settings=config.cloudbeds)
                    result = client.put_guest(
                        guest_id=guest_id,
                        reservation_id=reservation_id,
                        fields=fields_to_write,
                        dry_run=st.session_state.dry_run,
                    )
                    for cb_field, new_value in fields_to_write.items():
                        entry = make_entry(
                            action="autopreenchimento",
                            target=f"reserva {reservation_id} / hóspede {guest_id}",
                            field_name=cb_field,
                            before=main_guest.get(cb_field, ""),
                            after=new_value,
                            dry_run=result.dry_run,
                        )
                        append_log(config.app.log_file_path, entry)

                    if result.dry_run:
                        st.success("Simulado com sucesso — nada foi gravado (modo teste ligado).")
                    else:
                        st.success("Gravado no Cloudbeds com sucesso.")
                    st.session_state.pop("af_match", None)
