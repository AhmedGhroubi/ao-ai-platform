# app/services/scoring/language_scorer.py

from typing import List, Tuple, Dict, Any

from app.services.scoring.normalizers import normaliser_texte_langue



LANGUAGE_MAPPING = {
    "francais": ["francais", "francophone", "french"],
    "anglais": ["anglais", "english"],
    "arabe": ["arabe", "arabic"],
    "espagnol": ["espagnol", "spanish"],
    "portugais": ["portugais", "portuguese"],
    "allemand": ["allemand", "german"],
    "italien": ["italien", "italian"],
    "russe": ["russe", "russian"],
    "chinois": ["chinois", "chinese"],
}


def extraire_langues_requises(texte: str) -> List[str]:
    normalized = normaliser_texte_langue(texte)

    tokens = set(normalized.split())

    langues = []

    for langue, aliases in LANGUAGE_MAPPING.items():
        if any(alias in tokens for alias in aliases):
            langues.append(langue)

    return langues


def evaluer_critere_langue(
    expert_data: Dict[str, Any],
    nom_critere: str,
    regle_text: str,
    poids_max: float
) -> Tuple[float, str, bool]:

    texte = f"{nom_critere} {regle_text}".lower()

    langues_requises = extraire_langues_requises(texte)

    expert_langues = expert_data.get("langues", []) or []

    expert_langues_canon = []

    for langue in expert_langues:
        expert_langues_canon.extend(
            extraire_langues_requises(str(langue))
        )

    has_data = bool(expert_langues)

    if langues_requises:

        if " ou " in texte or " or " in texte or "et/ou" in texte:
            matched = any(
                lang in expert_langues_canon
                for lang in langues_requises
            )
        else:
            matched = all(
                lang in expert_langues_canon
                for lang in langues_requises
            )

        if matched:
            return (
                poids_max,
                f"Langue(s) requise(s) validée(s) : {', '.join(langues_requises)}.",
                has_data
            )

        return (
            0.0,
            f"Langue(s) requise(s) non satisfaites : {', '.join(langues_requises)}.",
            has_data
        )

    if expert_langues_canon:
        return (
            poids_max,
            "Langue(s) maîtrisée(s) renseignée(s).",
            has_data
        )

    return 0.0, "Aucune langue renseignée.", has_data