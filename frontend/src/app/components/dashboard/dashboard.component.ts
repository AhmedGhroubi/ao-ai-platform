import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { DashboardService } from '../../services/dashboard.service';
import { DashboardKpi, DashboardResponse, RecentTender } from '../../models/dashboard.models';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css']
})
export class DashboardComponent implements OnInit {
  private router = inject(Router);
  private dashboardService = inject(DashboardService);

  loading: boolean = true;
  errorMessage: string | null = null;

  // Données réelles
  kpis: DashboardKpi = {
    totalExperts: 0,
    totalTenders: 0,
    generatedTeams: 0,
    avgMatchScore: 0
  };

  // Données pour l'animation visuelle
  displayKpis: DashboardKpi = {
    totalExperts: 0,
    totalTenders: 0,
    generatedTeams: 0,
    avgMatchScore: 0
  };

  recentTenders: RecentTender[] = [];

  ngOnInit(): void {
    this.loadDashboardData();
  }

  loadDashboardData(): void {
    this.loading = true;
    this.errorMessage = null;

    this.dashboardService.getDashboardData().subscribe({
      next: (data: DashboardResponse) => {
        if (data) {
          this.recentTenders = data.recent_tenders || [];
          this.kpis = data.kpis;
          this.animateKpis(this.kpis, 1200);
        }
        this.loading = false;
      },
      error: (err) => {
        this.loading = false;
        this.errorMessage = "Impossible de charger les données du tableau de bord.";
        console.error('Erreur Dashboard:', err);
      }
    });
  }

  private animateKpis(targetKpis: DashboardKpi, duration: number = 1000): void {
    const startTime = performance.now();

    const step = (currentTime: number) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const easeOutProgress = progress * (2 - progress);

      this.displayKpis = {
        totalExperts: Math.floor(easeOutProgress * targetKpis.totalExperts),
        totalTenders: Math.floor(easeOutProgress * targetKpis.totalTenders),
        generatedTeams: Math.floor(easeOutProgress * targetKpis.generatedTeams),
        avgMatchScore: Math.floor(easeOutProgress * targetKpis.avgMatchScore)
      };

      if (progress < 1) {
        requestAnimationFrame(step);
      } else {
        this.displayKpis = { ...targetKpis };
      }
    };

    requestAnimationFrame(step);
  }

  getProfilesCount(tender: any): number {
    if (!tender) return 0;

    let data = tender.extractedData || tender.extracted_data;

    if (typeof data === 'string') {
      try { data = JSON.parse(data); } catch (e) {}
    }

    const profilsArray =
      (data && Array.isArray(data.profils) && data.profils) ||
      (data && Array.isArray(data.profiles) && data.profiles) ||
      (Array.isArray(tender.profils) && tender.profils) ||
      (Array.isArray(tender.profiles) && tender.profiles) ||
      (Array.isArray(tender.profils_recherche) && tender.profils_recherche);

    if (profilsArray && profilsArray.length > 0) {
      return profilsArray.reduce((sum: number, p: any) => {
        const qty = Number(
          p.quantite_demandee ??
          p.quantite ??
          p.nb_postes ??
          p.nombre_postes ??
          p.nombre ??
          p.qty ??
          p.count ??
          1
        );
        return sum + (isNaN(qty) || qty < 1 ? 1 : qty);
      }, 0);
    }

    if (typeof tender.profilesCount === 'number' && tender.profilesCount > 0) {
      return tender.profilesCount;
    }

    return tender.profils_count ?? tender.nb_profils ?? 0;
  }

  // --- MÉTHODES UTILITAIRES POUR LE TEMPLATE ---

  getTenderScore(tender: any): number | null {
    if (!tender) return null;
    const score = tender.score ?? tender.score_match ?? tender.score_global_equipe;
    return score !== undefined && score !== null && score > 0 ? Number(score) : null;
  }

  getStatusClass(tender: any): string {
    const status = tender?.status;
    if (!status || status === 'NO_TEAM' || status === 'Non analysé') return 'status-none';
    if (status === 'PAUSED') return 'status-paused';
    if (['GENERATED', 'GENERE', 'COMPLETED'].includes(status)) return 'status-generated';
    if (status === 'VALIDATED') return 'status-validated';
    return 'status-none';
  }

  getStatusLabel(tender: any): string {
    const status = tender?.status;
    if (status === 'PAUSED') return '⏸️ Traitement en Pause';
    if (['GENERATED', 'GENERE', 'COMPLETED'].includes(status)) return '⚡ Équipe Générée';
    if (status === 'VALIDATED') return '✅ Équipe Validée';
    return '⚪ Non analysé';
  }

  canGenerate(tender: any): boolean {
    const status = tender?.status;
    return !status || status === 'NO_TEAM' || status === 'Non analysé';
  }

  canResume(tender: any): boolean {
    return tender?.status === 'PAUSED';
  }

  canView(tender: any): boolean {
    const status = tender?.status;
    return ['GENERATED', 'GENERE', 'COMPLETED', 'VALIDATED'].includes(status);
  }

  // --- NAVIGATION ---

  navigateToStaffing(tender: RecentTender | any): void {
    const targetId = tender?.id ?? tender?.tender_id ?? tender?.id_tender;
    if (!targetId || targetId === 'undefined') {
      alert("Impossible d'ouvrir cet appel d'offres : ID manquant.");
      return;
    }
    this.router.navigate(['/staffing', targetId]);
  }

  createNewTender(): void { this.router.navigate(['/upload']); }
  createNewExpert(): void { this.router.navigate(['/experts/upload']); }
  viewAllTenders(): void { this.router.navigate(['/list']); }
}