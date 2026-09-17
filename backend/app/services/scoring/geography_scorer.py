import re
from typing import Any, Dict, List, Optional, Tuple

from .common import get_val
from .normalizers import normaliser_nom_geo


def nettoyer_regions_ciblees(raw: Any) -> List[str]:
    if not raw:
        return []
    if isinstance(raw, list):
        return [normaliser_nom_geo(r) for r in raw if r]
    if isinstance(raw, str):
        return [normaliser_nom_geo(r) for r in re.split(r"[;,]+", raw) if r.strip()]
    return []


def extraire_zones_cibles_ao(
    geo_context: Optional[Any],
    profile: Optional[Any] = None,
    contexte_global: str = "",
) -> List[str]:
    targets = []

    if geo_context is not None:
        if isinstance(geo_context, dict):
            for key in [
                "scope_geographique",
                "regions_ciblees",
                "pays_cibles",
                "pays_sous_region",
                "zones_cibles_ao",
                "pays",
                "scope",
            ]:
                if key in geo_context:
                    targets.extend(nettoyer_regions_ciblees(geo_context.get(key)))
        else:
            targets = nettoyer_regions_ciblees(geo_context)

    if not targets and profile is not None:
        for key in ["geo_context", "scope_geographique", "regions_ciblees", "pays_cibles", "pays"]:
            val = get_val(profile, key)
            if val:
                targets.extend(nettoyer_regions_ciblees(val))

    if not targets and contexte_global:
        pays_courants = [
            "cameroun",
            "cote d'ivoire",
            "côte d'ivoire",
            "senegal",
            "sénégal",
            "mali",
            "burkina faso",
            "guinee",
            "guinée",
            "togo",
            "benin",
            "bénin",
            "niger",
            "tchad",
            "gabon",
            "congo",
            "rdc",
            "tunisie",
            "maroc",
            "algerie",
            "algérie",
            "france",
            "afrique de l'ouest",
            "afrique centrale",
        ]
        text_norm = normaliser_nom_geo(contexte_global)
        for pays in pays_courants:
            pays_norm = normaliser_nom_geo(pays)
            if pays_norm in text_norm:
                targets.append(pays_norm)

    return list(set(targets))


def evaluer_region(
    expert_data: Dict[str, Any],
    nom_critere: str,
    regle_text: str,
    poids_max: float,
    geo_context: Optional[Any] = None,
) -> Tuple[float, str, bool]:
    del nom_critere, regle_text
    targets = extraire_zones_cibles_ao(geo_context)
    if not targets:
        return poids_max, "Aucune restriction géographique détectée.", True

    exp_locations = []
    for exp in (expert_data.get("experiences_professionnelles") or []) + (expert_data.get("projets_et_missions") or []):
        if isinstance(exp, dict):
            loc = exp.get("pays") or exp.get("lieu") or exp.get("region")
            if loc:
                exp_locations.append(normaliser_nom_geo(loc))

    nat = normaliser_nom_geo(expert_data.get("nationalite") or "")
    if nat:
        exp_locations.append(nat)

    matched = any(any(t in loc for t in targets) for loc in exp_locations if loc)
    if matched:
        return poids_max, f"Expérience / localisation dans la zone cible validée ({', '.join(targets)}).", True
    return 0.0, f"Aucune expérience documentée dans la zone cible ({', '.join(targets)}).", bool(exp_locations)


# Backward-compatible aliases for existing imports.
_nettoyer_regions_ciblees = nettoyer_regions_ciblees
_extraire_zones_cibles_ao = extraire_zones_cibles_ao
_evaluer_region = evaluer_region

