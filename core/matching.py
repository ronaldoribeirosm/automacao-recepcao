"""Match de hóspede entre o nome digitado no Cloudbeds e a planilha do Sheets.

Regra de segurança do projeto: casar só pelo nome é arriscado (nomes iguais,
acentos, abreviações). Por isso todo match "automático" exige nome parecido
E um segundo dado batendo exatamente (CPF, telefone, e-mail ou data de
nascimento). Quando isso não é possível, o sistema classifica o resultado
como AMBIGUOUS ou NOT_FOUND e devolve a decisão para o humano.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from enum import StrEnum
from typing import Any


def normalize_name(raw: str) -> str:
    """Remove acentos, baixa a caixa e colapsa espaços duplicados."""
    if not raw:
        return ""
    decomposed = unicodedata.normalize("NFKD", raw)
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    lowered = without_accents.strip().lower()
    return re.sub(r"\s+", " ", lowered)


def normalize_secondary(raw: str) -> str:
    """Normaliza CPF/telefone/e-mail para comparação: remove tudo que não é
    letra ou número e baixa a caixa. Isso faz '123.456.789-00' == '12345678900'
    e 'Nome@Email.com' == 'nome@email.com'."""
    if not raw:
        return ""
    return re.sub(r"[^a-z0-9]", "", raw.strip().lower())


def name_similarity(a: str, b: str) -> float:
    """Similaridade 0.0–1.0 entre dois nomes já normalizados."""
    return SequenceMatcher(None, a, b).ratio()


class MatchStatus(StrEnum):
    CONFIRMED = "confirmed"  # nome parecido + segundo dado bateu, exatamente 1 candidato
    AMBIGUOUS = "ambiguous"  # mais de um candidato plausível — decisão manual
    NOT_FOUND = "not_found"  # nenhum candidato — não faz nada


@dataclass
class Candidate:
    row: dict[str, Any]
    name_score: float
    secondary_match: bool


@dataclass
class MatchResult:
    status: MatchStatus
    candidates: list[Candidate]

    @property
    def confirmed_row(self) -> dict[str, Any] | None:
        if self.status == MatchStatus.CONFIRMED and self.candidates:
            return self.candidates[0].row
        return None


def find_guest_match(
    *,
    typed_name: str,
    typed_secondary: str,
    sheet_rows: list[dict[str, Any]],
    name_column: str,
    secondary_column: str,
    score_threshold: float = 0.87,
) -> MatchResult:
    """Compara o nome digitado no Cloudbeds com a planilha.

    - Candidatos com nome acima do threshold E segundo dado idêntico são os
      únicos elegíveis a match automático.
    - 1 candidato elegível -> CONFIRMED.
    - 2+ candidatos elegíveis, ou candidatos de nome sem segundo dado
      suficiente para desempatar -> AMBIGUOUS (mostra todos pra escolha manual).
    - 0 candidatos -> NOT_FOUND.
    """
    norm_typed_name = normalize_name(typed_name)
    norm_typed_secondary = normalize_secondary(typed_secondary)

    scored: list[Candidate] = []
    for row in sheet_rows:
        row_name = normalize_name(str(row.get(name_column, "")))
        if not row_name:
            continue
        score = name_similarity(norm_typed_name, row_name)
        if score < score_threshold:
            continue
        row_secondary = normalize_secondary(str(row.get(secondary_column, "")))
        secondary_match = bool(norm_typed_secondary) and (row_secondary == norm_typed_secondary)
        scored.append(Candidate(row=row, name_score=score, secondary_match=secondary_match))

    if not scored:
        return MatchResult(status=MatchStatus.NOT_FOUND, candidates=[])

    scored.sort(key=lambda c: c.name_score, reverse=True)

    confirmed = [c for c in scored if c.secondary_match]
    if len(confirmed) == 1:
        return MatchResult(status=MatchStatus.CONFIRMED, candidates=confirmed)

    # 0 ou 2+ confirmados por segundo dado: nunca decide sozinho, mostra as opções.
    return MatchResult(status=MatchStatus.AMBIGUOUS, candidates=scored)
