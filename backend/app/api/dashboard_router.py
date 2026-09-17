# app/routers/dashboard_router.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.expert import Expert
from app.models.tender import Tender
from app.models.tender_staffing import TenderStaffing

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("", status_code=200)
def get_dashboard_data(db: Session = Depends(get_db)):
    total_experts = db.query(Expert).count()
    tenders = db.query(Tender).all()
    
    generated_teams_count = 0
    total_scores = []
    recent_tenders = []

    for tender in tenders:
        # Récupération des affectations sauvegardées en BDD
        staffings = db.query(TenderStaffing).filter(TenderStaffing.tender_id == tender.id).all()
        saved_status = tender.saved_staffing.get("status") if isinstance(tender.saved_staffing, dict) else None
        
        has_team = len(staffings) > 0 or saved_status in ["COMPLETED", "GENERATED"]
        
        if has_team:
            generated_teams_count += 1
            scores = [s.score_global for s in staffings if s.score_global is not None]
            avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0
            total_scores.append(avg_score)
            status_str = "GENERATED"
        elif saved_status == "PAUSED":
            avg_score = None
            status_str = "PAUSED"
        else:
            avg_score = None
            status_str = "NO_TEAM"

        recent_tenders.append({
            "id": tender.id,
            "title": getattr(tender, "titre", None) or getattr(tender, "reference", None) or f"AO #{tender.id}",
            "reference": getattr(tender, "reference", f"REF-{tender.id}"),
            "status": status_str,
            "score_match": avg_score,
            "extracted_data": getattr(tender, "extracted_data", {})
        })

    avg_global = round(sum(total_scores) / len(total_scores), 1) if total_scores else 0.0

    return {
        "kpis": {
            "totalExperts": total_experts,
            "totalTenders": len(tenders),
            "generatedTeams": generated_teams_count,
            "avgMatchScore": avg_global
        },
        "recent_tenders": recent_tenders
    }