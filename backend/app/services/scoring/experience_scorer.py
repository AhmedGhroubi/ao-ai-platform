import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .constants import DOMAINES_ROLE, MOTS_GENERIQUES_SIMILARITE
from .normalizers import normaliser_experience_texte, normaliser_texte_langue
from .role_matcher import (
    construire_texte_projet,
    evaluer_compatibilite_roles,
    extraire_role_canonique,
    filtrer_experiences_par_domaine,
)


def dedupliquer_missions(missions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not missions:
        return []

    uniques = []
    cles_vues = set()

    for mission in missions:
        if not isinstance(mission, dict):
            continue

        nom = normaliser_texte_langue(
            str(mission.get("nom_projet") or mission.get("poste") or mission.get("intitule") or "")
        )
        d_deb = str(mission.get("date_debut") or mission.get("annee") or "")
        cle = f"{nom}_{d_deb}".strip("_")

        if cle and cle in cles_vues:
            continue
        if cle:
            cles_vues.add(cle)

        uniques.append(mission)

    return uniques


def analyser_contexte_experience(texte: str, titre_poste: str = "") -> Dict[str, Any]:
    full_text = f"{texte} {titre_poste}".lower()
    full_norm = normaliser_texte_langue(full_text)
    tokens = [t for t in full_norm.split() if len(t) > 3 and t not in MOTS_GENERIQUES_SIMILARITE]

    return {
        "tokens": set(tokens),
        "role_canonique": extraire_role_canonique(full_text),
    }


def calculer_score_pertinence_mission(
    profil_cible: Dict[str, Any],
    texte_projet: str,
) -> Dict[str, Any]:
    text_proj_norm = normaliser_texte_langue(texte_projet)
    tokens_proj = set([t for t in text_proj_norm.split() if len(t) > 3])

    tokens_cible = profil_cible.get("tokens", set())
    common = tokens_cible.intersection(tokens_proj)

    overlap_score = len(common) / len(tokens_cible) if tokens_cible else 0.0

    role_projet = extraire_role_canonique(texte_projet)
    role_cible = profil_cible.get("role_canonique")

    compat_role = evaluer_compatibilite_roles(role_cible, role_projet) if role_cible else 0.5
    score_final = round(0.5 * overlap_score + 0.5 * compat_role, 4)

    return {
        "score": score_final,
        "mots_communs": list(common),
        "compat_role": compat_role,
    }


def filtrer_missions_similaires(
    projets_expert: List[Dict[str, Any]],
    contexte_cible: str,
    titre_poste: str,
) -> List[Dict[str, Any]]:
    if not projets_expert:
        return []

    cible = str(contexte_cible or "").strip().lower()
    if not cible:
        return []

    profil_cible = analyser_contexte_experience(texte=cible, titre_poste=titre_poste)
    missions_evaluees = []

    for projet in projets_expert:
        if not isinstance(projet, dict):
            continue

        texte_projet = construire_texte_projet(projet)
        if not texte_projet.strip():
            continue

        score = calculer_score_pertinence_mission(profil_cible=profil_cible, texte_projet=texte_projet)

        projet_copie = dict(projet)
        projet_copie["_score_pertinence"] = round(score["score"], 4)
        projet_copie["_details_pertinence"] = score

        if score["score"] >= 0.40:
            missions_evaluees.append(projet_copie)

    missions_evaluees.sort(key=lambda p: p.get("_score_pertinence", 0.0), reverse=True)
    return missions_evaluees


def estimer_annees_sur_projets(
    projets: List[Dict[str, Any]],
    date_reference: Optional[datetime] = None,
) -> float:
    if not projets:
        return 0.0

    periods: List[Tuple[int, int]] = []
    fallback_months = 0.0
    current_date = date_reference or datetime.now()

    for projet in projets:
        if not isinstance(projet, dict):
            continue

        date_debut = str(projet.get("date_debut") or "").strip()
        date_fin = str(projet.get("date_fin") or "").strip()
        annee = str(projet.get("annee") or "").strip()
        periode = str(projet.get("periode") or "").strip()
        date_str = f"{annee} {date_debut} {date_fin} {periode}".lower()

        m_dates = re.findall(r"(\d{1,2})[/.-](\d{4})", date_str)
        if len(m_dates) >= 2:
            start_month = int(m_dates[0][0])
            start_year = int(m_dates[0][1])
            end_month = int(m_dates[1][0])
            end_year = int(m_dates[1][1])

            start = start_year * 12 + (start_month - 1)
            end = end_year * 12 + (end_month - 1) + 1
            if end > start:
                periods.append((start, end))
            continue

        years = re.findall(r"(19\d{2}|20\d{2})", date_str)
        if len(years) >= 2:
            start_year = int(years[0])
            end_year = int(years[1])
            if end_year >= start_year:
                periods.append((start_year * 12, (end_year + 1) * 12))
            continue

        if len(years) == 1:
            year = int(years[0])
            mots_en_cours = [
                "depuis",
                "a ce jour",
                "à ce jour",
                "actuel",
                "actuellement",
                "en cours",
                "encours",
                "present",
                "présent",
                "ongoing",
            ]
            if any(mot in date_str for mot in mots_en_cours):
                start = year * 12
                end = current_date.year * 12 + current_date.month
                if end > start:
                    periods.append((start, end))
            else:
                periods.append((year * 12, (year + 1) * 12))
            continue

        duree_mois = projet.get("duree_mois")
        if duree_mois is not None:
            try:
                valeur = float(duree_mois)
                if valeur > 0:
                    fallback_months += valeur
            except (ValueError, TypeError):
                pass

    periods.sort(key=lambda x: x[0])
    merged = []

    for current in periods:
        if not merged:
            merged.append(current)
            continue

        prev = merged[-1]
        if current[0] <= prev[1]:
            merged[-1] = (prev[0], max(prev[1], current[1]))
        else:
            merged.append(current)

    total_months = sum(end - start for start, end in merged) + fallback_months
    return max(0.0, round(total_months / 12.0, 1))


def extraire_seuil_minimal(text: str) -> Optional[float]:
    text_norm = text.lower()

    lettres_vers_chiffres = {
        " un ": " 1 ",
        " une ": " 1 ",
        " deux ": " 2 ",
        " trois ": " 3 ",
        " quatre ": " 4 ",
        " cinq ": " 5 ",
        " six ": " 6 ",
        " sept ": " 7 ",
        " huit ": " 8 ",
        " neuf ": " 9 ",
        " dix ": " 10 ",
    }
    for key, val in lettres_vers_chiffres.items():
        text_norm = text_norm.replace(key, val)

    patterns = [
        r"(?:>=|>|plus de|au moins|minimum|min|supérieur à|supérieure à|au-dessus de)\s*(\d+(?:\.\d+)?)",
        r"(\d+(?:\.\d+)?)\s*(?:ans?|ann[ée]e?s?)\s*(?:et plus|ou plus|\+)?",
        r"(\d+(?:\.\d+)?)\s*missions?",
    ]
    for pat in patterns:
        match = re.search(pat, text_norm)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass

    return None


def evaluer_regle_echelle_ou_seuil(
    valeur_obtenue: float,
    regle_text: str,
    poids_max: float,
    unite: str,
) -> Tuple[float, str]:
    text = regle_text.lower()

    match_progressive = re.search(r"(\d+)\s*pts?.*?(\d+)\s*ans?.*?\+(\d+)\s*pt.*?jusqu.*?(\d+)", text)
    if match_progressive:
        pts_base = float(match_progressive.group(1))
        seuil_base = float(match_progressive.group(2))
        pts_pas = float(match_progressive.group(3))
        seuil_max = float(match_progressive.group(4))

        if valeur_obtenue < seuil_base:
            return 0.0, f"{valeur_obtenue} {unite} (Inférieur au seuil de base requis : {seuil_base})."

        pts_supp = min(valeur_obtenue - seuil_base, seuil_max - seuil_base) * pts_pas
        score = min(pts_base + pts_supp, poids_max)
        return score, f"{valeur_obtenue} {unite} validé(s) ({score}/{poids_max} pts)."

    seuil = extraire_seuil_minimal(text)
    if seuil is not None:
        if valeur_obtenue >= seuil:
            return poids_max, f"Seuil validé : {valeur_obtenue} {unite} (Requis : >= {seuil})."
        return 0.0, f"Insuffisant : {valeur_obtenue} {unite} (Requis : >= {seuil})."

    if "acquis" in text:
        if valeur_obtenue > 0:
            return poids_max, f"Critère acquis ({valeur_obtenue} {unite})."
        return 0.0, "Non acquis."

    ratio = min(valeur_obtenue / 5.0, 1.0)
    return round(ratio * poids_max, 2), f"{valeur_obtenue} {unite} comptabilisé(s)."


def evaluer_experience_3_niveaux(
    nom_critere: str,
    categorie: str,
    regle_notation: str,
    poids_max: float,
    projets_expert: List[Dict[str, Any]],
    experiences_pro_expert: Optional[List[Dict[str, Any]]] = None,
    contexte_global: str = "",
    titre_poste: str = "",
    annees_exp_total_cv: float = 0.0,
    date_reference: Optional[datetime] = None,
) -> Tuple[float, str, bool]:
    texte_combines = f"{regle_notation} {nom_critere}".lower()

    projets_seuls = [p for p in (projets_expert or []) if isinstance(p, dict)]
    exps_pro_seules = [e for e in (experiences_pro_expert or []) if isinstance(e, dict)]

    source_missions = dedupliquer_missions(projets_seuls + exps_pro_seules)
    source_carrieres = exps_pro_seules if exps_pro_seules else projets_seuls
    toutes_experiences = projets_seuls + exps_pro_seules

    regle_mentionne_annees = bool(re.search(r"\d+(?:[.,]\d+)?\s*(?:ans?|ann[ée]e?s?)\b", texte_combines))

    patterns_exp_globale = [
        r"\bexpérience\s+(professionnelle\s+)?totale\b",
        r"\bexpérience\s+globale\b",
        r"\bexpérience\s+générale\b",
        r"\bancienneté\b",
        r"\bnombre\s+d['’]années\s+d['’]expérience\b",
    ]
    est_exp_globale = any(re.search(pattern, texte_combines) for pattern in patterns_exp_globale)

    mots_specialisation = [
        "analyste fonctionnel",
        "business analyst",
        "chef de projet",
        "chef de mission",
        "directeur de projet",
        "project manager",
        "architecte",
        "développeur",
        "developpeur",
        "administrateur",
        "dba",
        "techlead",
        "tech lead",
        "qualité",
        "qa",
        "testeur",
        "base de données",
        "bases de données",
        "database",
        "application web",
        "applications web",
        "application mobile",
        "applications mobiles",
        "développement web",
        "développement mobile",
        "système d'information",
        "systèmes d'information",
        "informatique",
        "cybersécurité",
        "sécurité informatique",
        "cloud",
        "réseau",
        "erp",
        "crm",
        "intelligence artificielle",
        "data science",
        "big data",
        "analyse fonctionnelle",
        "analyse des besoins",
        "spécifications fonctionnelles",
        "cahier des charges",
        "administration",
        "optimisation",
        "développement",
        "conception",
        "architecture",
        "gestion de projet",
        "pilotage de projet",
        "conduite de projet",
        "déploiement",
        "maintenance",
    ]
    est_specialise = any(terme in texte_combines for terme in mots_specialisation)

    est_exp_globale_pure = est_exp_globale and not est_specialise
    texte_norm = normaliser_experience_texte(texte_combines)
    est_role_similaire = bool(re.search(r"\b(rôle|role|poste|fonction)\s+similaire\b|\ben\s+tant\s+que\b", texte_norm))
    est_mission_similaire = bool(
        re.search(r"\b(mission|missions|projet|projets)\s+(similaire|similaires|semblable|semblables)\b", texte_norm)
    )

    est_niveau_1 = est_mission_similaire and not est_role_similaire

    if est_niveau_1:
        contexte_cible = contexte_global or nom_critere
        projets_pertinents = filtrer_missions_similaires(
            projets_expert=source_missions,
            contexte_cible=contexte_cible,
            titre_poste=titre_poste,
        )
        projets_pertinents = dedupliquer_missions(projets_pertinents)

        if regle_mentionne_annees:
            annees_similaires = estimer_annees_sur_projets(projets_pertinents, date_reference=date_reference)
            score_brut, explication = evaluer_regle_echelle_ou_seuil(
                valeur_obtenue=annees_similaires,
                regle_text=texte_combines,
                poids_max=poids_max,
                unite="ans d'expérience sur missions similaires",
            )

            details = []
            for projet in projets_pertinents[:5]:
                score_mission = projet.get("_score_pertinence", 0.0)
                nom_exp = (
                    projet.get("nom_projet")
                    or f"{projet.get('poste', '')} chez {projet.get('employeur', '')}".strip(" chez ")
                    or "Expérience"
                )
                details.append(f"{nom_exp} ({round(score_mission * 100)}%)")

            if details:
                explication += f" Missions retenues : {', '.join(details)}."

            has_data = annees_similaires > 0
            return (
                score_brut,
                (
                    "Niveau 1 (Missions similaires) : "
                    f"{explication} "
                    f"[{round(annees_similaires, 1)} an(s) calculé(s), "
                    f"{len(projets_pertinents)} mission(s) pertinente(s)]."
                ),
                has_data,
            )

        nb_similaires = len(projets_pertinents)
        score_brut, explication = evaluer_regle_echelle_ou_seuil(
            valeur_obtenue=nb_similaires,
            regle_text=texte_combines,
            poids_max=poids_max,
            unite="mission(s) similaire(s)",
        )

        details = []
        for projet in projets_pertinents[:5]:
            score_mission = projet.get("_score_pertinence", 0.0)
            nom_exp = (
                projet.get("nom_projet")
                or f"{projet.get('poste', '')} chez {projet.get('employeur', '')}".strip(" chez ")
                or "Expérience"
            )
            details.append(f"{nom_exp} ({round(score_mission * 100)}%)")

        if details:
            explication += f" Missions retenues : {', '.join(details)}."

        has_data = nb_similaires > 0
        return score_brut, f"Niveau 1 (Missions similaires) : {explication}", has_data

    if est_exp_globale_pure and regle_mentionne_annees:
        val_exp = annees_exp_total_cv if annees_exp_total_cv > 0 else estimer_annees_sur_projets(
            source_carrieres,
            date_reference=date_reference,
        )

        score_brut, explication = evaluer_regle_echelle_ou_seuil(
            valeur_obtenue=val_exp,
            regle_text=texte_combines,
            poids_max=poids_max,
            unite="ans (expérience globale)",
        )

        has_data = val_exp > 0
        return score_brut, f"Niveau 3 (Expérience professionnelle globale) : {explication}", has_data

    role_spec = extraire_role_canonique(nom_critere) or extraire_role_canonique(titre_poste)

    if role_spec and role_spec in DOMAINES_ROLE:
        projets_pertinents = filtrer_experiences_par_domaine(
            experiences=toutes_experiences,
            domaine_or_role=role_spec,
        )
    else:
        projets_pertinents = filtrer_missions_similaires(
            projets_expert=toutes_experiences,
            contexte_cible=nom_critere,
            titre_poste=titre_poste,
        )

    projets_pertinents = dedupliquer_missions(projets_pertinents)

    if regle_mentionne_annees:
        annees_specifiques = estimer_annees_sur_projets(projets_pertinents, date_reference=date_reference)

        score_brut, explication = evaluer_regle_echelle_ou_seuil(
            valeur_obtenue=annees_specifiques,
            regle_text=texte_combines,
            poids_max=poids_max,
            unite="ans (expérience spécialisée)",
        )

        details = []
        for projet in projets_pertinents[:5]:
            score_mission = projet.get("_score_pertinence", 0.0)
            nom_exp = (
                projet.get("nom_projet")
                or f"{projet.get('poste', '')} chez {projet.get('employeur', '')}".strip(" chez ")
                or "Expérience"
            )
            details.append(f"{nom_exp} ({round(score_mission * 100)}%)")

        if details:
            explication += f" Expériences retenues : {', '.join(details)}."

        has_data = len(projets_pertinents) > 0
        return (
            score_brut,
            (
                f"Niveau 2 (Expérience spécialisée '{nom_critere}') : {explication} "
                f"[{round(annees_specifiques, 1)} an(s) calculé(s) sur {len(projets_pertinents)} expérience(s) pertinente(s)]."
            ),
            has_data,
        )

    has_data = len(projets_pertinents) > 0
    nb_projets = len(projets_pertinents)

    score_brut, explication = evaluer_regle_echelle_ou_seuil(
        valeur_obtenue=nb_projets,
        regle_text=texte_combines,
        poids_max=poids_max,
        unite="projet(s) ou expérience(s) spécialisée(s)",
    )

    details = []
    for projet in projets_pertinents[:5]:
        score_mission = projet.get("_score_pertinence", 0.0)
        nom_exp = (
            projet.get("nom_projet")
            or f"{projet.get('poste', '')} chez {projet.get('employeur', '')}".strip(" chez ")
            or "Expérience"
        )
        details.append(f"{nom_exp} ({round(score_mission * 100)}%)")

    if details:
        explication += f" Expériences retenues : {', '.join(details)}."

    return (
        score_brut,
        f"Niveau 2 (Expérience spécialisée '{nom_critere}') : {explication} [{nb_projets} expérience(s) pertinente(s)].",
        has_data,
    )


# Backward-compatible aliases for existing imports.
_dedupliquer_missions = dedupliquer_missions
_analyser_contexte_experience = analyser_contexte_experience
_calculer_score_pertinence_mission = calculer_score_pertinence_mission
_filtrer_missions_similaires = filtrer_missions_similaires
_estimer_annees_sur_projets = estimer_annees_sur_projets
_extraire_seuil_minimal = extraire_seuil_minimal
_evaluer_regle_echelle_ou_seuil = evaluer_regle_echelle_ou_seuil
_evaluer_experience_3_niveaux = evaluer_experience_3_niveaux
