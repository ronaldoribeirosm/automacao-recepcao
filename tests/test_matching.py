from core.matching import (
    MatchStatus,
    find_guest_match,
    name_similarity,
    normalize_name,
    normalize_secondary,
)

SHEET_ROWS = [
    {"nome": "Maria da Silva Santos", "cpf": "123.456.789-00", "email": "maria@example.com"},
    {"nome": "Maria da Silva Santos", "cpf": "987.654.321-00", "email": "outra.maria@example.com"},
    {"nome": "João Pereira", "cpf": "111.222.333-44", "email": "joao@example.com"},
]


def test_normalize_name_strips_accents_case_and_spaces():
    assert normalize_name("  José  DA Silva  ") == "jose da silva"


def test_normalize_secondary_ignores_formatting():
    assert normalize_secondary("123.456.789-00") == normalize_secondary("12345678900")


def test_name_similarity_identical_is_one():
    assert name_similarity("maria silva", "maria silva") == 1.0


def test_confirmed_when_name_and_secondary_match_exactly_one():
    result = find_guest_match(
        typed_name="João Pereira",
        typed_secondary="111.222.333-44",
        sheet_rows=SHEET_ROWS,
        name_column="nome",
        secondary_column="cpf",
    )
    assert result.status == MatchStatus.CONFIRMED
    assert result.confirmed_row["email"] == "joao@example.com"


def test_ambiguous_when_two_namesakes_and_no_secondary_given():
    result = find_guest_match(
        typed_name="Maria da Silva Santos",
        typed_secondary="",
        sheet_rows=SHEET_ROWS,
        name_column="nome",
        secondary_column="cpf",
    )
    assert result.status == MatchStatus.AMBIGUOUS
    assert len(result.candidates) == 2


def test_confirmed_disambiguates_namesakes_via_secondary_field():
    result = find_guest_match(
        typed_name="Maria da Silva Santos",
        typed_secondary="987.654.321-00",
        sheet_rows=SHEET_ROWS,
        name_column="nome",
        secondary_column="cpf",
    )
    assert result.status == MatchStatus.CONFIRMED
    assert result.confirmed_row["email"] == "outra.maria@example.com"


def test_not_found_when_name_too_different():
    result = find_guest_match(
        typed_name="Zzzzz Wwwww",
        typed_secondary="",
        sheet_rows=SHEET_ROWS,
        name_column="nome",
        secondary_column="cpf",
    )
    assert result.status == MatchStatus.NOT_FOUND
    assert result.candidates == []


def test_ambiguous_when_secondary_matches_two_rows_never_auto_decides():
    rows = [
        {"nome": "Ana Costa", "cpf": "555.555.555-55"},
        {"nome": "Ana Costa", "cpf": "555.555.555-55"},
    ]
    result = find_guest_match(
        typed_name="Ana Costa",
        typed_secondary="555.555.555-55",
        sheet_rows=rows,
        name_column="nome",
        secondary_column="cpf",
    )
    assert result.status == MatchStatus.AMBIGUOUS
