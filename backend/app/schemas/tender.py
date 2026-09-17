from datetime import datetime

from pydantic import BaseModel
from typing import Any, Dict, Optional,List

# Schéma de base contenant les attributs communs
class TenderBase(BaseModel):
    title: Optional[str] = None
    reference: str
    raw_text: Optional[str] = None
    file_path: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None
    status: Optional[str] = "En attente"
    created_at: Optional[datetime] = None

# Schéma requis pour la création (ce que le Frontend va envoyer)
class TenderCreate(TenderBase):
    pass  # Pour l'instant, on a besoin des mêmes champs que la base

# Schéma utilisé pour renvoyer la donnée (ce que l'API va répondre)
class TenderResponse(TenderBase):
    id: int
    regions_ciblees: Optional[List[str]] = None

    # Indique à Pydantic de lire les données même si ce sont des modèles ORM (SQLAlchemy)
    class Config:
        from_attributes = True