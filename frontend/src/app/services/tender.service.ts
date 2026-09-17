import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

// ==========================================
//  INTERFACES POUR LE MULTI-AGENT
// ==========================================
export interface CritereEvaluation {
  type_critere: string;
  libelle_exigence: string;
  points_maximum: number;
  regle_notation: string;
}

export interface ValidationIA {
  necessite_verification_humaine: boolean;
  motif_doute: string;
}

export interface Profil {
  id: string; // UUID généré par le backend pour le trackBy Angular
  titre_du_poste: string;
  quantite_demandee: number;
  criteres_evaluation: CritereEvaluation[];
  validation: ValidationIA;
  observations: string;
}

export interface TenderResponse {
  tender_id: number;
  reference: string;
  title?: string;
  status: string;
  extracted_data: {
    contexte_mission_globale: string;
    profils: Profil[];
  };
  regions_ciblees: string[];
}

@Injectable({
  providedIn: 'root'
})
export class TenderService {
  private apiUrl = 'http://127.0.0.1:8000'; 

  constructor(private http: HttpClient) {}

  // 1. Uploader un nouveau PDF (Retourne maintenant les données typées)
  uploadTender(formData: FormData): Observable<TenderResponse> {
    return this.http.post<TenderResponse>(`${this.apiUrl}/api/tenders/upload/`, formData);
  }

  // 2. Récupérer un appel d'offres par son ID
  getTenderById(id: number): Observable<TenderResponse> {
    return this.http.get<TenderResponse>(`${this.apiUrl}/api/tenders/${id}`);
  }

  // 3. Récupérer la liste des Tenders
  getAllTenders(): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/api/tenders/`); 
  }

  // 4. Sauvegarder les modifications
  updateTenderData(tenderId: number, data: any): Observable<TenderResponse> {
    return this.http.put<TenderResponse>(`${this.apiUrl}/api/tenders/${tenderId}/save-extracted-data`, data);
  }
  
  // 5. Supprimer
  deleteTender(id: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/api/tenders/${id}`);
  }
  // 6. Annuler l'analyse
  cancelTenderAnalysis(id: number): Observable<any> {
  return this.http.post<any>(`${this.apiUrl}/api/tenders/${id}/cancel`, {});
}
}