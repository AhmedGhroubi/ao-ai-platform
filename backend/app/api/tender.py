import os
import shutil
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form, Query
from sqlalchemy.orm import Session
from typing import List
from typing import Optional
from app.database.session import get_db
from app.models.tender import Tender
from app.schemas.tender import TenderBase, TenderCreate, TenderResponse
from app.ai.tender_parser.pdf_extractor import extract_text_and_tables_from_pdf
import nest_asyncio
from llama_parse import LlamaParse
from PyPDF2 import PdfReader, PdfWriter
import tempfile
import fitz
from app.ai.tender_parser.profile_extractor import extract_profiles_from_images
from app.schemas.profile import TenderDataUpdate



nest_asyncio.apply()

router = APIRouter(
    prefix="/tenders",
    tags=["Tenders"]
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
UPLOAD_DIR = os.path.join(BASE_DIR, "storage", "uploads", "tenders")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload/")
async def upload_tender(
    pages: str = Form(None, description="Pages à extraire (ex: 37,38)"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Le fichier doit être un PDF.")

    # 1. Génération de la référence et création immédiate en DB pour obtenir l'ID
    auto_reference = f"REF-{uuid.uuid4().hex[:4].upper()}"
    new_tender = Tender(reference=auto_reference) 
    db.add(new_tender)
    db.commit()
    db.refresh(new_tender) # MAGIE : new_tender.id contient maintenant l'ID généré par PostgreSQL !

    pdf_path = os.path.join(UPLOAD_DIR, file.filename)

    # Sauvegarde temporaire du fichier
    with open(pdf_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    image_paths = []
    try:
        doc = fitz.open(pdf_path)
        pages_to_extract = []

        # Sélection des pages
        if pages:
            try:
                pages_to_extract = [int(p.strip())-1 for p in pages.split(",")]
                pages_to_extract = [p for p in pages_to_extract if 0 <= p < len(doc)]
            except ValueError:
                raise HTTPException(status_code=400, detail="Format des pages invalide.")
        else:
            mots_cles = ["chef de mission", "analyste fonctionnel", "expert en bases de données", "grille d'évaluation"]
            pages_set = set()
            for i in range(len(doc)):
                page_text = doc[i].get_text("text").lower()
                if any(mot in page_text for mot in mots_cles):
                    pages_set.add(i)
            pages_to_extract = sorted(list(pages_set))[:6]

        if not pages_to_extract:
            raise HTTPException(status_code=404, detail="Aucune page pertinente trouvée.")

        # 2. Extraction en images (On utilise new_tender.id)
        for idx in pages_to_extract:
            page = doc.load_page(idx)
            pix = page.get_pixmap(dpi=200) 
            img_path = os.path.join(UPLOAD_DIR, f"temp_page_{new_tender.id}_{idx}.jpg")
            pix.save(img_path)
            image_paths.append(img_path)
        doc.close()

        # 3. Analyse IA (On utilise new_tender.id et auto_reference)
        result_json = extract_profiles_from_images(image_paths, new_tender.id, auto_reference)
        
        if not result_json:
            raise HTTPException(status_code=500, detail="L'extraction Vision a échoué.")

        # 4. Mise à jour de l'entrée existante avec le JSON
        new_tender.extracted_data = result_json
        db.commit()
        db.refresh(new_tender)
        
        return {"message": "Tender analysé et sauvegardé avec succès", "data": result_json}

    except Exception as e:
        # En cas d'erreur pendant l'IA, on supprime le tender qu'on avait créé au début pour garder la BDD propre
        db.delete(new_tender)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Erreur interne : {str(e)}")

    finally:
        # Nettoyage des fichiers temporaires
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        for img_path in image_paths:
            if os.path.exists(img_path):
                os.remove(img_path)


@router.get("/", response_model=List[TenderResponse])
def read_tenders(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    tenders = db.query(Tender).offset(skip).limit(limit).all()
    return tenders

@router.put("/{tender_id}/save-extracted-data")
async def save_verified_data(
    tender_id: int,
    data: TenderDataUpdate,
    db: Session = Depends(get_db)
):
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Appel d'offres non trouvé")

    # Mise à jour des données (Pydantic convertit automatiquement en dict)
    tender.extracted_data = data.model_dump()
    tender.status = "Analysé"
    db.commit()
    return {"message": "Données sauvegardées avec succès !"}

@router.get("/{tender_id}", response_model=TenderResponse)
def read_tender(tender_id: int, db: Session = Depends(get_db)):
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Appel d'offres non trouvé")
    return tender

@router.delete("/{tender_id}")
def delete_tender(tender_id: int, db: Session = Depends(get_db)):
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Appel d'offres non trouvé")
    
    db.delete(tender)
    db.commit()
    return {"message": "Appel d'offres supprimé avec succès"}


