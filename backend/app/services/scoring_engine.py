import re
from typing import Any, Dict, List, Optional, Tuple

from app.services.language_scorer import (
    evaluer_critere_langue,
    extraire_langues_requises,
)
from app.services.scoring.certification_scorer import (
    analyser_exigence_certification,
    evaluer_certification_algo,
    extraire_seuil_certifications,
    verifier_organisme_reconnu,
    verifier_validite_certification,
)
from app.services.scoring.common import get_val
from app.services.scoring.constants import (
    CERTIFICATION_DOMAINES,
    DIPLOME_DOMAINES,
    DOMAINES_ROLE,
    MATRICE_COMPATIBILITE_ROLES,
    MOTS_GENERIQUES_SIMILARITE,
    NIVEAUX_ACADEMIQUES,
    ORGANISMES_RECONNUS,
    ROLES_DICTIONNAIRE,
)
from app.services.scoring.diploma_scorer import (
    analyser_regle_diplome,
    evaluer_correspondance_domaine,
    evaluer_diplome_algo,
    extraire_niveau_numerique,
)
from app.services.scoring.experience_scorer import (
    analyser_contexte_experience,
    calculer_score_pertinence_mission,
    dedupliquer_missions,
    estimer_annees_sur_projets,
    evaluer_experience_3_niveaux,
    evaluer_regle_echelle_ou_seuil,
    extraire_seuil_minimal,
    filtrer_missions_similaires,
)
from app.services.scoring.geography_scorer import (
    evaluer_region,
    extraire_zones_cibles_ao,
    nettoyer_regions_ciblees,
)
from app.services.scoring.normalizers import (
    contient_expression,
    normaliser_experience_texte,
    normaliser_nom_geo,
    normaliser_texte_langue,
)
from app.services.scoring.role_matcher import (
    construire_texte_projet,
    evaluer_compatibilite_roles,
    extraire_role_canonique,
    extraire_role_dominant_candidat,
    extraire_tous_les_roles_candidat,
    filtrer_experiences_par_domaine,
)


class ScoringEngine:
    """Façade de compatibilité qui délègue vers les modules de scoring spécialisés."""

    _MOTS_GENERIQUES_SIMILARITE = MOTS_GENERIQUES_SIMILARITE
    ROLES_DICTIONNAIRE = ROLES_DICTIONNAIRE
    MATRICE_COMPATIBILITE_ROLES = MATRICE_COMPATIBILITE_ROLES
    DOMAINES_ROLE = DOMAINES_ROLE
    DIPLOME_DOMAINES = DIPLOME_DOMAINES
    CERTIFICATION_DOMAINES = CERTIFICATION_DOMAINES
    ORGANISMES_RECONNUS = ORGANISMES_RECONNUS
    NIVEAUX_ACADEMIQUES = NIVEAUX_ACADEMIQUES

    @staticmethod
    def _get_val(obj: Any, key: str, default: Any = None) -> Any:
        return get_val(obj, key, default)

    @staticmethod
    def _extract_poids_max(critere: Any) -> float:
        pmax = get_val(critere, "points_maximum")
        if pmax is not None:
            try:
                val = float(pmax)
                if val > 0:
                    return val
            except (ValueError, TypeError):
                pass

        regle = str(get_val(critere, "regle_notation", ""))
        matches = re.findall(r"(\d+(?:\.\d+)?)\s*pts?", regle, re.IGNORECASE)
        if matches:
            try:
                vals = [float(m) for m in matches]
                max_val = max(vals)
                if max_val > 0:
                    return max_val
            except ValueError:
                pass

        return 1.0

    @staticmethod
    def _est_critere_langue(nom_critere: str, categorie: str) -> bool:
        if categorie in ["langue", "langues"]:
            return True
        text = f"{nom_critere} {categorie}".lower()
        return "langue" in text or bool(extraire_langues_requises(text))

    @staticmethod
    def _est_critere_region(nom_critere: str, categorie: str, regle_notation: str) -> bool:
        if categorie == "region":
            return True
        text = f"{nom_critere} {regle_notation}".lower()
        return "région" in text or "region" in text

    # Wrappers de compatibilité (noms historiques)
    _normaliser_texte_langue = staticmethod(normaliser_texte_langue)
    _normaliser_experience_texte = staticmethod(normaliser_experience_texte)
    _normaliser_nom_geo = staticmethod(normaliser_nom_geo)
    _contient_expression = staticmethod(contient_expression)

    _extraire_role_canonique = staticmethod(extraire_role_canonique)
    _extraire_tous_les_roles_candidat = staticmethod(extraire_tous_les_roles_candidat)
    _extraire_role_dominant_candidat = staticmethod(extraire_role_dominant_candidat)
    _evaluer_compatibilite_roles = staticmethod(evaluer_compatibilite_roles)
    _construire_texte_projet = staticmethod(construire_texte_projet)
    _filtrer_experiences_par_domaine = staticmethod(filtrer_experiences_par_domaine)

    _extraire_niveau_numerique = staticmethod(extraire_niveau_numerique)
    _evaluer_correspondance_domaine = staticmethod(evaluer_correspondance_domaine)
    _analyser_regle_diplome = staticmethod(analyser_regle_diplome)
    _evaluer_diplome_algo = staticmethod(evaluer_diplome_algo)

    _analyser_exigence_certification = staticmethod(analyser_exigence_certification)
    _verifier_validite_certification = staticmethod(verifier_validite_certification)
    _verifier_organisme_reconnu = staticmethod(verifier_organisme_reconnu)
    _extraire_seuil_certifications = staticmethod(extraire_seuil_certifications)
    _evaluer_certification_algo = staticmethod(evaluer_certification_algo)

    _extraire_langues_requises = staticmethod(extraire_langues_requises)
    _evaluer_critere_langue = staticmethod(evaluer_critere_langue)

    _nettoyer_regions_ciblees = staticmethod(nettoyer_regions_ciblees)
    _extraire_zones_cibles_ao = staticmethod(extraire_zones_cibles_ao)
    _evaluer_region = staticmethod(evaluer_region)

    _dedupliquer_missions = staticmethod(dedupliquer_missions)
    _analyser_contexte_experience = staticmethod(analyser_contexte_experience)
    _calculer_score_pertinence_mission = staticmethod(calculer_score_pertinence_mission)
    _filtrer_missions_similaires = staticmethod(filtrer_missions_similaires)
    _estimer_annees_sur_projets = staticmethod(estimer_annees_sur_projets)
    _extraire_seuil_minimal = staticmethod(extraire_seuil_minimal)
    _evaluer_regle_echelle_ou_seuil = staticmethod(evaluer_regle_echelle_ou_seuil)
    _evaluer_experience_3_niveaux = staticmethod(evaluer_experience_3_niveaux)

    @classmethod
    def calculate_match(
        cls,
        expert: Any,
        profile: Any,
        contexte_global: str = "",
        geo_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[float, List[Dict[str, Any]], float, bool]:
        score_breakdown = []
        total_poids_obtenu = 0.0
        criteres_avec_donnees = 0

        expert_data = get_val(expert, "extracted_data")
        if not expert_data or not isinstance(expert_data, dict):
            expert_data = expert if isinstance(expert, dict) else {}

        if geo_context is None:
            geo_context = (
                get_val(profile, "geo_context")
                or get_val(profile, "scope_geographique")
                or get_val(profile, "regions_ciblees")
                or get_val(profile, "pays_cibles")
            )

        criteres_attendus = get_val(profile, "criteres_evaluation", []) or []
        titre_poste = get_val(profile, "titre_du_poste") or get_val(profile, "titre", "") or contexte_global

        somme_criteres_max = sum(cls._extract_poids_max(c) for c in criteres_attendus)
        declared_total = float(get_val(profile, "score_total_poste") or 0.0)
        total_poids_maximal = somme_criteres_max if somme_criteres_max > 0 else declared_total

        projets_expert = get_val(expert_data, "projets_et_missions", []) or []
        etudes_expert = expert_data.get("etudes", [])
        certifs_expert = expert_data.get("certifications", [])
        annees_exp_total_cv = float(get_val(expert_data, "annees_experience_total") or 0.0)
        experiences_pro_expert = get_val(expert_data, "experiences_professionnelles", []) or []
        toutes_experiences = (projets_expert or []) + (experiences_pro_expert or [])

        for critere in criteres_attendus:
            nom_critere = get_val(critere, "libelle_exigence") or get_val(critere, "nom", "")
            categorie = str(get_val(critere, "type_critere") or get_val(critere, "categorie", "")).lower()
            poids_max = cls._extract_poids_max(critere)
            regle_notation = str(get_val(critere, "regle_notation", ""))

            score_brut = 0.0
            explication = ""
            has_data = True

            if cls._est_critere_langue(nom_critere, categorie):
                score_brut, explication, has_data = evaluer_critere_langue(expert_data, nom_critere, regle_notation, poids_max)
            elif cls._est_critere_region(nom_critere, categorie, regle_notation):
                score_brut, explication, has_data = evaluer_region(expert_data, nom_critere, regle_notation, poids_max, geo_context)
            elif categorie in ["diplome", "qualification"]:
                score_brut, explication, has_data = evaluer_diplome_algo(etudes_expert, nom_critere, regle_notation, poids_max)
            elif categorie == "certification":
                score_brut, explication, has_data = evaluer_certification_algo(certifs_expert, nom_critere, regle_notation, poids_max)
            elif categorie == "experience":
                score_brut, explication, has_data = evaluer_experience_3_niveaux(
                    nom_critere=nom_critere,
                    categorie=categorie,
                    regle_notation=regle_notation,
                    poids_max=poids_max,
                    projets_expert=projets_expert,
                    experiences_pro_expert=experiences_pro_expert,
                    contexte_global=contexte_global,
                    titre_poste=titre_poste,
                    annees_exp_total_cv=annees_exp_total_cv,
                )
            else:
                has_data = False
                explication = f"Catégorie '{categorie}' évaluée par défaut."

            if has_data:
                criteres_avec_donnees += 1

            score_brut = round(min(max(score_brut, 0.0), poids_max), 2)
            total_poids_obtenu += score_brut
            score_breakdown.append(
                {
                    "critere": nom_critere,
                    "score_obtenu": score_brut,
                    "score_maximal": poids_max,
                    "explication": explication,
                }
            )

        role_poste = extraire_role_canonique(titre_poste or contexte_global)
        roles_candidat = extraire_tous_les_roles_candidat(expert_data)
        role_dominant = extraire_role_dominant_candidat(expert_data)

        facteur_specialisation = 1.0
        eligible = True

        if role_poste:
            if not roles_candidat:
                eligible = False
                compat_role = 0.0
                nb_exp_role = 0
            else:
                compat_role = max(evaluer_compatibilite_roles(role_poste, r) for r in roles_candidat)
                experiences_role = filtrer_experiences_par_domaine(toutes_experiences, role_poste)
                nb_exp_role = len(experiences_role)

                seuil_role = {
                    "dba": 0.50,
                    "sysadmin": 0.50,
                    "qualite": 0.40,
                    "developpeur": 0.50,
                    "analyste": 0.40,
                    "chef_projet": 0.40,
                    "expert_technique": 0.40,
                }.get(role_poste, 0.40)

                if role_poste == "dba":
                    eligible = nb_exp_role >= 3 and (compat_role >= 0.50 or role_dominant == "dba")
                else:
                    eligible = compat_role >= seuil_role and nb_exp_role >= 1

            facteur_specialisation = round(0.6 + 0.4 * compat_role, 2)

            if not eligible or facteur_specialisation < 1.0:
                score_breakdown.append(
                    {
                        "critere": "Éligibilité & Spécialisation du rôle",
                        "score_obtenu": 0.0,
                        "score_maximal": 0.0,
                        "explication": (
                            f"Statut : {'Éligible' if eligible else 'INÉLIGIBLE'}. "
                            f"Poste requis '{role_poste}', Rôle dominant candidat '{role_dominant or 'aucun'}', "
                            f"Nombre d'expériences domaine : {nb_exp_role}, "
                            f"Rôles candidat {roles_candidat} (Compatibilité rôle : {int(compat_role * 100)}%)."
                        ),
                    }
                )

        if total_poids_maximal > 0:
            score_brut_pct = (total_poids_obtenu / total_poids_maximal) * 100
            score_global = round(score_brut_pct * facteur_specialisation, 2)
            score_global = min(score_global, 100.0)
        else:
            score_global = 0.0

        confidence = round(criteres_avec_donnees / len(criteres_attendus), 2) if criteres_attendus else 1.0
        return score_global, score_breakdown, confidence, eligible
