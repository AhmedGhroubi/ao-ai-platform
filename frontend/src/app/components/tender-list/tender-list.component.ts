import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { TenderService } from '../../services/tender.service';

@Component({
  selector: 'app-tender-list',
  standalone: true,
  imports: [CommonModule, RouterModule], 
  templateUrl: './tender-list.component.html'
})
export class TenderListComponent implements OnInit {
  tenders: any[] = [];

  constructor(private tenderService: TenderService,private router: Router) {}

  ngOnInit(): void {
    this.loadTenders();
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
    // On demande confirmation avant de supprimer (bonne pratique UX)
    const confirmDelete = confirm("Êtes-vous sûr de vouloir supprimer cet appel d'offres ?");
    
    if (confirmDelete) {
      this.tenderService.deleteTender(id).subscribe({
        next: () => {
          // Succès ! On met à jour la liste affichée SANS recharger la page
          // Cela va automatiquement réorganiser notre numérotation dynamique
          this.tenders = this.tenders.filter(t => t.id !== id);
        },
        error: (err) => {
          console.error("Erreur lors de la suppression", err);
          alert("❌ Impossible de supprimer cet appel d'offres.");
        }
      });
    }
  }
}