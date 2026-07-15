import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { ExpertService } from '../../services/expert.service';
import { Expert } from '../../models/expert.model';

@Component({
  selector: 'app-expert-list',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './expert-list.component.html',
  styleUrls: ['./expert-list.component.css']
})
export class ExpertListComponent implements OnInit {
  experts: Expert[] = [];
  filteredExperts: Expert[] = [];
  searchTerm: string = '';
  uploadingExpertId: number | null = null;
  private apiUrl = '/api/experts'; // Adjust as needed

  // Stats calculées pour le bandeau supérieur
  totalCount = 0;
  analyzedCount = 0;
  processingCount = 0;

  constructor(private expertService: ExpertService, private router: Router, private http: HttpClient) {}

  ngOnInit(): void {
    this.loadExperts();
  }

  loadExperts(): void {
    this.expertService.getExperts().subscribe({
      next: (data) => {
        this.experts = data;
        this.filteredExperts = data;
        this.calculateStats();
      },
      error: (err) => console.error("Erreur lors de la récupération des experts", err)
    });
  }

  calculateStats(): void {
    this.totalCount = this.experts.length;
    this.analyzedCount = this.experts.filter(e => e.status === 'Analysé').length;
    this.processingCount = this.experts.filter(e => e.status === 'En cours d\'analyse' || e.status === 'En attente').length;
  }

  filterExperts(): void {
    const term = this.searchTerm.toLowerCase().trim();
    if (!term) {
      this.filteredExperts = this.experts;
    } else {
      this.filteredExperts = this.experts.filter(e => 
        (e.nom_expert && e.nom_expert.toLowerCase().includes(term)) ||
        e.filename.toLowerCase().includes(term) ||
        (e.extracted_data?.titre_poste_principal && e.extracted_data.titre_poste_principal.toLowerCase().includes(term))
      );
    }
  }

  viewDetails(id: number): void {
    this.router.navigate(['/experts/details', id]);
  }

  onEdit(expert: Expert): void {
    this.router.navigate(['/experts/edit', expert.id]);
  }

  onDelete(id: number): void {
    const confirmDelete = confirm("Êtes-vous sûr de vouloir supprimer cet expert ?");
    if (confirmDelete) {
      this.expertService.deleteExpert(id).subscribe({
        next: () => {
          this.experts = this.experts.filter(e => e.id !== id);
          this.filterExperts();
          this.calculateStats();
        },
        error: (err) => alert("Erreur lors de la suppression.")
      });
    }
  }
  annulerAnalyse(id: number): void {
    if (confirm('Voulez-vous vraiment annuler l\'analyse en cours ? Cela supprimera ce fichier de la liste.')) {
      this.executerSuppression(id);
    }
  }
  private executerSuppression(id: number): void {
    this.expertService.deleteExpert(id).subscribe({
      next: () => {
        // Mise à jour de l'affichage
        this.experts = this.experts.filter(e => e.id !== id);
      },
      error: (err) => {
        console.error('Erreur lors de la suppression', err);
        alert('Une erreur est survenue.');
      }
    });
  }
  reprendreAnalyse(expertId: number): void {
    const expert = this.experts.find(e => e.id === expertId);
    
    if (expert) {
      // 1. Mise à jour optimiste de l'UI
      expert.status = "En cours d'analyse";
      this.calculateStats(); 
    }

    // 2. Appel propre au service
    this.expertService.startAnalysis(expertId).subscribe({
      next: (res) => {
        console.log('Analyse reprise avec succès', res);
        // Si ton backend renvoie l'expert mis à jour, tu peux rafraîchir ici
        // this.loadExperts();
      },
      error: (err) => {
        console.error('Erreur lors de la reprise de l\'analyse', err);
        if (expert) {
          // Si l'API échoue, on remet le statut d'erreur
          expert.status = "Erreur"; 
          this.calculateStats();
        }
      }
    });
  }
  onFileSelected(event: any, expert: any): void {
    const file: File = event.target.files[0];
    
    if (!file) return;

    // Vérification de l'extension
    if (!file.name.endsWith('.docx')) {
      alert("Seuls les fichiers Word (.docx) sont acceptés.");
      event.target.value = ''; // Réinitialise l'input
      return;
    }

    // Active l'état de chargement sur le bouton cliqué (Affiche "⏳ Envoi...")
    this.uploadingExpertId = expert.id;

    const formData = new FormData();
    formData.append('file', file);

    // Appel à la nouvelle route PUT de ton backend
    this.http.put(`${this.apiUrl}/${expert.id}/reanalyze`, formData).subscribe({
      next: (updatedExpert: any) => {
        // Arrête l'état de chargement
        this.uploadingExpertId = null;
        
        // Met à jour la ligne dans le tableau immédiatement
        const index = this.experts.findIndex(e => e.id === expert.id);
        if (index !== -1) {
          this.experts[index] = updatedExpert;
        }

        // Réinitialise l'input file pour permettre un nouvel upload futur
        event.target.value = ''; 
      },
      error: (err) => {
        this.uploadingExpertId = null;
        console.error("Erreur lors de la mise à jour du CV :", err);
        alert("Une erreur est survenue lors de l'envoi du document.");
        event.target.value = ''; 
      }
    });
  }
}