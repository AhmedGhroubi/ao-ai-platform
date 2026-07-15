import os
from typing import Any
import uuid
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, BackgroundTasks
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.expert import Expert
from app.schemas.expert import ExpertResponse
from app.ai.expert_parser.expert_extractor import agent_1_civil_academique, agent_2_experiences, agent_3_skills_tagging, agent_4_projets_missions, run_expert_extraction_pipeline, split_cv_sections
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.utils.docx_reader import extract_text_from_docx


router = APIRouter(
    prefix="/experts",
    tags=["Experts"]
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
UPLOAD_DIR = os.path.join(BASE_DIR, "storage", "uploads", "cvs")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload", response_model=ExpertResponse)
def upload_expert_cv(
    file: UploadFile = File(...), 
    background_tasks: BackgroundTasks = BackgroundTasks, 
    db: Session = Depends(get_db)
):
    if not file.filename.endswith('.docx'):
        raise HTTPException(status_code=400, detail="Seuls les fichiers Word (.docx) sont acceptés.")

    # Sauvegarde physique du fichier
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"cv_{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    with open(file_path, "wb") as buffer:
        buffer.write(file.file.read())

    # Enregistrement initial en BDD
    db_expert = Expert(
        filename=file.filename, 
        file_path=file_path,
        status="En attente"
    )
    db.add(db_expert)
    db.commit()
    db.refresh(db_expert)

    # 🚀 Déclenchement de l'Agent IA en arrière-plan
    background_tasks.add_task(run_expert_extraction_pipeline, db_expert.id)
    
    return db_expert


@router.get("/", response_model=list[ExpertResponse])
def list_experts(db: Session = Depends(get_db)):
    """Récupère la liste de tous les experts"""
    return db.query(Expert).all()

@router.get("/{expert_id}", response_model=ExpertResponse)
def get_expert(expert_id: int, db: Session = Depends(get_db)):
    """Récupère un expert précis avec tout son JSON extrait"""
    expert = db.query(Expert).filter(Expert.id == expert_id).first()
    if not expert:
        raise HTTPException(status_code=404, detail="Expert non trouvé")
    return expert

class ExpertUpdate(BaseModel):
    nom_expert: Optional[str] = None
    slug_unique: Optional[str] = None
    status: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None

@router.put("/{expert_id}", response_model=ExpertResponse)
def update_expert(
    expert_id: int, 
    expert_data: ExpertUpdate, 
    db: Session = Depends(get_db)
):
    """Met à jour les informations d'un expert et ses données extraites"""
    
    # 1. Chercher l'expert dans la base de données
    db_expert = db.query(Expert).filter(Expert.id == expert_id).first()
    if not db_expert:
        raise HTTPException(status_code=404, detail="Expert non trouvé")
    
    # 2. Mettre à jour les champs si des données ont été envoyées
    if expert_data.nom_expert is not None:
        db_expert.nom_expert = expert_data.nom_expert
        
    if expert_data.slug_unique is not None:
        db_expert.slug_unique = expert_data.slug_unique
        
    if expert_data.status is not None:
        db_expert.status = expert_data.status
        
    if expert_data.extracted_data is not None:
        
        db_expert.extracted_data = expert_data.extracted_data
    
    # 3. Sauvegarder les modifications
    db.commit()
    db.refresh(db_expert)
    
    return db_expert

@router.delete("/{expert_id}", response_model=dict)
def delete_expert(expert_id: int, db: Session = Depends(get_db)):
    """Supprime un expert et son fichier associé"""
    db_expert = db.query(Expert).filter(Expert.id == expert_id).first()
    if not db_expert:
        raise HTTPException(status_code=404, detail="Expert non trouvé")
    
    # Supprimer le fichier physique si il existe
    if os.path.exists(db_expert.file_path):
        os.remove(db_expert.file_path)
    
    # Supprimer l'entrée de la base de données
    db.delete(db_expert)
    db.commit()
    
    return {"detail": "Expert supprimé avec succès"}

@router.post("/{expert_id}/analyze", response_model=ExpertResponse)
def resume_expert_analysis(
    expert_id: int, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db)
):
    """Relance ou reprend l'analyse IA d'un CV existant"""
    
    # 1. Vérifier que l'expert existe
    db_expert = db.query(Expert).filter(Expert.id == expert_id).first()
    if not db_expert:
        raise HTTPException(status_code=404, detail="Expert non trouvé")
    
    # 2. Mettre à jour le statut pour l'interface
    db_expert.status = "En attente"
    db.commit()
    db.refresh(db_expert)
    
    # 3. Déclenchement de l'Agent IA en arrière-plan (exactement comme dans l'upload)
    background_tasks.add_task(run_expert_extraction_pipeline, db_expert.id)
    
    return db_expert


@router.put("/{expert_id}/reanalyze", response_model=ExpertResponse)
def reanalyze_expert_cv(
    expert_id: int,
    file: UploadFile = File(...), 
    background_tasks: BackgroundTasks = BackgroundTasks, 
    db: Session = Depends(get_db)
):
    """Met à jour le fichier d'un expert existant et relance l'analyse IA de zéro."""
    
    # 1. Vérifier que l'expert existe
    db_expert = db.query(Expert).filter(Expert.id == expert_id).first()
    if not db_expert:
        raise HTTPException(status_code=404, detail="Expert non trouvé")

    # 2. Vérifier le format du nouveau fichier
    if not file.filename.endswith('.docx'):
        raise HTTPException(status_code=400, detail="Seuls les fichiers Word (.docx) sont acceptés.")

    # 3. Sauvegarde physique du NOUVEAU fichier
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"cv_update_{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    with open(file_path, "wb") as buffer:
        buffer.write(file.file.read())

    # 4. (Optionnel mais recommandé) Supprimer l'ancien fichier physique pour ne pas saturer le serveur
    if db_expert.file_path and os.path.exists(db_expert.file_path):
        try:
            os.remove(db_expert.file_path)
        except Exception as e:
            print(f"Erreur lors de la suppression de l'ancien CV : {e}")

    # 5. Mettre à jour l'expert en base de données
    db_expert.filename = file.filename
    db_expert.file_path = file_path
    db_expert.status = "En attente"
    
    # ⚠️ TRÈS IMPORTANT : On vide le JSON précédent pour forcer l'orchestrateur à tout reprendre depuis le début
    db_expert.extracted_data = {} 
    
    db.commit()
    db.refresh(db_expert)

    # 6. 🚀 Déclenchement de l'Agent IA en arrière-plan (exactement comme l'upload)
    background_tasks.add_task(run_expert_extraction_pipeline, db_expert.id)
    
    return db_expert

@router.post("/{expert_id}/reanalyze-section/{section_name}")
def reanalyze_specific_section(
    expert_id: int, 
    section_name: str, 
    db: Session = Depends(get_db)
):
    """Relance l'analyse uniquement pour une section précise (ex: 'experiences', 'projets')."""
    
    # 1. Récupérer l'expert
    db_expert = db.query(Expert).filter(Expert.id == expert_id).first()
    if not db_expert or not db_expert.file_path:
        raise HTTPException(status_code=404, detail="Expert ou fichier introuvable")

    # 2. Extraire le texte du fichier Word existant
    full_text = extract_text_from_docx(db_expert.file_path)
    profile_zone, projects_zone = split_cv_sections(full_text)

    # 3. Préparer la mise à jour du JSON
    # On fait une copie du dictionnaire existant pour ne pas perdre les autres données
    current_data = db_expert.extracted_data.copy() if db_expert.extracted_data else {}

    # 4. Aiguillage selon la section demandée
    try:
        if section_name == "experiences":
            # On n'appelle QUE l'Agent 2
            print("🤖 Appel de l'Agent 2 (Expériences)...")
            experiences_data = agent_2_experiences(profile_zone)
            current_data.update(experiences_data)
            
        elif section_name == "identite":
            # On n'appelle QUE l'Agent 1
            print("🤖 Appel de l'Agent 1 (Identité)...")
            identite_data = agent_1_civil_academique(profile_zone)
            current_data.update(identite_data)
            
        elif section_name == "projets":
            # On n'appelle QUE l'Agent 4
            print("🤖 Appel des Agents Projets...")
            projets_data = agent_4_projets_missions(projects_zone)
            current_data.update(projets_data)
            
        else:
            raise HTTPException(status_code=400, detail="Section inconnue")

        # 5. Sauvegarder les nouvelles données fusionnées
        db_expert.extracted_data = current_data
        db.commit()
        db.refresh(db_expert)
        
        return db_expert

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'analyse : {str(e)}")