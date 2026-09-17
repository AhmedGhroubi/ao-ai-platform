import numpy as np
from typing import List, Dict, Any, Optional
from scipy.optimize import linear_sum_assignment
from app.services.scoring_engine import ScoringEngine


class TeamOptimizer:

    @classmethod
    def optimize_and_staff(
        cls,
        profiles: List[Any],
        experts: List[Any],
        langues_exigees: Optional[List[str]] = None,
        regions_ciblees: Optional[Any] = None,
        contexte_global: str = ""
    ) -> Dict[str, Any]:

        if not profiles:
            return {
                "selected_team": [],
                "score_global_equipe": 0.0,
                "conflits": [{"type": "AUCUN_PROFIL", "message": "Aucun profil requis n'a été fourni."}],
                "top_candidates_par_profil": {}
            }

        if not experts:
            return {
                "selected_team": [],
                "score_global_equipe": 0.0,
                "conflits": [{"type": "AUCUN_EXPERT", "message": "Aucun candidat disponible dans la base."}],
                "top_candidates_par_profil": {}
            }

        # Expansion des profils selon leur quantité
        slots = []
        for p in profiles:
            qty = getattr(p, "quantite", getattr(p, "quantite_demandee", 1))
            qty = max(1, int(qty)) if str(qty).isdigit() or isinstance(qty, (int, float)) else 1
            for instance_idx in range(qty):
                slots.append({
                    "profile_obj": p,
                    "profile_id": getattr(p, "id", None),
                    "poste": getattr(p, "titre_du_poste", getattr(p, "poste", "Profil non spécifié")),
                    "slot_index": instance_idx
                })

        num_slots = len(slots)
        num_experts = len(experts)

        # Calcul de la matrice des scores et filtrage d'éligibilité
        scores_matrix = np.zeros((num_slots, num_experts))
        breakdowns_matrix = [[None for _ in range(num_experts)] for _ in range(num_slots)]
        confidences_matrix = np.zeros((num_slots, num_experts))
        eligibility_matrix = np.zeros((num_slots, num_experts), dtype=bool)

        candidates_cache: Dict[Any, List[Dict[str, Any]]] = {}

        for s_idx, slot in enumerate(slots):
            p_obj = slot["profile_obj"]
            p_id = slot["profile_id"]

            if p_id not in candidates_cache:
                candidates_cache[p_id] = []

            for e_idx, expert in enumerate(experts):
                score, breakdown, confidence, eligible = ScoringEngine.calculate_match(
                    expert=expert,
                    profile=p_obj,
                    contexte_global=contexte_global,
                    geo_context=regions_ciblees
                )

                scores_matrix[s_idx, e_idx] = score
                breakdowns_matrix[s_idx][e_idx] = breakdown
                confidences_matrix[s_idx, e_idx] = confidence
                eligibility_matrix[s_idx, e_idx] = eligible

                candidates_cache[p_id].append({
                    "expert_id": getattr(expert, "id", None),
                    "nom_expert": getattr(expert, "nom_expert", f"Expert #{getattr(expert, 'id', '')}"),
                    "score_global": round(float(score), 2),
                    "confidence": confidence,
                    "score_breakdown": breakdown,
                    "eligible": eligible
                })

        # Tri et conservation du Top 5 éligibles par profil
        top_candidates_par_profil = {}
        for p_id, cand_list in candidates_cache.items():
            sorted_cands = sorted(cand_list, key=lambda c: (c["eligible"], c["score_global"]), reverse=True)
            top_candidates_par_profil[str(p_id)] = sorted_cands[:5]

        # Détermination du meilleur poste individuel pour chaque expert
        best_roles_per_expert = {}
        for e_idx in range(num_experts):
            best_s_idx = int(np.argmax(scores_matrix[:, e_idx]))
            best_roles_per_expert[e_idx] = slots[best_s_idx]["poste"]

        # Matrice des coûts pour l'algorithme Hongrois
        cost_matrix = np.zeros((num_slots, num_experts))

        for s_idx in range(num_slots):
            for e_idx in range(num_experts):
                score = scores_matrix[s_idx, e_idx]
                eligible = eligibility_matrix[s_idx, e_idx]
                if eligible:
                    cost_matrix[s_idx, e_idx] = 100.0 - score
                else:
                    cost_matrix[s_idx, e_idx] = 1000.0 + (100.0 - score)

        row_ind, col_ind = linear_sum_assignment(cost_matrix)

        selected_team = []
        conflits = []
        total_score_sum = 0.0
        poids_effectifs = 0

        for r, c in zip(row_ind, col_ind):
            slot_info = slots[r]
            assigned_expert = experts[c]
            assigned_score = float(scores_matrix[r, c])
            is_eligible = bool(eligibility_matrix[r, c])
            
            assigned_role_name = slot_info["poste"]
            best_role_name = best_roles_per_expert[c]
            exp_name = getattr(assigned_expert, "nom_expert", f"Expert #{getattr(assigned_expert, 'id', '')}")

            # 1. Fallback si candidat non éligible
            if not is_eligible:
                conflits.append({
                    "type": "AFFECTATION_FALLBACK",
                    "poste": assigned_role_name,
                    "poste_concerne": assigned_role_name,
                    "required_profile_id": slot_info["profile_id"],
                    "expert_id": getattr(assigned_expert, "id", None),
                    "nom_expert": exp_name,
                    "score": round(assigned_score, 2),
                    "message": (
                        f"Aucun candidat strictly éligible n'a été trouvé pour le poste '{assigned_role_name}'. "
                        f"Le meilleur candidat disponible a été affecté en fallback."
                    )
                })

            # 2. Arbitrage d'équipe : GÉNÉRÉ UNIQUEMENT SI LE POSTE ATTRIBUÉ EST DIFFÉRENT DU MEILLEUR POSTE
            if assigned_role_name != best_role_name:
                conflits.append({
                    "type": "ARBITRAGE_EQUIPE",
                    "poste": assigned_role_name,
                    "poste_concerne": assigned_role_name,
                    "required_profile_id": slot_info["profile_id"],
                    "expert_id": getattr(assigned_expert, "id", None),
                    "nom_expert": exp_name,
                    "best_individual_role": best_role_name,
                    "score": round(assigned_score, 2),
                    "message": (
                        f"{exp_name} aurait eu un meilleur score sur le poste '{best_role_name}', "
                        f"mais a été réaffecté sur '{assigned_role_name}' pour maximiser l'efficience globale."
                    )
                })

            selected_team.append({
                "poste": assigned_role_name,
                "required_profile_id": slot_info["profile_id"],
                "expert_id": getattr(assigned_expert, "id", None),
                "nom_expert": exp_name,
                "score_global": round(assigned_score, 2),
                "confidence": float(confidences_matrix[r, c]),
                "score_breakdown": breakdowns_matrix[r][c],
                "eligible": is_eligible,
                "poste_non_pourvu": False,
                "best_individual_role": best_role_name  # Transmis au service de justification
            })

            total_score_sum += assigned_score
            poids_effectifs += 1

        score_global_equipe = round(total_score_sum / poids_effectifs, 2) if poids_effectifs > 0 else 0.0

        return {
            "selected_team": selected_team,
            "score_global_equipe": score_global_equipe,
            "conflits": conflits,
            "top_candidates_par_profil": top_candidates_par_profil
        }