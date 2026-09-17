import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { StaffingService } from '../../services/staffing.service';
import { StaffingGenerationResponse, StaffingSlot, AlternativeCandidate } from '../../models/staffing.models';
import { ExportService, TeamMemberExport } from '../../services/export.service';

@Component({
  selector: 'app-staffing-dashboard',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './staffing-dashboard.component.html',
  styleUrls: ['./staffing-dashboard.component.css']
})
export class StaffingDashboardComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private staffingService = inject(StaffingService);
  
  // Service d'exportation
  public exportService = inject(ExportService);

  // Propriétés de l'Appel d'Offres
  tenderTitle: string = "Appel d'Offres";

  // États applicatifs
  tenderId!: number;
  staffingData: StaffingGenerationResponse | null = null;
  loading: boolean = false;
  isPaused: boolean = false;
  isRateLimited: boolean = false;
  errorMessage: string | null = null;
  activeJustificationSlotId: string | number | null = null;
  conflictWarning: {
    expertId: number;
    expertName: string;
    currentSlot: StaffingSlot;
    conflictingSlot: StaffingSlot;
    replacementExpert?: AlternativeCandidate | null;
  } | null = null;

  ngOnInit(): void {
    const paramId = this.route.snapshot.paramMap.get('tenderId');
    if (paramId) {
      this.tenderId = +paramId;
      this.loadInitialStaffing();
    } else {
      this.errorMessage = "Impossible de récupérer l'identifiant de l'appel d'offres dans l'URL.";
    }
  }

  /**
   * ⚡ 1. Chargement initial : Vérifie l'état BDD + le localStorage pour restaurer l'état de pause
   */
  loadInitialStaffing(): void {
    this.loading = true;
    this.errorMessage = null;

    const wasPausedLocally = localStorage.getItem(`staffing_paused_${this.tenderId}`) === 'true';

    this.staffingService.getSavedTeam(this.tenderId).subscribe({
      next: (res) => {
        this.loading = false;

        if (!res) {
          this.staffingData = null;
          this.setPausedState(wasPausedLocally);
          return;
        }

        const isPausedStatus = wasPausedLocally || 
                               res.status?.toUpperCase() === 'PAUSED' || 
                               (res as any).is_paused === true;

        if (isPausedStatus) {
          this.applyStaffingResponse(res);
          this.setPausedState(true);
          return;
        }

        if (res.has_saved_team || (res.proposition_equipe && res.proposition_equipe.length > 0)) {
          this.applyStaffingResponse(res);
          this.setPausedState(false);
        } else {
          this.staffingData = null;
          this.setPausedState(false);
        }
      },
      error: () => {
        this.loading = false;
        if (wasPausedLocally) {
          this.setPausedState(true);
        } else {
          this.staffingData = null;
          this.setPausedState(false);
        }
      }
    });
  }

  /**
   * 🚀 Génération / Reprise de l'optimisation
   */
  onTriggerOptimization(forceRecalculate: boolean = true): void {
    const shouldForce = this.isPaused ? false : forceRecalculate;

    this.loading = true;
    this.errorMessage = null;

    this.staffingService.generateStaffing(this.tenderId, shouldForce).subscribe({
      next: (res) => {
        this.applyStaffingResponse(res);
        this.loading = false;

        const isPausedStatus = res.status?.toUpperCase() === 'PAUSED' || (res as any).is_paused === true;

        if (isPausedStatus) {
          this.setPausedState(true);
        } else {
          this.setPausedState(false);
        }
      },
      error: (err) => {
        this.loading = false;
        if (err.status === 429) {
          this.setPausedState(true);
        } else {
          this.setPausedState(false);
          this.errorMessage = err.error?.detail || "Une erreur est survenue lors de l'optimisation.";
        }
      }
    });
  }

  /**
   * 🛠️ Gestionnaire centralisé de l'état de pause
   */
  private setPausedState(paused: boolean): void {
    this.isPaused = paused;
    this.isRateLimited = paused;

    if (paused) {
      localStorage.setItem(`staffing_paused_${this.tenderId}`, 'true');
      this.errorMessage = "Traitement en pause : Limite d'appels IA atteinte. La progression est sauvegardée. Vous pouvez cliquer sur 'Reprendre'.";
    } else {
      localStorage.removeItem(`staffing_paused_${this.tenderId}`);
    }
  }

  /**
   * ✋ Sélection d'une alternative simple pour un poste
   */
  onSelectAlternative(slot: StaffingSlot, alternative: AlternativeCandidate): void {
    const oldExpert = slot.expert_selectionne;
    const conflictingSlot = this.findAssignedSlotForExpert(alternative.expert_id, slot);

    if (conflictingSlot) {
      this.conflictWarning = {
        expertId: alternative.expert_id,
        expertName: alternative.nom_expert,
        currentSlot: slot,
        conflictingSlot: conflictingSlot,
        replacementExpert: alternative
      };
      this.errorMessage = null;
      return;
    }

    this.staffingService.selectManualExpert(
      this.tenderId, 
      slot.required_profile_id, 
      alternative.expert_id, 
      oldExpert?.expert_id
    ).subscribe({
      next: (response) => {
        const selectedExpert = {
          expert_id: alternative.expert_id,
          nom_expert: alternative.nom_expert,
          score_global: response.score_global,
          confidence: alternative.confidence,
          score_breakdown: alternative.score_breakdown,
          justification_ia: response.justification_ia,
          selectionne_par_defaut: false,
          selectionne_par_user: true
        };

        slot.expert_selectionne = selectedExpert;
        slot.showAlternatives = false;
        this.clearConflictWarning();

        this.refreshSlotCandidatesList(slot.required_profile_id);
        this.recalculateGlobalScore();
      },
      error: () => {
        slot.expert_selectionne = oldExpert;
        this.errorMessage = "Impossible d'appliquer ce changement d'expert.";
      }
    });
  }

  confirmConflictReplacement(): void {
    if (!this.conflictWarning || !this.staffingData) return;

    const currentSlot = this.conflictWarning.currentSlot;
    const conflictingSlot = this.conflictWarning.conflictingSlot;
    const expertB = this.conflictWarning.replacementExpert;
    const expertA = currentSlot.expert_selectionne;

    if (!currentSlot || !conflictingSlot || !expertB || !expertA) {
      this.clearConflictWarning();
      return;
    }

    this.loading = true;
    this.errorMessage = null;

    this.staffingService.selectManualExpert(
      this.tenderId, 
      currentSlot.required_profile_id, 
      expertB.expert_id, 
      expertA.expert_id
    ).subscribe({
      next: (currentResponse) => {
        this.staffingService.selectManualExpert(
          this.tenderId, 
          conflictingSlot.required_profile_id, 
          expertA.expert_id, 
          expertB.expert_id
        ).subscribe({
          next: (conflictingResponse) => {
            this.applySelectedExpertToSlot(currentSlot, expertB, currentResponse.justification_ia, currentResponse.score_global);
            this.applySelectedExpertToSlot(conflictingSlot, expertA, conflictingResponse.justification_ia, conflictingResponse.score_global);

            currentSlot.showAlternatives = false;
            conflictingSlot.showAlternatives = false;

            this.refreshSlotCandidatesList(currentSlot.required_profile_id);
            this.refreshSlotCandidatesList(conflictingSlot.required_profile_id);

            this.recalculateGlobalScore();
            this.clearConflictWarning();
            this.loading = false;
          },
          error: () => {
            this.loading = false;
            this.errorMessage = "Impossible de finaliser l'échange sur le second poste.";
          }
        });
      },
      error: () => {
        this.loading = false;
        this.errorMessage = "Impossible de sauvegarder la première partie de l'échange.";
      }
    });
  }

  refreshSlotCandidatesList(profileId: string | number): void {
    this.staffingService.getCandidatesForProfile(this.tenderId, profileId).subscribe(candidates => {
      const slot = this.staffingData?.proposition_equipe.find(
        s => String(s.required_profile_id) === String(profileId)
      );
      if (slot) {
        slot.alternatives = candidates.filter(c => c.expert_id !== slot.expert_selectionne?.expert_id);
      }
    });
  }

  toggleAlternatives(slot: StaffingSlot): void {
    slot.showAlternatives = !slot.showAlternatives;
    if (slot.showAlternatives && (!slot.alternatives || slot.alternatives.length === 0)) {
      this.refreshSlotCandidatesList(slot.required_profile_id);
    }
  }

  private applySelectedExpertToSlot(slot: StaffingSlot, expert: AlternativeCandidate | any, justificationIa?: any, scoreGlobal?: number): void {
    slot.expert_selectionne = {
      expert_id: expert.expert_id,
      nom_expert: expert.nom_expert,
      score_global: scoreGlobal ?? expert.score_global ?? 0,
      confidence: expert.confidence ?? 0,
      score_breakdown: expert.score_breakdown ?? [],
      justification_ia: justificationIa ?? expert.justification_ia ?? { resume: '', points_forts: [], points_faibles: [], criteres_non_satisfaits: [] },
      selectionne_par_defaut: false,
      selectionne_par_user: true
    };
  }

  private recalculateGlobalScore(): void {
    if (this.staffingData?.proposition_equipe?.length) {
      const totalScore = this.staffingData.proposition_equipe.reduce(
        (sum, slot) => sum + (slot.expert_selectionne?.score_global || 0),
        0
      );
      this.staffingData.score_global_equipe = Math.round((totalScore / this.staffingData.proposition_equipe.length) * 100) / 100;
    }
  }

  findAssignedSlotForExpert(expertId: number, currentSlot?: StaffingSlot): StaffingSlot | null {
    if (!this.staffingData?.proposition_equipe) return null;

    return this.staffingData.proposition_equipe.find((slot) => {
      const isSameExpert = slot.expert_selectionne?.expert_id === expertId;
      const isDifferentSlot = slot !== currentSlot;
      return isSameExpert && isDifferentSlot;
    }) ?? null;
  }

  isSlotInConflict(slot: StaffingSlot): boolean {
    if (!this.conflictWarning) return false;
    return this.conflictWarning.currentSlot === slot || this.conflictWarning.conflictingSlot === slot;
  }

  clearConflictWarning(): void {
    this.conflictWarning = null;
  }

  toggleJustificationDrawer(profileId: string | number): void {
    this.activeJustificationSlotId = this.activeJustificationSlotId === profileId ? null : profileId;
  }

  private applyStaffingResponse(res: StaffingGenerationResponse): void {
    this.staffingData = res;
    this.activeJustificationSlotId = null;
    this.conflictWarning = null;

    // Mise à jour dynamique du titre du projet si fourni par l'API
    if ((res as any).tender_title || (res as any).title || (res as any).reference) {
      this.tenderTitle = (res as any).tender_title || (res as any).title || (res as any).reference;
    }

    if (Array.isArray(res.proposition_equipe)) {
      res.proposition_equipe.forEach((slot) => {
        slot.showAlternatives = false;
        slot.alternatives = Array.isArray(slot.alternatives) ? slot.alternatives : [];
      });
    }
  }

  goBackToTenders(): void {
    this.router.navigate(['/list']);
  }

  /**
 * 📥 Exportation dynamique au format CSV / Excel
 */
exportCsv(): void {
  if (!this.staffingData || !this.staffingData.proposition_equipe) {
    return;
  }

  // 1. Récupération du Score Global de l'Équipe (score_global_equipe)
  let scoreGlobalEquipe = 'N/A';
  
  if (this.staffingData.score_global_equipe !== undefined && this.staffingData.score_global_equipe !== null) {
    scoreGlobalEquipe = `${this.staffingData.score_global_equipe}%`;
  } else {
    // Calcul de secours au cas où la propriété serait absente
    const scores = this.staffingData.proposition_equipe
      .map(s => s.expert_selectionne?.score_global)
      .filter((s): s is number => s !== undefined && s !== null);

    if (scores.length > 0) {
      const avg = Math.round(scores.reduce((a, b) => a + b, 0) / scores.length);
      scoreGlobalEquipe = `${avg}%`;
    }
  }

  // 2. En-tête / Résumé général de l'équipe
  const summaryHeader = [
    `"Score Global de l'Équipe";"${scoreGlobalEquipe}"`,
    '' // Ligne vide de séparation
  ];

  // 3. En-têtes du fichier CSV
  const headers = ['Poste Requis', 'Expert Affecté', 'Score Adéquation'];

  // 4. Transformation des données de l'équipe
  const rows = this.staffingData.proposition_equipe.map((slot) => {
    const expert = slot.expert_selectionne;

    // Titre lisible du poste
    const posteName = slot.poste || 'Poste non spécifié';
    const expertName = expert?.nom_expert || 'Non attribué';
    
    // Vérification explicite pour gérer le cas d'un score égal à 0
    const score = (expert?.score_global !== undefined && expert?.score_global !== null) 
      ? `${expert.score_global}%` 
      : 'N/A';

    // Échappement des guillemets pour éviter de casser le format CSV
    return [
      `"${posteName.replace(/"/g, '""')}"`,
      `"${expertName.replace(/"/g, '""')}"`,
      `"${score}"`
    ].join(';');
  });

  // 5. Assemblage avec le BOM UTF-8 (\uFEFF) + le résumé + les en-têtes + les lignes
  const csvContent = '\uFEFF' + [
    ...summaryHeader,
    headers.join(';'),
    ...rows
  ].join('\n');

  // 6. Déclenchement du téléchargement
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `Staffing_Equipe_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  window.URL.revokeObjectURL(url);
}
  /**
   * 🖨️ Impression / Exportation PDF
   */
  exportPdf(): void {
    this.exportService.exportToPdf();
  }
}