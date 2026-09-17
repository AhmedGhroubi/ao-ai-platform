import re
def _extraire_seuil(nom_critere: str, regle_notation: str) -> int:
    """
    Cherche d'abord >= N dans regle_notation (source fiable),
    puis dans le libellé, puis fallback à 3.
    """
    # Pattern prioritaire : >= N ou ≥ N (présent dans presque toutes les règles AO)
    pattern_seuil = re.compile(r'>=\s*(\d+)|≥\s*(\d+)')

    for texte in [regle_notation, nom_critere]:
        m = pattern_seuil.search(texte or "")
        if m:
            return int(m.group(1) or m.group(2))

    # Fallback : premier nombre dans le libellé (ex: "7 ans d'expérience")
    m = re.search(r'(\d+)', nom_critere or "")
    if m:
        return int(m.group(1))

    return 3   # défaut conservateur