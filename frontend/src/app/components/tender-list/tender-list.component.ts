import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { TenderService } from '../../services/tender.service';
import { Subscription } from 'rxjs/internal/Subscription';
import { switchMap, startWith } from 'rxjs/operators';
import { interval } from 'rxjs/internal/observable/interval';

@Component({
  selector: 'app-tender-list',
  standalone: true,
  imports: [CommonModule, RouterModule], 
  templateUrl: './tender-list.component.html'
})
export class TenderListComponent implements OnInit {
  tenders: any[] = [];
  private pollingSub!: Subscription;

  constructor(private tenderService: TenderService,private router: Router) {}

  ngOnInit(): void {
    this.pollingSub = interval(5000)
      .pipe(
        startWith(0), // S'exécute immédiatement au chargement de la page
        switchMap(() => this.tenderService.getAllTenders()) // Rappelle l'API
      )
      .subscribe({
        next: (data) => {
          this.tenders = data; 
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
      },
      error: (err) => console.error('Erreur lors du chargement des Tenders', err)
    });
  }
  viewDetails(id: number): void {
    // ⚠️ Remplace 'editor' par le vrai nom de la route de ta page d'édition
    this.router.navigate(['/editor', id]); 
  }

  // 🗑️ Fonction pour supprimer
  deleteTender(id: number): void {
    const confirmDelete = confirm("Êtes-vous sûr de vouloir supprimer cet appel d'offres ?");
    
    if (confirmDelete) {
      this.tenderService.deleteTender(id).subscribe({
        next: () => {
          // Succès ! On met à jour la liste affichée SANS recharger la page
          this.tenders = this.tenders.filter(t => t.id !== id);
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
      // 💡 On appelle directement la route de suppression existante
      this.tenderService.deleteTender(id).subscribe({
        next: () => {
          // On le retire instantanément de l'affichage
          this.tenders = this.tenders.filter(t => t.id !== id);
        },
        error: (err) => {
          console.error("Erreur lors de l'annulation et suppression", err);
          alert("❌ Impossible d'annuler/supprimer l'analyse pour le moment.");
        }
      });
    }
  }
}