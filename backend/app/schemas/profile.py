from pydantic import BaseModel, field_validator
from typing import List, Optional

class CriteresEvaluation(BaseModel):
    type_critere: Optional[str] = None
    libelle_exigence: str
    points_maximum: float
    regle_notation: Optional[str] = None
    seuil_bas: Optional[str] = None
    seuil_haut: Optional[str] = None
    points_seuil_bas: Optional[float] = None
    points_seuil_haut: Optional[float] = None

    # 💡 Nettoyeur pour les floats optionnels (Convertit "" en None)
    @field_validator('points_seuil_bas', 'points_seuil_haut', mode='before')
    @classmethod
    def empty_string_to_none(cls, v):
        if v == "":
            return None
        return v

    # 💡 Nettoyeur pour les points max (Convertit "" en 0.0 si vide)
    @field_validator('points_maximum', mode='before')
    @classmethod
    def empty_string_to_zero(cls, v):
        if v == "":
            return 0.0
        return v

class ValidationIA(BaseModel):
    necessite_verification_humaine: bool
    motif_doute: Optional[str] = ""

class VerificationMath(BaseModel):
    somme_calculee: float
    somme_attendue: float
    ecart: float
    ok: bool

class ProfilDemande(BaseModel):
    id: Optional[str] = None
    titre_du_poste: str
    quantite_demandee: Optional[int] = 1
    score_total_poste: Optional[float] = 0.0
    criteres_evaluation: List[CriteresEvaluation]
    observations: Optional[str] = ""
    
    verification_mathematique: Optional[VerificationMath] = None
    validation: Optional[ValidationIA] = None
    corrections_apportees: Optional[List[str]] = []
    fallback_applique: Optional[bool] = False
    error: Optional[str] = None

    # 💡 Blindage aussi pour les nombres du profil
    @field_validator('quantite_demandee', mode='before')
    @classmethod
    def empty_int_to_default(cls, v):
        if v == "":
            return 1
        return v

    @field_validator('score_total_poste', mode='before')
    @classmethod
    def empty_float_to_zero(cls, v):
        if v == "":
            return 0.0
        return v

class ExtractedData(BaseModel):
    contexte_mission_globale: Optional[str] = ""
    profils: List[ProfilDemande]

class TenderDataUpdate(BaseModel):
    extracted_data: Optional[ExtractedData] = None
    contexte_mission_globale: Optional[str] = None
    profils: Optional[List[ProfilDemande]] = None