from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, Float, ForeignKey, JSON, Text, DateTime
from sqlalchemy.orm import relationship
from app.database.session import Base  

# ========================================================================================
# 1. TABLE : PROFILS REQUIS (TenderRequiredProfile)
# ========================================================================================
class TenderRequiredProfile(Base):
    """
    Représente un profil / poste exigé dans le cahier des charges de l'Appel d'Offre.
    Exemple : 1 "Chef de projet" avec des critères de diplôme, région, compétences, etc.
    """
    __tablename__ = "tender_required_profiles"

    id = Column(Integer, primary_key=True, index=True)
    tender_id = Column(Integer, ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False)
    
    # 💼 Poste standardisé (ex: "Chef de projet", "Expert SIG")
    poste = Column(String, nullable=False)
    quantite = Column(Integer, default=1, nullable=False)
    
    # 📋 Critères d'évaluation dynamiques et leurs pondérations (poids)
    # Format JSON : 
    # [
    #   {"nom": "Diplôme d'Ingénieur", "categorie": "diplome", "poids_max": 1.5, "requis": true},
    #   {"nom": "Expérience globale > 15 ans", "categorie": "experience", "poids_max": 2.0, "requis": true},
    #   {"nom": "Maîtrise de Microsoft Azure", "categorie": "competences", "poids_max": 3.0, "requis": false}
    # ]
    criteres_evaluation = Column(JSON, nullable=False, default=list)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # 🤝 Relations
    tender = relationship("Tender", back_populates="required_profiles")
    staffing_propositions = relationship(
        "TenderStaffing", 
        back_populates="required_profile", 
        cascade="all, delete-orphan"
    )


# ========================================================================================
# 2. TABLE : PROPOSITIONS D'EXPERTS (TenderStaffing)
# ========================================================================================
class TenderStaffing(Base):
    """
    Représente la proposition et l'évaluation d'un expert spécifique pour un profil requis.
    """
    __tablename__ = "tender_staffing"

    id = Column(Integer, primary_key=True, index=True)
    tender_id = Column(Integer, ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False)
    required_profile_id = Column(String, ForeignKey("tender_required_profiles.id", ondelete="CASCADE"), nullable=False)
    expert_id = Column(Integer, ForeignKey("experts.id", ondelete="CASCADE"), nullable=True)
    poste_concerne = Column(String, nullable=False)

    status = Column(String, default="COMPLETED")  # "IN_PROGRESS", "PAUSED", "COMPLETED", "FAILED"

    # 📊 Métriques de matching
    score_global = Column(Integer, nullable=False)  # ex: 85 (Note globale sur 100)
    ranking = Column(Integer, nullable=False)       # Classement (ex: 1 pour le meilleur, 2, 3...)
    confidence = Column(Float, nullable=False, default=1.0) # Indice de confiance de l'évaluation (0.0 à 1.0)

    # 🧬 Détail du score dynamique (Score obtenu vs Max pour chaque critère défini dans le profil)
    # Format JSON :
    # [
    #   {"critere": "Diplôme d'Ingénieur", "score_obtenu": 1.5, "score_maximal": 1.5, "explication": "Possède un diplôme d'ingénieur d'État."},
    #   {"critere": "Expérience globale > 15 ans", "score_obtenu": 2.0, "score_maximal": 2.0, "explication": "Affiche 34 ans d'expérience."}
    # ]
    score_breakdown = Column(JSON, nullable=False, default=list)

    # 💬 Justification IA hautement structurée (Angular va adorer pour le rendu visuel !)
    # Format JSON :
    # {
    #   "resume": "Profil exceptionnel avec plus de 30 ans d'expérience.",
    #   "points_forts": ["Longue expérience en Afrique subsaharienne", "Bilingue Français/Anglais"],
    #   "points_faibles": ["Peu de certifications cloud récentes"],
    #   "criteres_non_satisfaits": ["Certification Azure manquante"]
    # }
    justification_ia = Column(JSON, nullable=False, default=dict)

    # 🤖 Origine de la proposition et traçabilité
    generated_by = Column(String, default="algorithm", nullable=False) # 'algorithm', 'manual', 'hybrid'
    selectionne_par_defaut = Column(Boolean, default=False)             # Choix initial proposé par le solver
    
    # 🔘 Sélection utilisateur
    selectionne_par_user = Column(Boolean, default=False)
    selected_by_user_id = Column(Integer, nullable=True)               # Permet de savoir quel utilisateur a validé ce profil
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 🤝 Relations
    tender = relationship("Tender")
    required_profile = relationship("TenderRequiredProfile", back_populates="staffing_propositions")
    expert = relationship("Expert")