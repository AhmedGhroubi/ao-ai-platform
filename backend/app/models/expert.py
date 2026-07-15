from sqlalchemy import Column, Integer, String, JSON
from app.database.session import Base

class Expert(Base):
    __tablename__ = "experts"

    id = Column(Integer, primary_key=True, index=True)
    slug_unique = Column(String, unique=True, index=True, nullable=True)  # ex: rami-loulou-24101991
    nom_expert = Column(String, nullable=True)                           
    filename = Column(String, nullable=False)                            
    file_path = Column(String, nullable=False)                           
    status = Column(String, default="En attente")                        
    extracted_data = Column(JSON, nullable=True)