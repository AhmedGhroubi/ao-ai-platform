import os
import json
import hashlib
from typing import Dict, Any, List, Optional
from groq import Groq
from app.models.expert import Expert
from app.models.tender_staffing import TenderRequiredProfile


# ──────────────────────────────────────────────────────────────────────────────
# CACHE PERSISTANT DES JUSTIFICATIONS
# ──────────────────────────────────────────────────────────────────────────────
JUSTIF_CACHE_FILE = os.getenv("JUSTIF_CACHE_FILE", "justification_cache.json")


def _load_cache() -> dict:
    if os.path.exists(JUSTIF_CACHE_FILE):
        try:
            with open(JUSTIF_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            print("  [JustificationService] Cache corrompu ou illisible, redémarrage à vide.")
    return {}


_justif_cache: dict[str, dict] = _load_cache()


def _save_cache():
    tmp_file = f"{JUSTIF_CACHE_FILE}.tmp"
    try:
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(_justif_cache, f, ensure_ascii=False, indent=2)
        os.replace(tmp_file, JUSTIF_CACHE_FILE)
    except OSError as e:
        print(f"  [JustificationService] Échec de sauvegarde du cache : {e}")


def _cache_key(
    expert_id: Any,
    profile_id: Any,
    score_global: int,
    score_breakdown: List[Dict[str, Any]],
    best_individual_role: Optional[str] = None,
) -> str:
    breakdown_sig = json.dumps(score_breakdown, sort_keys=True, ensure_ascii=False)
    raw = f"{expert_id}|{profile_id}|{score_global}|{breakdown_sig}|{best_individual_role or ''}"
    return hashlib.md5(raw.encode()).hexdigest()


class JustificationService:
    _client = None

    @classmethod
    def _build_deterministic_justification(
        cls,
        expert: Any,
        profile: Any,
        score_global: int,
        score_breakdown: List[Dict[str, Any]],
        best_individual_role: Optional[str] = None,
    ) -> Dict[str, Any]:
        points_forts: List[str] = []
        points_faibles: List[str] = []
        criteres_non_satisfaits: List[str] = []

        for crit in score_breakdown:
            critere = str(crit.get("critere", "")).lower()
            score_obtenu = float(crit.get("score_obtenu", 0) or 0.0)
            score_maximal = float(crit.get("score_maximal", 0) or 0.0)
            explication = str(crit.get("explication", "")).lower()

            if score_obtenu >= score_maximal and score_maximal > 0:
                continue

            is_language = "langue" in critere or "langues" in critere or "langages" in critere
            is_region = "région" in critere or "region" in critere or "sous-région" in critere or "sous region" in critere

            if is_language or is_region:
                if "satisfait" in explication or "valid" in explication:
                    continue
                label = "langue" if is_language else "région"
                points_faibles.append(f"Le profil présente encore un point d’attention sur la maîtrise de la {label} demandée.")
                criteres_non_satisfaits.append(f"Exigence de {label} non complètement satisfaite.")
                continue

            if "gestion de projet" in critere or "gestion de projet" in explication:
                points_faibles.append("L’expérience en gestion de projet reste partiellement démontrée.")
                criteres_non_satisfaits.append("Expérience en gestion de projet partiellement satisfaisante.")
            elif score_obtenu < score_maximal:
                points_faibles.append(f"Le critère '{crit.get('critere', '')}' n'est que partiellement satisfait.")
                criteres_non_satisfaits.append(str(crit.get("critere", "")))

        if best_individual_role and best_individual_role != profile.poste:
            points_faibles.append(
                f"Affectation issue d'un arbitrage d'équipe (poste individuel optimal : {best_individual_role})."
            )

        if not points_faibles:
            points_faibles.append("Le profil reste globalement cohérent avec le poste.")

        if not criteres_non_satisfaits:
            criteres_non_satisfaits.append("Aucun critère majeur n'a été identifié comme non satisfait.")

        return {
            "resume": f"Le candidat présente un profil globalement adapté au poste de {profile.poste} avec un score global de {score_global}/100.",
            "points_forts": [
                "Profil cohérent avec les attentes du poste.",
                "Score global élevé et structure de justification stable.",
            ],
            "points_faibles": points_faibles,
            "criteres_non_satisfaits": criteres_non_satisfaits,
        }

    @classmethod
    def get_client(cls):
        if cls._client is None:
            cls._client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        return cls._client

    @classmethod
    def generate_justification(
        cls,
        expert: Expert,
        profile: TenderRequiredProfile,
        score_global: int,
        score_breakdown: List[Dict[str, Any]],
        force_regenerate: bool = False,
        best_individual_role: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Appelle Groq pour transformer les notes déterministes et le CV de l'expert
        en une justification textuelle structurée au format JSON.

        Paramètre optionnel rétrocompatible :
        - best_individual_role (str) : Intitulé du poste où l'expert obtient son meilleur
          score individuel. Si renseigné et identique au poste attribué, toute mention
          d'arbitrage d'équipe ou de réaffectation est formellement interdite au LLM.
        """
        expert_id = getattr(expert, "id", None) or f"{expert.nom}_{expert.prenom}"
        profile_id = getattr(profile, "id", None) or profile.poste

        cache_key = _cache_key(
            expert_id=expert_id,
            profile_id=profile_id,
            score_global=score_global,
            score_breakdown=score_breakdown,
            best_individual_role=best_individual_role,
        )
        if not force_regenerate and cache_key in _justif_cache:
            print(f"  [JustificationService] Cache hit pour {expert_id} / {profile_id}")
            return _justif_cache[cache_key]

        client = cls.get_client()

        # 1. Extraction et limitation du texte du CV pour respecter la fenêtre de contexte
        expert_name = f"{expert.nom} {expert.prenom}"
        data = expert.extracted_data or {}
        cv_summary = json.dumps({
            "titre":   data.get("titre_poste_principal", ""),
            "exp":     data.get("annees_experience_total", 0),
            "skills":  data.get("competences_techniques", [])[:10],
            "pays":    data.get("pays_d_intervention", []),
            "projets": [
                {k: p.get(k, "") for k in ("nom_projet", "poste_occupe", "client_ou_bailleur")}
                for p in data.get("projets_et_missions", [])[:3]
            ],
        }, ensure_ascii=False)[:1800]

        # 2. Préparation du contexte des scores calculés par Python
        scores_formatted = ""
        for crit in score_breakdown:
            scores_formatted += f"- {crit['critere']} : {crit['score_obtenu']}/{crit['score_maximal']} ({crit['explication']})\n"

        # 3. Contrôle strict du contexte d'arbitrage vs poste de prédilection
        is_best_match = (best_individual_role is None) or (best_individual_role == profile.poste)

        if is_best_match:
            arbitration_instructions = (
                "CONSIGNE D'AFFECTATION :\n"
                "- Ce poste EST LE POSTE DE PRÉDILECTION (meilleur score individuel) de l'expert.\n"
                "- Il est STRICTEMENT INTERDIT d'inventer ou d'évoquer une réaffectation, un arbitrage d'équipe, "
                "un déplacement vers un second choix ou une concession d'optimisation.\n"
                "- Justifie l'affectation uniquement par l'adéquation directe du candidat à ce poste précis."
            )
        else:
            arbitration_instructions = (
                f"CONSIGNE D'AFFECTATION :\n"
                f"- Ce poste ('{profile.poste}') résulte d'un arbitrage d'optimisation globale de l'équipe.\n"
                f"- Le poste individuel idéal de l'expert était '{best_individual_role}'.\n"
                f"- Explique brièvement que ce placement optimise la performance globale de l'équipe tout en valorisant ses compétences."
            )

        # 4. Prompts structurés
        system_prompt = (
            "Tu es un Directeur des Ressources Humaines senior spécialisé dans les appels d'offres internationaux.\n"
            "Ton rôle est d'expliquer de manière objective pourquoi un expert a obtenu un certain score pour un poste donné.\n"
            "Tu dois impérativement respecter les scores fournis par le moteur de calcul algorithmique. Ne modifie pas les notes.\n"
            "Ne suppose JAMAIS qu'un arbitrage ou une réaffectation a eu lieu à moins que les consignes d'affectation ne l'indiquent expressément.\n"
            "Tu dois répondre exclusivement au format JSON contenant les clés suivantes :\n"
            "- 'resume' (string) : Un résumé de 2-3 phrases sur la pertinence globale.\n"
            "- 'points_forts' (array of strings) : Les 2 à 4 principaux atouts de l'expert pour ce poste.\n"
            "- 'points_faibles' (array of strings) : Les limites du profil ou points d'attention.\n"
            "- 'criteres_non_satisfaits' (array of strings) : Les exigences de l'AO auxquelles l'expert n'a pas répondu (basé sur le score_breakdown).\n"
        )

        user_prompt = f"""
        **Poste recherché dans l'Appel d'Offres :** {profile.poste}

        **Candidat évalué :** {expert_name}
        **Score global obtenu :** {score_global}/100

        **Cadre d'affectation :**
        {arbitration_instructions}

        **Détail des scores calculés par l'algorithme :**
        {scores_formatted}

        **Extrait du CV de l'expert :**
        {cv_summary}

        Rédige ton analyse pour ce candidat. Sois direct, professionnel, constructif et rigoureux.
        """

        try:
            # 5. Appel à l'API de Groq — max_tokens plafonné
            response = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=1200,
            )

            raw_content = response.choices[0].message.content
            parsed_justification = json.loads(raw_content)

            required_keys = ["resume", "points_forts", "points_faibles", "criteres_non_satisfaits"]
            for key in required_keys:
                if key not in parsed_justification:
                    parsed_justification[key] = [] if key != "resume" else "Évaluation générée."

            # 6. Mise en cache pour éviter de repayer un appel identique plus tard
            _justif_cache[cache_key] = parsed_justification
            _save_cache()

            return parsed_justification

        except Exception as e:
            print(f"Erreur d'appel API Groq : {str(e)}")
            return cls._build_deterministic_justification(
                expert=expert,
                profile=profile,
                score_global=score_global,
                score_breakdown=score_breakdown,
                best_individual_role=best_individual_role,
            )