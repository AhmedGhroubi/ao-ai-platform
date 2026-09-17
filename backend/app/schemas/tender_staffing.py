from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

# ========================================================================================
# 1. SOUS-SCHÉMAS STRUCTURES (Pour la validation fine des objets JSON)
# ========================================================================================

class CritereEvaluation(BaseModel):
    nom: str
    categorie: str  # 'diplome', 'experience', 'competences', 'region', 'langues'
    poids_max: float
    requis: bool

class CritereScoreMatch(BaseModel):
    critere: str
    score_obtenu: float
    score_maximal: float
    explication: str

class JustificationIAStructuree(BaseModel):
    resume: str
    points_forts: List[str] = []
    points_faibles: List[str] = []
    criteres_non_satisfaits: List[str] = []


# ========================================================================================
# 2. SCHÉMAS POUR LES PROFILS REQUIS (TenderRequiredProfile)
# ========================================================================================

class RequiredProfileBase(BaseModel):
    poste: str
    quantite: int = 1
    criteres_evaluation: List[CritereEvaluation] = []

class RequiredProfileCreate(RequiredProfileBase):
    pass

class RequiredProfileResponse(RequiredProfileBase):
    id: int
    tender_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ========================================================================================
# 3. SCHÉMAS POUR LES PROPOSITIONS D'EXPERTS (TenderStaffing)
# ========================================================================================

class TenderStaffingBase(BaseModel):
    tender_id: int
    required_profile_id: str
    expert_id: int
    score_global: int = Field(..., ge=0, le=100)
    ranking: int
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    score_breakdown: List[CritereScoreMatch] = []
    justification_ia: JustificationIAStructuree
    generated_by: str = "algorithm" # 'algorithm', 'manual', 'hybrid'
    selectionne_par_defaut: bool = False
    selectionne_par_user: bool = False
    selected_by_user_id: Optional[int] = None

class TenderStaffingCreate(TenderStaffingBase):
    pass

# Schéma pour mettre à jour une sélection depuis Angular
class StaffingSelectionUpdate(BaseModel):
    expert_id: int
    required_profile_id: int
    selectionne: bool
    user_id: Optional[int] = None  # Trace qui fait l'action

class TenderStaffingResponse(TenderStaffingBase):
    id: int
    updated_at: datetime
    # Pour simplifier la vie d'Angular, on peut injecter le nom de l'expert en sortie d'API
    nom_expert: Optional[str] = None

    class Config:
        from_attributes = True