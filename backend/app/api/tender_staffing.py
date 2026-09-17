import re
import time
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional, Callable
from pydantic import BaseModel

from app.database.session import get_db
from app.models.expert import Expert
from app.models.tender import Tender
from app.models.tender_staffing import TenderRequiredProfile, TenderStaffing
from app.services.team_optimizer import TeamOptimizer
from app.services.scoring_engine import ScoringEngine
from app.services.justification_service import JustificationService

router = APIRouter(prefix="/tenders", tags=["Staffing & Optimisation"])


# =========================================================================
# 🛠️ HELPERS RECURRIS & EXTRACTION
# =========================================================================
def _execute_with_retry(llm_func: Callable, *args, **kwargs) -> Any:
    """
    Exécute un appel LLM avec 3 tentatives en cas de Rate Limit / Quota (429, 413, rate_limit).
    Applique une temporisation progressive : 10s (tentative 1), 20s (tentative 2), 30s (tentative 3).
    """
    for attempt in range(1, 4):
        try:
            return llm_func(*args, **kwargs)
        except Exception as e:
            err = str(e).lower()
            if any(keyword in err for keyword in ["rate_limit", "429", "413", "quota"]):
                wait = 10 * attempt
                print(f" ⚠️ [Rate Limit LLM] Tentative {attempt}/3 échouée. Pause de {wait}s...")
                time.sleep(wait)
                if attempt == 3:
                    raise e
            else:
                raise e


def _parse_cached_candidate(c: Any) -> Dict[str, Any]:
    """Normalise un candidat issu du cache JSON en dictionnaire structuré pour l'API."""
    if isinstance(c, (list, tuple)) and len(c) >= 5:
        exp_info = c[0]
        cand_id = exp_info.get("id") if isinstance(exp_info, dict) else getattr(exp_info, "id", None)
        cand_name = exp_info.get("nom_expert") if isinstance(exp_info, dict) else _get_expert_display_name(exp_info)
        score_val = round(float(c[1]), 2) if c[1] is not None else 0.0
        return {
            "expert_id": cand_id,
            "nom_expert": cand_name,
            "score_global": score_val,
            "score_match": score_val,
            "confidence": c[3],
            "score_breakdown": c[2],
            "eligible": c[4],
            "justification_ia": {},
            "selectionne_par_defaut": False,
        }
    elif isinstance(c, dict):
        return c
    return {}


def _get_expert_display_name(expert: Any) -> str:
    """Retourne un nom d'affichage robuste pour un expert, quel que soit le schéma stocké."""
    if not expert:
        return "Expert Inconnu"

    nom_expert = getattr(expert, "nom_expert", None)
    if nom_expert:
        return str(nom_expert)

    nom = getattr(expert, "nom", None)
    prenom = getattr(expert, "prenom", None)
    if nom or prenom:
        parts = [str(p).strip() for p in [nom, prenom] if str(p).strip()]
        return " ".join(parts) if parts else "Expert Inconnu"

    expert_id = getattr(expert, "id", None)
    return f"Expert #{expert_id}" if expert_id is not None else "Expert Inconnu"


def _get_requested_languages(tender: Any) -> List[str]:
    """Retourne les langues demandées depuis l'attribut du modèle ou depuis extracted_data."""
    if hasattr(tender, "langues_exigees") and tender.langues_exigees:
        return list(tender.langues_exigees)

    extracted_data = getattr(tender, "extracted_data", None)
    if isinstance(extracted_data, dict):
        languages = extracted_data.get("langues_exigees")
        if languages:
            return list(languages)

    return []

def _get_profile_by_id(tender: Any, profile_id: Any, db: Session) -> Any:
    """
    Récupère le profil depuis la BDD SQL ou bascule sur extracted_data (JSON) 
    si la table TenderRequiredProfile est vide.
    """
    if not tender:
        return None

    # 1. Recherche BDD
    profile_db = db.query(TenderRequiredProfile).filter(
        TenderRequiredProfile.tender_id == tender.id,
        TenderRequiredProfile.id == profile_id
    ).first()
    if profile_db:
        return profile_db

    # 2. Fallback JSON (extracted_data)
    extracted_blob = getattr(tender, "extracted_data", None)
    if isinstance(extracted_blob, dict):
        inner_data = extracted_blob.get("extracted_data", extracted_blob)
        if isinstance(inner_data, dict):
            json_profiles = inner_data.get("profils", [])
            target_id = _normalize_profile_id(profile_id)
            for p in json_profiles:
                if _normalize_profile_id(p.get("id")) == target_id:
                    return JSONProfileWrapper(p)

    return None

def _get_regions_ciblees(tender: Any) -> List[Any]:
    """Extrait les régions/pays cibles de l'AO."""
    if not tender:
        return []

    root_regions = getattr(tender, "regions_ciblees", None)
    if isinstance(root_regions, list) and root_regions:
        return root_regions
    if isinstance(root_regions, (set, tuple)) and root_regions:
        return list(root_regions)
    if isinstance(root_regions, str) and root_regions.strip():
        return [r.strip() for r in re.split(r"[;,]+", root_regions) if r.strip()]

    extracted_blob = getattr(tender, "extracted_data", None)
    if not isinstance(extracted_blob, dict):
        return []

    regions = (
        extracted_blob.get("regions_ciblees")
        or extracted_blob.get("pays_cibles")
        or extracted_blob.get("pays")
    )

    if not regions and "extracted_data" in extracted_blob:
        inner = extracted_blob.get("extracted_data")
        if isinstance(inner, dict):
            regions = (
                inner.get("regions_ciblees")
                or inner.get("pays_cibles")
                or inner.get("pays")
            )

    if isinstance(regions, list):
        return regions
    elif isinstance(regions, (set, tuple)):
        return list(regions)

    return []


def _normalize_profile_id(profile_id: Any) -> str:
    """Normalise l'identifiant du profil pour éviter les différences de type entre l'API et la base."""
    return str(profile_id)


def _get_cached_top_candidates(tender: Any, profile_id: Any) -> Optional[List[Dict[str, Any]]]:
    """Relit les candidats déjà scorés et sauvegardés au moment de la génération d'équipe."""
    if not tender:
        return None

    saved = tender.saved_staffing
    if not isinstance(saved, dict):
        return None

    cached_by_profile = saved.get("top_candidates_par_profil")
    if not isinstance(cached_by_profile, dict) or not cached_by_profile:
        return None

    target = _normalize_profile_id(profile_id)
    for key, candidates in cached_by_profile.items():
        if _normalize_profile_id(key) == target:
            return candidates
    return None


def _build_alternative_candidates(
    experts: List[Any],
    profile: Any,
    excluded_expert_id: Optional[int] = None,
    regions_ciblees: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    """Construit le Top 5 des experts alternatifs pour un profil, en excluant l'expert actuellement sélectionné."""
    scored_candidates = []
    for expert in experts:
        if excluded_expert_id is not None and getattr(expert, "id", None) == excluded_expert_id:
            continue

        score = getattr(expert, "score", None)
        breakdown = getattr(expert, "score_breakdown", [])
        confidence = getattr(expert, "confidence", getattr(expert, "confidence_score", None))
        eligible = getattr(expert, "eligible", None)

        if score is None:
            if profile is not None:
                score, breakdown, confidence, eligible = ScoringEngine.calculate_match(
                    expert, profile, geo_context=regions_ciblees
                )
            else:
                score, breakdown, confidence, eligible = 0.0, [], 0.0, False

        score_float = round(float(score), 2)

        scored_candidates.append({
            "expert_id": getattr(expert, "id", None),
            "nom_expert": _get_expert_display_name(expert),
            "score_global": score_float,
            "score_match": score_float,
            "confidence": confidence,
            "score_breakdown": breakdown,
            "eligible": eligible if eligible is not None else True,
            "justification_ia": getattr(expert, "justification_ia", {}),
            "selectionne_par_defaut": False,
        })

    # Tri prioritaire sur l'éligibilité puis sur le score global
    scored_candidates.sort(key=lambda c: (c.get("eligible", False), c["score_global"]), reverse=True)
    return scored_candidates[:5]


class ExpertSelectionRequest(BaseModel):
    required_profile_id: Any
    expert_id: int
    old_expert_id: Optional[int] = None  


class JSONProfileWrapper:
    """ Wrapper pour transformer le JSON de l'IA en objet compatible dot-notation """
    def __init__(self, data: dict):
        self.id = data.get("id")
        self.poste = data.get("titre_du_poste")
        self.criteres_evaluation = data.get("criteres_evaluation", [])
        self.titre_du_poste = data.get("titre_du_poste")

        self.quantite = self._coerce_quantity(
            data.get("quantite_demandee")
            or data.get("quantite")
            or data.get("quantity")
            or data.get("nombre_experts_demandes")
            or 1
        )
        self.quantite_demandee = self.quantite

    @staticmethod
    def _coerce_quantity(value: Any) -> int:
        if isinstance(value, bool):
            return 1
        if isinstance(value, (int, float)):
            return max(1, int(value))
        if isinstance(value, str):
            match = re.search(r"\d+", value)
            if match:
                return max(1, int(match.group(0)))
        return 1


# =========================================================================
# 💾 ENDPOINT 1 : LECTURE INSTANTANÉE - Cache BDD 
# =========================================================================
@router.get("/{tender_id}/staffing", status_code=status.HTTP_200_OK)
def get_saved_tender_staffing(tender_id: int, db: Session = Depends(get_db)):
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    saved_meta = (tender.saved_staffing or {}) if (tender and isinstance(tender.saved_staffing, dict)) else {}
    conflits_sauvegardes = saved_meta.get("conflits_arbitres", [])
    saved_status = saved_meta.get("status")

    staffing_entries = db.query(TenderStaffing).filter(
        TenderStaffing.tender_id == tender_id
    ).order_by(TenderStaffing.id.asc()).all()

    if not staffing_entries:
        return {
            "has_saved_team": False,
            "status": "PAUSED" if saved_status == "PAUSED" else "empty",
            "score_global_equipe": 0.0,
            "conflits_arbitres": conflits_sauvegardes,
            "proposition_equipe": []
        }

    all_experts = db.query(Expert).all()
    experts_dict = {e.id: e for e in all_experts}
    regions_ciblees = _get_regions_ciblees(tender)

    proposition_equipe_payload = []

    for entry in staffing_entries:
        exp_obj = experts_dict.get(entry.expert_id)
        nom_expert = _get_expert_display_name(exp_obj)

        cached_candidates = _get_cached_top_candidates(tender, entry.required_profile_id)
        if cached_candidates is not None:
            formatted_candidates = [_parse_cached_candidate(c) for c in cached_candidates]
            alternatives = [
                c for c in formatted_candidates if c.get("expert_id") != entry.expert_id
            ][:5]
        else:
            alternatives = _build_alternative_candidates(
                all_experts,
                profile=None,
                excluded_expert_id=entry.expert_id,
                regions_ciblees=regions_ciblees,
            )

        score_indiv_float = round(float(entry.score_global), 2) if entry.score_global is not None else 0.0
        is_eligible = getattr(entry, "eligible", True)
        has_expert = entry.expert_id is not None and exp_obj is not None

        proposition_equipe_payload.append({
            "poste": entry.poste_concerne,
            "required_profile_id": entry.required_profile_id,
            "poste_non_pourvu": not has_expert,
            "statut_poste": "Pourvu" if has_expert else "⚠️ Poste non pourvu",
            "expert_selectionne": {
                "expert_id": entry.expert_id,
                "nom_expert": nom_expert if has_expert else "⚠️ Non attribué",
                "score_global": score_indiv_float if has_expert else 0.0,
                "confidence": getattr(entry, "confidence", getattr(entry, "confidence_score", None)),
                "eligible": is_eligible,
                "score_breakdown": entry.score_breakdown,
                "justification_ia": entry.justification_ia,
                "selectionne_par_defaut": entry.selectionne_par_defaut,
                "selectionne_par_user": entry.selectionne_par_user
            },
            "alternatives": alternatives
        })

    valid_scores = [p["expert_selectionne"]["score_global"] for p in proposition_equipe_payload if not p["poste_non_pourvu"]]
    score_global_equipe = round(
        float(sum(valid_scores) / len(valid_scores)),
        2
    ) if valid_scores else 0.0

    final_status = "PAUSED" if saved_status == "PAUSED" else "success"

    return {
        "has_saved_team": True,
        "status": final_status,
        "score_global_equipe": round(float(score_global_equipe), 2),
        "conflits_arbitres": conflits_sauvegardes,
        "proposition_equipe": proposition_equipe_payload
    }


# =========================================================================
# ⚙️ ENDPOINT 2 : GÉNÉRATION / REGÉNÉRATION
# =========================================================================
@router.post("/{tender_id}/staffing/generate", status_code=status.HTTP_201_CREATED)
def generate_tender_staffing(
    tender_id: int, 
    force_recalculate: bool = Query(False),
    db: Session = Depends(get_db)
):
    def _set_paused_status_in_db(tender_obj):
        try:
            current_saved = tender_obj.saved_staffing or {}
            current_saved["status"] = "PAUSED"
            tender_obj.saved_staffing = current_saved
            db.commit()
        except Exception:
            db.rollback()

    if not force_recalculate:
        existing_staffing = get_saved_tender_staffing(tender_id, db)
        if existing_staffing.get("has_saved_team") or existing_staffing.get("status") == "PAUSED":
            return existing_staffing

    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Appel d'offres introuvable.")

    extracted_blob = tender.extracted_data
    if not extracted_blob:
        raise HTTPException(
            status_code=400, 
            detail="L'appel d'offres ne contient aucune donnée extraite."
        )
        
    if "extracted_data" in extracted_blob and isinstance(extracted_blob["extracted_data"], dict):
        inner_data = extracted_blob["extracted_data"]
    else:
        inner_data = extracted_blob

    json_profiles = inner_data.get("profils", [])
    if not json_profiles:
        raise HTTPException(
            status_code=400, 
            detail="⚠️ Aucun profil requis trouvé. Vérifiez la structure du JSON de cet AO."
        )

    profiles = [JSONProfileWrapper(p) for p in json_profiles]
    all_experts = db.query(Expert).all()

    for expert in all_experts:
        if hasattr(expert, "nom_expert") and expert.nom_expert:
            parts = expert.nom_expert.split(" ", 1)
            expert.nom = parts[0]
            expert.prenom = parts[1] if len(parts) > 1 else ""
        else:
            expert.nom = "Expert"
            expert.prenom = f"#{expert.id}"

    langues_demandees = _get_requested_languages(tender)
    regions_ciblees = _get_regions_ciblees(tender)

    try:
        contexte_global = tender.extracted_data.get("contexte_mission_globale", "")
        optimization_result = _execute_with_retry(
            TeamOptimizer.optimize_and_staff,
            profiles,
            all_experts,
            langues_demandees,
            regions_ciblees,
            contexte_global=contexte_global
        )
    except Exception as e:
        err_str = str(e).lower()
        if any(kw in err_str for kw in ["429", "413", "rate_limit", "quota"]):
            _set_paused_status_in_db(tender)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Quota IA temporairement atteint lors de l'optimisation après 3 tentatives (10s, 20s, 30s)."
            )
        raise HTTPException(status_code=500, detail=f"Erreur d'optimisation : {str(e)}")
    
    selected_team = optimization_result.get("selected_team", [])
    top_candidates_cache = optimization_result.get("top_candidates_par_profil", {})

    experts_dict = {e.id: e for e in all_experts}
    profiles_dict = {p.id: p for p in profiles}

    justifications_optimales = {}
    proposition_equipe_payload = []

    for index, member in enumerate(selected_team):
        p_id = member["required_profile_id"]
        exp_id = member["expert_id"]
        expert_obj = experts_dict.get(exp_id) if exp_id else None
        profile_obj = profiles_dict.get(p_id)

        # On ne passe que si le profil requis lui-même n'existe pas
        if not profile_obj:
            continue

        score_indiv_float = round(float(member["score_global"]), 2) if member.get("score_global") is not None else 0.0
        is_eligible = member.get("eligible", True)
        has_expert = exp_id is not None and expert_obj is not None

        if expert_obj:
            if index > 0:
                time.sleep(2)

            try:
                justification_ia = _execute_with_retry(
                    JustificationService.generate_justification,
                    expert=expert_obj,
                    profile=profile_obj,
                    score_global=score_indiv_float,
                    score_breakdown=member["score_breakdown"],
                    best_individual_role=member.get("best_individual_role")
                    
                )
            except Exception:
                justification_ia = {
                    "resume": "Justification temporairement simplifiée (Quota d'API IA atteint après 3 tentatives).",
                    "points_forts": [f"Score d'adéquation global de {score_indiv_float}%"],
                    "points_faibles": [],
                    "criteres_non_satisfaits": []
                }
        else:
            justification_ia = {
                "resume": "Aucun candidat trouvé dans la base pour ce profil.",
                "points_forts": [],
                "points_faibles": [],
                "criteres_non_satisfaits": []
            }
        
        if exp_id:
            justifications_optimales[exp_id] = justification_ia

        candidates_profil = top_candidates_cache.get(p_id, [])
        formatted_candidates = [_parse_cached_candidate(c) for c in candidates_profil]
        top_alternatives = [
            c for c in formatted_candidates if c.get("expert_id") != exp_id
        ][:5]

        proposition_equipe_payload.append({
            "poste": member["poste"],
            "required_profile_id": p_id,
            "poste_non_pourvu": not has_expert,
            "statut_poste": "Pourvu" if has_expert else "⚠️ Poste non pourvu",
            "expert_selectionne": {
                "expert_id": exp_id,
                "nom_expert": member["nom_expert"] if has_expert else "⚠️ Non attribué",
                "score_global": score_indiv_float if has_expert else 0.0,
                "confidence": member["confidence"],
                "eligible": is_eligible,
                "score_breakdown": member["score_breakdown"],
                "justification_ia": justification_ia,
                "selectionne_par_defaut": True,
                "selectionne_par_user": True
            },
            "alternatives": top_alternatives
        })

    try:
        db.query(TenderStaffing).filter(TenderStaffing.tender_id == tender_id).delete(synchronize_session=False)
        tender = db.query(Tender).filter(Tender.id == tender_id).first()
        if tender:
            tender.saved_staffing = {
                "status": "COMPLETED",
                "conflits_arbitres": optimization_result.get("conflits", []),
                "top_candidates_par_profil": optimization_result.get("top_candidates_par_profil", {})
            }
        for item in proposition_equipe_payload:
            selected_node = item["expert_selectionne"]
            if selected_node["expert_id"] is None:
                continue
            
            staffing_entry = TenderStaffing(
                tender_id=tender_id,
                required_profile_id=item["required_profile_id"],
                expert_id=selected_node["expert_id"],
                poste_concerne=item["poste"], 
                score_global=selected_node["score_global"],
                score_breakdown=selected_node["score_breakdown"],
                confidence=selected_node.get("confidence"),
                justification_ia=selected_node["justification_ia"],
                selectionne_par_defaut=True,
                selectionne_par_user=True,
                generated_by="auto"
            )
            if hasattr(staffing_entry, "eligible"):
                staffing_entry.eligible = selected_node.get("eligible", True)

            db.add(staffing_entry)

        db.commit()

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"⚠️ Échec persistance simulation : {str(e)}")

    valid_scores = [p["expert_selectionne"]["score_global"] for p in proposition_equipe_payload if not p["poste_non_pourvu"]]
    score_global_equipe = round(
        float(sum(valid_scores) / len(valid_scores)),
        2
    ) if valid_scores else 0.0

    return {
        "status": "COMPLETED",
        "has_saved_team": True,
        "score_global_equipe": score_global_equipe,
        "conflits_arbitres": optimization_result.get("conflits", []),
        "proposition_equipe": proposition_equipe_payload
    }


# =========================================================================
# ✋ ENDPOINT 3 : SÉLECTION MANUELLE
# =========================================================================
@router.put("/{tender_id}/staffing/select", status_code=status.HTTP_200_OK)
def manual_expert_selection(tender_id: int, payload: ExpertSelectionRequest, db: Session = Depends(get_db)):
    expert_exists = db.query(Expert).filter(Expert.id == payload.expert_id).first()
    if not expert_exists:
        raise HTTPException(status_code=404, detail="L'expert cible n'existe pas.")

    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    
    profile_exists = _get_profile_by_id(tender, payload.required_profile_id, db)

    normalized_profile_id = _normalize_profile_id(payload.required_profile_id)
    existing_entries = db.query(TenderStaffing).filter(
        TenderStaffing.tender_id == tender_id
    ).all()
    
    profile_entries = [
        entry for entry in existing_entries 
        if _normalize_profile_id(entry.required_profile_id) == normalized_profile_id
    ]

    if not profile_entries:
        raise HTTPException(status_code=404, detail="Aucun poste trouvé pour ce profil.")

    target_entry = None
    if payload.old_expert_id:
        target_entry = next((e for e in profile_entries if e.expert_id == payload.old_expert_id), None)

    if not target_entry:
        target_entry = next((e for e in profile_entries if getattr(e, "selectionne_par_user", False)), None)
    if not target_entry:
        target_entry = next((e for e in profile_entries if getattr(e, "selectionne_par_defaut", False)), None)
    if not target_entry:
        target_entry = profile_entries[0]

    regions_ciblees = _get_regions_ciblees(tender)
    
    # profile_exists étant maintenant trouvé, ScoringEngine s'exécute correctement
    raw_score, score_breakdown, confidence, eligible = (
        ScoringEngine.calculate_match(expert_exists, profile_exists, geo_context=regions_ciblees)
        if profile_exists else (0.0, {}, 0.0, False)
    )
    
    score_global = round(float(raw_score), 2)
    
    if profile_exists:
        try:
            justification_ia = _execute_with_retry(
                JustificationService.generate_justification,
                expert=expert_exists,
                profile=profile_exists,
                score_global=score_global,
                score_breakdown=score_breakdown
            )
        except Exception:
            justification_ia = {
                "resume": "Justification indisponible (Erreur ou quota IA après 3 tentatives).", 
                "points_forts": [], 
                "points_faibles": [], 
                "criteres_non_satisfaits": []
            }
    else:
        justification_ia = {"resume": "Choix manuel de l'utilisateur."}

    try:
        target_entry.expert_id = payload.expert_id
        target_entry.score_global = score_global
        target_entry.score_breakdown = score_breakdown
        target_entry.confidence = confidence
        target_entry.justification_ia = justification_ia
        target_entry.selectionne_par_user = True
        target_entry.selectionne_par_defaut = False
        target_entry.generated_by = "hybrid"

        if hasattr(target_entry, "eligible"):
            target_entry.eligible = eligible

        db.commit()

        return {
            "status": "updated",
            "message": "Sélection manuelle enregistrée et mise à jour sur le poste.",
            "expert_id": payload.expert_id,
            "required_profile_id": payload.required_profile_id,
            "score_global": target_entry.score_global,
            "eligible": eligible,
            "justification_ia": target_entry.justification_ia
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur de modification d'équipe : {str(e)}")


# =========================================================================
# 🔍 ENDPOINT 4 : RECHERCHE DES CANDIDATS ALTERNATIFS
# =========================================================================
@router.get("/{tender_id}/staffing/candidates/{profile_id}", status_code=status.HTTP_200_OK)
def get_candidates_for_profile(tender_id: int, profile_id: str, db: Session = Depends(get_db)):
    normalized_profile_id = _normalize_profile_id(profile_id)
    entries = db.query(TenderStaffing).filter(
        TenderStaffing.tender_id == tender_id
    ).all()

    profile_entries = [e for e in entries if _normalize_profile_id(e.required_profile_id) == normalized_profile_id]

    selected_entry = next((entry for entry in profile_entries if getattr(entry, "selectionne_par_user", False)), None)
    if not selected_entry:
        selected_entry = next((entry for entry in profile_entries if getattr(entry, "selectionne_par_defaut", False)), None)

    excluded_expert_id = selected_entry.expert_id if selected_entry else None

    all_experts = db.query(Expert).all()
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    
    profile = _get_profile_by_id(tender, profile_id, db)

    regions_ciblees = _get_regions_ciblees(tender)
    
    return _build_alternative_candidates(
        all_experts, 
        profile, 
        excluded_expert_id=excluded_expert_id, 
        regions_ciblees=regions_ciblees
    )