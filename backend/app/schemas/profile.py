from pydantic import BaseModel
from typing import List, Optional

class CriteresEvaluation(BaseModel):
    type_critere: str
    libelle_exigence: str
    points_maximum: float
    regle_notation: str

class ProfilDemande(BaseModel):
    titre_du_poste: str
    quantite_demandee: int
    criteres_evaluation: List[CriteresEvaluation]
    observations: Optional[str] = ""

class ExtractedData(BaseModel):
    contexte_mission_globale: str
    profils: List[ProfilDemande]

class TenderDataUpdate(BaseModel):
    extracted_data: ExtractedData