import { inject, Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { 
  StaffingGenerationResponse, 
  ExpertSelectionResponse, 
  AlternativeCandidate 
} from '../models/staffing.models';

@Injectable({
  providedIn: 'root'
})
export class StaffingService {
  private http = inject(HttpClient);
  private apiUrl = `${environment.apiUrl}/api/tenders`; 

  /**
   * 💾 Vérifier si une équipe sauvegardée existe en BDD (Lecture 0 ms)
   */
  getSavedTeam(tenderId: number): Observable<StaffingGenerationResponse & { has_saved_team: boolean }> {
    return this.http.get<StaffingGenerationResponse & { has_saved_team: boolean }>(
      `${this.apiUrl}/${tenderId}/staffing`
    );
  }

  /**
   * ⚡ Génère ou régénère l'équipe optimale.
   * @param forceRecalculate - Mettre à `true` pour forcer le Solver/IA à recalculer.
   */
  generateStaffing(tenderId: number, forceRecalculate: boolean = false): Observable<StaffingGenerationResponse> {
    let params = new HttpParams();
    if (forceRecalculate) {
      params = params.set('force_recalculate', 'true');
    }

    return this.http.post<StaffingGenerationResponse>(
      `${this.apiUrl}/${tenderId}/staffing/generate`, 
      {}, 
      { params }
    );
  }

/**
   * ✋ Enregistre un choix humain (DRH) sur un slot précis sans dupliquer la ligne
   */
  selectManualExpert(
    tenderId: number, 
    requiredProfileId: string | number, 
    expertId: number,
    oldExpertId?: number 
  ): Observable<ExpertSelectionResponse> {
    const payload: { required_profile_id: string | number; expert_id: number; old_expert_id?: number } = { 
      required_profile_id: requiredProfileId, 
      expert_id: expertId 
    };

    if (oldExpertId) {
      payload.old_expert_id = oldExpertId;
    }

    return this.http.put<ExpertSelectionResponse>(
      `${this.apiUrl}/${tenderId}/staffing/select`, 
      payload
    );
  }

  /**
   * 🔍 Récupère le Top 10 des candidats alternatifs pour un profil
   */
  getCandidatesForProfile(
    tenderId: number, 
    profileId: string | number
  ): Observable<AlternativeCandidate[]> {
    return this.http.get<AlternativeCandidate[]>(
      `${this.apiUrl}/${tenderId}/staffing/candidates/${profileId}`
    );
  }
}