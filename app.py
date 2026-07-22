"""Automação Recepção — ponto de entrada do Streamlit.

Três funções, todas via API oficial do Cloudbeds — nunca simula clique na
tela deles. Nenhuma função usa endpoint de exclusão.
"""

from __future__ import annotations

import streamlit as st

from core import config
from core.ui import inject_style, render_mode_banner

st.set_page_config(
    page_title="Automação Recepção",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_style()

if "dry_run" not in st.session_state:
    st.session_state.dry_run = config.app.dry_run_default

with st.sidebar:
    st.subheader("Modo de operação")
    st.session_state.dry_run = st.toggle(
        "Modo teste (dry-run)",
        value=st.session_state.dry_run,
        help="Desligado = grava de verdade no Cloudbeds. Deixe ligado até validar tudo.",
    )
    st.caption(
        "Enquanto ligado, o sistema só mostra o que faria — nenhuma escrita real "
        "acontece no Cloudbeds."
    )

render_mode_banner(st.session_state.dry_run)

st.title("Automação Recepção")
st.caption("Cloudbeds + Google Sheets — leitura em primeiro lugar, escrita só com confirmação.")

st.divider()

col1, col2, col3 = st.columns(3, gap="large")

with col1:
    st.markdown("### 📊 Ocupação")
    st.write("Planilha de ocupação dos próximos 7 dias, gerada a partir das reservas.")
    st.caption("Só leitura.")
    st.page_link("pages/1_Ocupacao.py", label="Abrir", icon="➡️")

with col2:
    st.markdown("### 🧾 Autopreenchimento")
    st.write("Casa o hóspede da reserva com a planilha e sugere os dados pra preencher.")
    st.caption("Leitura na planilha + escrita nos campos do hóspede.")
    st.page_link("pages/2_Autopreenchimento.py", label="Abrir", icon="➡️")

with col3:
    st.markdown("### 🕓 Histórico de estadias")
    st.write("Conta quantas vezes o hóspede já se hospedou e grava isso na nota da reserva.")
    st.caption("Leitura de reservas + escrita só no campo da nota.")
    st.page_link("pages/3_Historico.py", label="Abrir", icon="➡️")

st.divider()

with st.expander("Status da configuração"):
    cb_ok = config.cloudbeds.is_configured()
    sh_ok = config.sheets.is_configured()
    st.write(f"{'✅' if cb_ok else '❌'} Cloudbeds (API key + property ID)")
    st.write(f"{'✅' if sh_ok else '❌'} Google Sheets (credencial + ID da planilha)")
    if not (cb_ok and sh_ok):
        st.info(
            "Preencha o arquivo `.env` (veja `.env.example`) antes de usar as funções "
            "que dependem dessas integrações."
        )

st.caption(
    "Regra de ouro: este sistema nunca faz DELETE em nada — nenhuma das três "
    "funções usa endpoint de exclusão."
)
