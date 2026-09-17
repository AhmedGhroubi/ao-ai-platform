
from sqlalchemy import Column, String, Boolean, Text, Float, Integer
from app.database.session import Base

class SemanticCache(Base):
    __tablename__ = "semantic_cache"

    id = Column(Integer, primary_key=True, index=True)
    cache_hash = Column(String(32), unique=True, index=True) 
    critere = Column(Text, nullable=False)
    valeur_cv = Column(Text, nullable=True)
    match_result = Column(Boolean, nullable=False)          
    confidence = Column(Float, nullable=False)              
    explication = Column(Text, nullable=True)
    source = Column(String(50), nullable=False)             