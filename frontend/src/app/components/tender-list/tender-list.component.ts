import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { TenderService } from '../../services/tender.service';
import { StaffingService } from '../../services/staffing.service';
import { Subscription } from 'rxjs';
import { switchMap, startWith } from 'rxjs/operators';
import { interval } from 'rxjs';

@Component({
  selector: 'app-tender-list',
  standalone: true,
  imports: [CommonModule, RouterModule], 
  templateUrl: './tender-list.component.html',
  styleUrls: ['./tender-list.component.css']
})
export class TenderListComponent implements OnInit, OnDestroy {
  tenders: any[] = [];
  staffingStates: Record<number, boolean> = {};
  private pollingSub!: Subscription;

  constructor(
    private tenderService: TenderService,
    private staffingService: StaffingService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.pollingSub = interval(5000)
      .pipe(
        startWith(0),
        switchMap(() => this.tenderService.getAllTenders())
      )
      .subscribe({
        next: (data) => {
          this.tenders = data;
          this.refreshStaffingStates(this.tenders);
          console.log("Mes Tenders reçus du backend :", data);
        },
        error: (err) => console.error('Erreur lors du chargement des Tenders', err)
      });
  }

  ngOnDestroy(): void {
    if (this.pollingSub) {
      this.pollingSub.unsubscribe();
    }
  }

  loadTenders(): void {
    this.tenderService.getAllTenders().subscribe({
      next: (data) => {
        this.tenders = data;
        this.refreshStaffingStates(this.tenders);
      },
      error: (err) => console.error('Erreur lors du chargement des Tenders', err)
    });
  }

  private refreshStaffingStates(tenders: any[]): void {
    tenders.forEach((tender) => {
      // 🛠️ Récupération sécurisée de l'ID (correction de tender.fid -> tenderId)
      const tenderId = tender?.id ?? tender?.tender_id;

      if (!tenderId || tenderId === 'undefined') {
        return;
      }

      this.staffingService.getSavedTeam(tenderId).subscribe({
        next: (response) => {
          if (response) {
            this.staffingStates[tenderId] = !!response.has_saved_team;
          }
        },
        error: () => {
          this.staffingStates[tenderId] = false;
        }
      });
    });
  }

  hasGeneratedTeam(tender: any): boolean {
    const tenderId = tender?.id ?? tender?.tender_id;
    return !!this.staffingStates[tenderId];
  }

  viewDetails(id: number): void {
    this.router.navigate(['/editor', id]); 
  }

  deleteTender(id: number): void {
    const confirmDelete = confirm("Êtes-vous sûr de vouloir supprimer cet appel d'offres ?");
    if (confirmDelete) {
      this.tenderService.deleteTender(id).subscribe({
        next: () => {
          this.tenders = this.tenders.filter(t => (t.id ?? t.tender_id) !== id);
        },
        error: (err) => {
          console.error("Erreur lors de la suppression", err);
          alert("❌ Impossible de supprimer cet appel d'offres.");
        }
      });
    }
  }

  cancelAnalysis(id: number): void {
    const confirmCancel = confirm("Êtes-vous sûr de vouloir annuler l'analyse et supprimer cet appel d'offres de la liste ?");
    if (confirmCancel) {
      this.tenderService.deleteTender(id).subscribe({
        next: () => {
          this.tenders = this.tenders.filter(t => (t.id ?? t.tender_id) !== id);
        },
        error: (err) => {
          console.error("Erreur lors de l'annulation et suppression", err);
          alert("❌ Impossible d'annuler/supprimer l'analyse pour le moment.");
        }
      });
    }
  }
}