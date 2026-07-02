from sqlalchemy import Column, DateTime, Integer, String, Text,JSON, func
from app.database.session import Base 

class Tender(Base):
    __tablename__ = "tenders"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    reference = Column(String, unique=True, index=True)
    raw_text = Column(Text, nullable=True)
    file_path = Column(String, nullable=True)
    extracted_data = Column(JSON, nullable=True)
    status = Column(String, default="En attente")
    created_at = Column(DateTime(timezone=True), server_default=func.now())