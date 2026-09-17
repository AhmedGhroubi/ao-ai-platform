import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, forkJoin, map, catchError, of } from 'rxjs';
import { DashboardResponse, RecentTender } from '../models/dashboard.models';

@Injectable({
  providedIn: 'root'
})
export class DashboardService {
  private http = inject(HttpClient);
  private apiUrl = 'http://localhost:8000/api/tenders/';
  private expertsUrl = 'http://localhost:8000/api/experts/';

  getDashboardData(): Observable<DashboardResponse> {
    return forkJoin({
      tenders: this.http.get<any[]>(this.apiUrl).pipe(catchError(() => of([]))),
      experts: this.http.get<any[]>(this.expertsUrl).pipe(catchError(() => of([])))
    }).pipe(
      map(({ tenders, experts }) => {
        
        // 1. Normalisation des objets Appels d'Offres
        const normalizedTenders: RecentTender[] = tenders.map(t => {
          const actualId = t.id ?? t.tender_id ?? t.id_tender ?? t._id;
          const count = this.calculateProfilesCount(t);
          const score = t.score ?? t.score_match ?? t.score_global_equipe ?? null;

          return {
            id: actualId,
            tender_id: actualId,
            reference: t.reference || `AO-${actualId}`,
            title: t.title || t.titre || t.objet || 'Appel d\'offres sans titre',
            client: t.client || t.organisme || 'Non spécifié',
            profilesCount: count,
            status: this.mapStatus(t.status || t.statut),
            score: score !== null && score !== undefined ? Number(score) : undefined,
            updatedAt: t.updatedAt || t.created_at || 'Récemment',
            extractedData: t.extractedData || t.extracted_data
          };
        });

        // 2. Calculs dynamiques des KPIs
        const totalTenders = normalizedTenders.length;
        const totalExperts = experts.length > 0 ? experts.length : 10;

        const generatedTeams = normalizedTenders.filter(
          t => t.status === 'GENERATED' || t.status === 'VALIDATED'
        ).length;

        // Calcul du score moyen
        const tendersWithScore = normalizedTenders.filter(
          (t): t is RecentTender & { score: number } => typeof t.score === 'number' && t.score > 0
        );

        const avgMatchScore = tendersWithScore.length > 0
          ? Math.round(tendersWithScore.reduce((sum, t) => sum + (t.score ?? 0), 0) / tendersWithScore.length)
          : 0;

        return {
          kpis: {
            totalExperts: totalExperts,
            totalTenders: totalTenders,
            generatedTeams: generatedTeams,
            avgMatchScore: avgMatchScore
          },
          recent_tenders: normalizedTenders
        };
      })
    );
  }

  /**
   * Calcule le nombre total d'experts requis en faisant la somme de quantite_demandee
   */
  private calculateProfilesCount(t: any): number {
    let extracted = t.extractedData || t.extracted_data;

    if (typeof extracted === 'string') {
      try {
        extracted = JSON.parse(extracted);
      } catch (e) {
        console.error('Erreur de lecture du JSON extracted_data', e);
      }
    }

    // Fonction d'accumulation des quantités
    const sumQuantities = (profilsArray: any[]): number => {
      return profilsArray.reduce((total, p) => {
        const qty = Number(p.quantite_demandee ?? p.quantite ?? p.qty ?? 1);
        return total + (isNaN(qty) || qty < 1 ? 1 : qty);
      }, 0);
    };

    // 1. Somme dans extractedData.profils
    if (extracted && Array.isArray(extracted.profils)) {
      return sumQuantities(extracted.profils);
    }

    // 2. Somme si profils/profiles est à la racine
    if (Array.isArray(t.profils)) return sumQuantities(t.profils);
    if (Array.isArray(t.profiles)) return sumQuantities(t.profiles);
    if (Array.isArray(t.profils_recherche)) return sumQuantities(t.profils_recherche);

    return t.profilesCount || t.nb_profils || 0;
  }

  private mapStatus(rawStatus: string): 'NO_TEAM' | 'PAUSED' | 'GENERATED' | 'VALIDATED' {
    if (!rawStatus) return 'NO_TEAM';
    const s = rawStatus.toUpperCase();
    if (s.includes('PAUSE')) return 'PAUSED';
    if (s.includes('VALI')) return 'VALIDATED';
    if (s.includes('GEN') || s.includes('CREAT')) return 'GENERATED';
    return 'NO_TEAM';
  }
}