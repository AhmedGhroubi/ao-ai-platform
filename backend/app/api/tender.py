import os
import shutil
import uuid
from fastapi import APIRouter, Depends, HTTPException,File, UploadFile, Form, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database.session import get_db
from app.models.tender import Tender
from app.schemas.tender import TenderBase, TenderCreate, TenderResponse
import fitz
from app.schemas.profile import TenderDataUpdate
from app.ai.tender_parser.multi_agent_extractor import run_tender_multi_agent_pipeline
from app.database.session import SessionLocal 


router = APIRouter(
    prefix="/tenders",
    tags=["Tenders"]
)

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
UPLOAD_DIR = os.path.join(BASE_DIR, "storage", "uploads", "tenders")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Limite de sécurité pour la détection automatique de pages
# Groq Vision = max 5 images par appel → on garde 4 pour la marge
# Le pipeline gère lui-même le chunking si on dépasse cette limite
MAX_AUTO_PAGES = 4


def process_tender_in_background(tender_id: int, pdf_path: str, auto_reference: str, pages_input: str):
    """Fonction exécutée en arrière-plan par FastAPI"""
    db = SessionLocal() # Nouvelle session pour l'arrière-plan
    
    try:
        # Récupération du tender en cours
        tender = db.query(Tender).filter(Tender.id == tender_id).first()
        if not tender:
            return

        doc = fitz.open(pdf_path)
        pages_to_extract = []

        # ── Sélection des pages ───────────────────────────────────────────────
        if pages_input:
            if "-" in pages_input and "," not in pages_input:
                parts = pages_input.split("-")
                start, end = int(parts[0].strip()), int(parts[1].strip())
                pages_to_extract = list(range(start - 1, min(end, len(doc))))
            else:
                pages_to_extract = [int(p.strip()) - 1 for p in pages_input.split(",")]
                pages_to_extract = [p for p in pages_to_extract if 0 <= p < len(doc)]
        else:
            mots_cles = [
                "chef de mission", "analyste fonctionnel", "expert en bases de données",
                "grille d'évaluation", "qualification générale", "adéquation pour la mission",
                "expérience dans la région", "position pc-"
            ]
            pages_set = set()
            for i in range(len(doc)):
                page_text = doc[i].get_text("text").lower()
                if any(mot in page_text for mot in mots_cles):
                    pages_set.add(i)            
                pages_to_extract = sorted(list(pages_set))

        # Calcul de start_page et end_page
        if pages_to_extract:
            start_page = min(pages_to_extract) + 1  
            end_page   = max(pages_to_extract) + 1  
        else:
            start_page, end_page = None, None

        doc.close()

        # ── Lancement du pipeline IA ──────────────────────────────────────────
        result_json = run_tender_multi_agent_pipeline(
            pdf_path=pdf_path,
            tender_id=str(tender.id),
            reference=auto_reference,
            start_page=start_page,
            end_page=end_page,
            dpi=100,
        )

        # ── 🛑 SÉCURITÉ ANNULATION / SUPPRESSION ──────────────────────────────
        # Force SQLAlchemy à recharger l'état réel de la BDD (ignore le cache local)
        db.expire_all() 
        tender = db.query(Tender).filter(Tender.id == tender_id).first()
        
        # Cas 1 : Le tender a été complètement supprimé de la BDD pendant l'analyse
        if not tender:
            print(f"🛑 [Background Task] Le tender #{tender_id} a été supprimé par l'utilisateur. Arrêt propre.")
            db.rollback()
            return

        # Cas 2 : L'IA renvoie un dictionnaire signalant qu'elle a stoppé suite à une annulation
        if result_json and isinstance(result_json, dict) and "error" in result_json:
            error_msg = str(result_json.get("error")).lower()
            if "interrompue" in error_msg or "supprimé" in error_msg:
                print(f"🛑 [Background Task] Analyse interrompue pour le tender #{tender_id}. Pas de mise à jour.")
                db.rollback()
                return

        # ── Mise à jour normale de la Base de Données ─────────────────────────
        if result_json:
            tender.extracted_data = result_json
            tender.status = "Analysé" 
        else:
            tender.status = "Erreur"
        
        db.commit()

    except Exception as e:
        print(f"❌ Erreur Background Task: {e}")
        db.rollback()
        try:
            # En cas de crash, on ne passe en statut "Erreur" QUE si la ligne existe encore
            tender = db.query(Tender).filter(Tender.id == tender_id).first()
            if tender:
                tender.status = "Erreur"
                db.commit()
        except Exception as db_err:
            print(f"⚠️ Impossible de mettre à jour le statut d'erreur (Tender probablement supprimé) : {db_err}")

    finally:
        # Nettoyage du PDF et fermeture de la session DB
        if os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
            except Exception as file_err:
                print(f"⚠️ Erreur lors de la suppression du fichier physique : {file_err}")
        db.close()

@router.post("/upload/")
async def upload_tender(
    background_tasks: BackgroundTasks,
    pages: str = Form(None, description="Pages à extraire, ex: '37,38,39' ou '37-42'"),
    file: UploadFile = File(...),
    title: str =Form(...),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Le fichier doit être un PDF.")

    # 1. Création en DB avec le statut "En cours"
    auto_reference = f"REF-{uuid.uuid4().hex[:4].upper()}"
    new_tender = Tender(reference=auto_reference, title=title, status="En cours")
    db.add(new_tender)
    db.commit()
    db.refresh(new_tender)

    # 2. Sauvegarde PHYSIQUE du fichier AVANT de lancer la tâche
    pdf_path = os.path.join(UPLOAD_DIR, f"{new_tender.id}_{file.filename}")
    with open(pdf_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 3. On délègue le travail lourd à la tâche en arrière-plan
    background_tasks.add_task(
        process_tender_in_background,  
        tender_id=new_tender.id,
        pdf_path=pdf_path,
        auto_reference=auto_reference,
        pages_input=pages
    )

    # 4. Le RETURN immédiat 
    return {
        "message": "Upload réussi, analyse en cours...",
        "tender_id": new_tender.id,
        "reference": auto_reference
    }

@router.get("/", response_model=List[TenderResponse])
def read_tenders(skip: int = 0, db: Session = Depends(get_db)):
    return db.query(Tender).offset(skip).all()


@router.get("/{tender_id}", response_model=TenderResponse)
def read_tender(tender_id: int, db: Session = Depends(get_db)):
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Appel d'offres non trouvé")
    return tender


@router.put("/{tender_id}/save-extracted-data")
async def save_verified_data(
    tender_id: int,
    data: TenderDataUpdate,
    db: Session = Depends(get_db)
):
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Appel d'offres non trouvé")

    # 1. Sauvegarde de extracted_data
    if data.extracted_data:
        tender.extracted_data = data.extracted_data.model_dump()
    else:
        tender.extracted_data = {
            "contexte_mission_globale": data.contexte_mission_globale,
            "profils": [p.model_dump() for p in (data.profils or [])]
        }
        
    # 🌍 2. NOUVEAU : Sauvegarde des régions ciblées à la racine
    if hasattr(data, 'regions_ciblees') and data.regions_ciblees is not None:
        tender.regions_ciblees = data.regions_ciblees
        
    tender.status = "Analysé"
    db.commit()
    
    return {"message": "Données et régions sauvegardées avec succès !"}


@router.delete("/{tender_id}")
def delete_tender(tender_id: int, db: Session = Depends(get_db)):
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Appel d'offres non trouvé")
    db.delete(tender)
    db.commit()
    return {"message": "Appel d'offres supprimé avec succès"}

@router.post("/{tender_id}/cancel")
def cancel_tender_analysis(tender_id: int, db: Session = Depends(get_db)):
    # 1. Rechercher le tender
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Appel d'offres non trouvé")
    
    # 2. Vérifier s'il est bien en cours d'analyse
    if tender.status != "En cours":
        raise HTTPException(status_code=400, detail="L'analyse n'est pas en cours")
    
    # 3. Changer le statut pour interrompre le flux
    tender.status = "En attente"  # Ou "Annulé" si tu as créé un statut dédié
    db.commit()
    
    return {"message": "L'analyse a été annulée avec succès"}