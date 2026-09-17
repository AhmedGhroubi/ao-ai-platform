# app/services/scoring/role_matcher.py

from typing import Dict, List, Optional, Any

from .constants import (
    ROLES_DICTIONNAIRE,
    MATRICE_COMPATIBILITE_ROLES,
    DOMAINES_ROLE
)
from .normalizers import normaliser_experience_texte, contient_expression


def extraire_role_canonique(texte: str) -> Optional[str]:
    if not texte:
        return None

    texte_norm = normaliser_experience_texte(texte)
    candidats = []

    for role_canonique, synonymes in ROLES_DICTIONNAIRE.items():
        for syn in synonymes:
            syn_norm = normaliser_experience_texte(syn)

            if not syn_norm:
                continue

            if contient_expression(texte_norm, syn_norm):
                candidats.append((
                    len(syn_norm.split()),
                    len(syn_norm),
                    role_canonique
                ))

    if not candidats:
        return None

    candidats.sort(reverse=True)

    return candidats[0][2]


def extraire_tous_les_roles_candidat(expert_data: Dict) -> List[str]:
    if not expert_data or not isinstance(expert_data, dict):
        return []

    roles_trouves = set()

    for field in [
        "titre", "poste", "intitule",
        "role_principal", "titre_profil",
        "poste_actuel"
    ]:
        value = expert_data.get(field)

        if isinstance(value, str) and value:
            role = extraire_role_canonique(value)

            if role:
                roles_trouves.add(role)

    experiences = (
        expert_data.get("experiences_professionnelles") or []
    ) + (
        expert_data.get("projets_et_missions") or []
    )

    for exp in experiences:
        if not isinstance(exp, dict):
            continue

        intitule = str(
            exp.get("poste_occupe")
            or exp.get("poste")
            or exp.get("role")
            or exp.get("intitule")
            or ""
        )

        role = extraire_role_canonique(intitule)

        if role:
            roles_trouves.add(role)

    return list(roles_trouves)


def extraire_role_dominant_candidat(expert_data: Dict) -> Optional[str]:
    if not expert_data or not isinstance(expert_data, dict):
        return None

    frequences_roles = {}

    for field in [
        "titre", "poste", "intitule",
        "role_principal", "titre_profil",
        "poste_actuel"
    ]:
        value = expert_data.get(field)

        if isinstance(value, str) and value:
            role = extraire_role_canonique(value)

            if role:
                frequences_roles[role] = frequences_roles.get(role, 0) + 1.5

    experiences = (
        expert_data.get("experiences_professionnelles") or []
    ) + (
        expert_data.get("projets_et_missions") or []
    )

    for exp in experiences:
        if not isinstance(exp, dict):
            continue

        intitule = str(
            exp.get("poste_occupe")
            or exp.get("poste")
            or exp.get("role")
            or exp.get("intitule")
            or ""
        )

        role = extraire_role_canonique(intitule)

        if role:
            frequences_roles[role] = frequences_roles.get(role, 0) + 1

    if not frequences_roles:
        return None

    return max(frequences_roles, key=frequences_roles.get)


def evaluer_compatibilite_roles(
    role_requis: Optional[str],
    role_candidat: Optional[str]
) -> float:

    if not role_requis:
        return 1.0

    if not role_candidat:
        return 0.0

    if role_requis == role_candidat:
        return 1.0

    return MATRICE_COMPATIBILITE_ROLES.get(
        role_requis,
        {}
    ).get(role_candidat, 0.0)


def construire_texte_projet(exp: Dict[str, Any]) -> str:
    if not exp or not isinstance(exp, dict):
        return ""

    champs = [
        exp.get("poste_occupe"),
        exp.get("poste"),
        exp.get("intitule"),
        exp.get("role"),
        exp.get("nom_projet"),
        exp.get("titre_projet"),
        exp.get("description"),
        exp.get("resume"),
        exp.get("environnements_techniques"),
        exp.get("technologies"),
        exp.get("outils"),
        exp.get("taches"),
        exp.get("activites"),
        exp.get("livrables")
    ]

    textes = []

    for champ in champs:
        if isinstance(champ, list):
            textes.extend(str(x) for x in champ if x)
        elif champ:
            textes.append(str(champ))

    return " ".join(textes)


def filtrer_experiences_par_domaine(
    experiences: List[Dict],
    domaine_or_role: str
) -> List[Dict]:

    if not experiences:
        return []

    role_canon = (
        extraire_role_canonique(domaine_or_role)
        or domaine_or_role.lower()
    )

    mots_cles = DOMAINES_ROLE.get(role_canon, [])

    if not mots_cles:
        mots_cles = [
            normaliser_experience_texte(w)
            for w in domaine_or_role.split()
            if len(w) > 3
        ]

    mots_cles_norm = [
        normaliser_experience_texte(m)
        for m in mots_cles
        if m
    ]

    retenues = []

    for exp in experiences:
        if not isinstance(exp, dict):
            continue

        texte = construire_texte_projet(exp)
        texte_norm = normaliser_experience_texte(texte)

        hits = [
            m for m in mots_cles_norm
            if contient_expression(texte_norm, m)
        ]

        if hits:
            exp_copie = dict(exp)
            exp_copie["_score_pertinence"] = min(
                1.0,
                0.4 + 0.2 * len(hits)
            )
            exp_copie["_mots_trouves"] = hits
            retenues.append(exp_copie)

    retenues.sort(
        key=lambda x: x.get("_score_pertinence", 0.0),
        reverse=True
    )

    return retenues