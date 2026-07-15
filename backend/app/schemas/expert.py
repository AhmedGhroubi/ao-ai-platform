from pydantic import BaseModel
from typing import Optional, Any

class ExpertResponse(BaseModel):
    id: int
    slug_unique: Optional[str] = None
    nom_expert: Optional[str] = None
    filename: str
    status: str
    extracted_data: Optional[Any] = None

    class Config:
        from_attributes = True