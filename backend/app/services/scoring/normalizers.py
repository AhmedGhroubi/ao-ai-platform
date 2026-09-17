# app/services/scoring/normalizers.py

import re
from typing import Any


def normaliser_texte_langue(texte: str) -> str:
    if not texte:
        return ""

    text = str(texte).lower()

    replacements = {
        "é": "e",
        "è": "e",
        "ê": "e",
        "à": "a",
        "â": "a",
        "ç": "c",
        "î": "i",
        "ï": "i",
        "ô": "o",
        "ö": "o",
        "ù": "u",
        "û": "u",
        "œ": "oe"
    }

    for src, dst in replacements.items():
        text = text.replace(src, dst)

    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def normaliser_experience_texte(texte: str) -> str:
    return normaliser_texte_langue(texte)


def normaliser_nom_geo(val: Any) -> str:
    if val is None:
        return ""

    text = str(val).lower()

    replacements = {
        "é": "e", "è": "e", "ê": "e", "ë": "e",
        "à": "a", "â": "a", "ä": "a",
        "î": "i", "ï": "i",
        "ô": "o", "ö": "o",
        "ù": "u", "û": "u", "ü": "u",
        "ç": "c", "œ": "oe",
        "'": " ",
        "-": " ",
        "/": " ",
        "\\": " ",
        ".": " ",
        ",": " ",
        ";": " ",
    }

    for src, dst in replacements.items():
        text = text.replace(src, dst)

    text = re.sub(r"[^a-z0-9 ]+", " ", text)

    aliases = {
        "cameroon": "cameroun",
        "cote d ivoire": "cote d ivoire",
        "cote divoire": "cote d ivoire",
        "republique du cameroun": "cameroun",
        "republique de cote d ivoire": "cote d ivoire",
    }

    text = " ".join(text.split())

    return aliases.get(text, text)


def contient_expression(texte_norm: str, expression_norm: str) -> bool:
    if not expression_norm:
        return False

    padded_text = f" {texte_norm} "
    padded_expr = f" {expression_norm} "

    return (
        padded_expr in padded_text
        or texte_norm.startswith(expression_norm)
        or texte_norm.endswith(expression_norm)
    )