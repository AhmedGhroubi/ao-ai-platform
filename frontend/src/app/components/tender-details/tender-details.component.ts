import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common'; 
import { RouterModule, ActivatedRoute } from '@angular/router'; 
import { FormsModule } from '@angular/forms'; // Nécessaire pour [(ngModel)]
import { TenderService, TenderResponse } from '../../services/tender.service';

@Component({
  selector: 'app-tender-details',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule], // Ajout de FormsModule
  templateUrl: './tender-details.component.html',
  styleUrls: ['./tender-details.component.css']
})
export class TenderDetailsComponent implements OnInit {
  // Alignement des variables avec votre template HTML
  tender: TenderResponse | null = null;
  extractedData: any = null;
  
  // Variable pour le champ textarea des régions
  scopeGeographiqueText: string = '';
  
  isLoading: boolean = true;
  hasError: boolean = false;
  isSaving: boolean = false;
  showSuccessMessage: boolean = false;

  constructor(
    private route: ActivatedRoute,
    private tenderService: TenderService
  ) {}

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    
    if (id) {
      this.tenderService.getTenderById(+id).subscribe({
        next: (data) => {
          let cleanData: any = data;

          // 🛡️ SÉCURITÉ 1 : Parsing JSON si nécessaire
          if (typeof cleanData.extracted_data === 'string') {
            try {
              cleanData.extracted_data = JSON.parse(cleanData.extracted_data);
            } catch (e) {
              console.error("Erreur de parsing JSON", e);
            }
          }

          // 🛡️ SÉCURITÉ 2 : Correction double imbrication
          if (cleanData.extracted_data && cleanData.extracted_data.extracted_data) {
            cleanData.extracted_data = cleanData.extracted_data.extracted_data;
          }

          // Affectation aux variables utilisées dans le HTML
          this.tender = cleanData as TenderResponse;
          this.extractedData = this.tender.extracted_data;

          // 🌍 CHARGEMENT DES RÉGIONS : Conversion du tableau en texte pour le textarea
          if (this.tender.regions_ciblees && Array.isArray(this.tender.regions_ciblees)) {
            this.scopeGeographiqueText = this.tender.regions_ciblees.join(', ');
          } else {
            this.scopeGeographiqueText = '';
          }

          console.log("🟢 Données nettoyées prêtes pour le HTML :", this.tender);
          this.isLoading = false;
        },
        error: (err) => {
          console.error("🔴 Erreur lors du chargement :", err);
          this.hasError = true;
          this.isLoading = false;
        }
      });
    } else {
      this.hasError = true;
      this.isLoading = false;
    }
  }

  

  // --- Méthodes utilitaires pour la gestion des profils (déjà prévues dans votre HTML) ---

  addProfile(): void {
    this.extractedData.profils.push({
      titre_du_poste: '',
      quantite_demandee: 1,
      observations: '',
      criteres_evaluation: []
    });
  }

  removeProfile(index: number): void {
    this.extractedData.profils.splice(index, 1);
  }

  addCriterion(profileIndex: number): void {
    this.extractedData.profils[profileIndex].criteres_evaluation.push({
      type_critere: '',
      libelle_exigence: '',
      points_maximum: 1,
      regle_notation: ''
    });
  }

  removeCriterion(profileIndex: number, criterionIndex: number): void {
    this.extractedData.profils[profileIndex].criteres_evaluation.splice(criterionIndex, 1);
  }
}