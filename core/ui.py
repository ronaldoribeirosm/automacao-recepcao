"""Componentes de UI compartilhados entre as páginas do Streamlit."""

from __future__ import annotations

from typing import Any

import streamlit as st

from core.config import BASE_DIR

_STYLE_PATH = BASE_DIR / "assets" / "style.css"


def inject_style() -> None:
    css = _STYLE_PATH.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def render_mode_banner(dry_run: bool) -> None:
    if dry_run:
        st.markdown(
            '<div class="modo-banner modo-banner--teste">'
            "🧪 MODO TESTE (dry-run) — nada é gravado no Cloudbeds, só simulado."
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="modo-banner modo-banner--producao">'
            "⚠️ MODO PRODUÇÃO — as ações abaixo gravam de verdade no Cloudbeds."
            "</div>",
            unsafe_allow_html=True,
        )


def render_diff(label: str, before: Any, after: Any) -> None:
    before_display = "(vazio)" if before in (None, "") else str(before)
    st.markdown(
        f"""
        <div class="diff-row">
            <span class="diff-row__label">{label}</span>
            <span class="diff-row__before">{before_display}</span>
            <span class="diff-row__arrow">→</span>
            <span class="diff-row__after">{after}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_match_badge(status: str) -> str:
    mapping = {
        "confirmed": ('<span class="badge badge--confirmed">✓ Match confirmado</span>'),
        "ambiguous": (
            '<span class="badge badge--ambiguous">⚠ Mais de um candidato — escolha manual</span>'
        ),
        "not_found": ('<span class="badge badge--not-found">✕ Não encontrado</span>'),
    }
    return mapping.get(status, "")
