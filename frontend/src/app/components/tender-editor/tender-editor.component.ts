import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { TenderService } from '../../services/tender.service';

@Component({
  selector: 'app-tender-editor',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './tender-editor.component.html'
})
export class TenderEditorComponent implements OnInit {
  tenderId!: number;
  tenderData: any = null;
  isSaving: boolean = false;
  showSuccessMessage: boolean = false;
  
  // Initialisation avec la structure exacte reçue de l'IA
  extractedData: any = {
    contexte_mission_globale: "",
    profils: []
  }; 

  constructor(
    private route: ActivatedRoute,
    private tenderService: TenderService
  ) {}

  ngOnInit(): void {
    this.tenderId = Number(this.route.snapshot.paramMap.get('id'));
    this.loadTender();
  }

  loadTender(): void {
    this.tenderService.getTenderById(this.tenderId).subscribe({
      next: (res) => {
        this.tenderData = res;
        
        // On récupère les données brutes
        let rawData: any = (res as any).extracted_data ?? res;

        if (rawData && (rawData as any).extracted_data) {
          rawData = (rawData as any).extracted_data;
        }

        // On assigne enfin les bonnes données à notre variable
        this.extractedData = rawData || { contexte_mission_globale: "", profils: [] };
        
        // Sécurité et initialisation du mode lecture
        if (!this.extractedData.profils) {
          this.extractedData.profils = [];
        } else {
          this.extractedData.profils.forEach((p: any) => p.isEditing = false);
        }
      },
      error: (err) => console.error('Erreur lors du chargement', err)
    });
  }

  // --- GESTION DES PROFILS ---
  addProfile(): void {
    this.extractedData.profils.push({
      titre_du_poste: 'Nouveau Profil',
      quantite_demandee: 1,
      criteres_evaluation: [],
      observations: ''
    });
  }

  removeProfile(index: number): void {
    this.extractedData.profils.splice(index, 1);
  }

  // --- GESTION DES CRITÈRES ---
  addCriterion(profileIndex: number): void {
    if (!this.extractedData.profils[profileIndex].criteres_evaluation) {
      this.extractedData.profils[profileIndex].criteres_evaluation = [];
    }
    
    // Structure d'un nouveau critère selon ton modèle
    this.extractedData.profils[profileIndex].criteres_evaluation.push({
      type_critere: 'experience',
      libelle_exigence: 'Nouvelle exigence...',
      points_maximum: 0,
      regle_notation: ''
    });
  }

  removeCriterion(profileIndex: number, criterionIndex: number): void {
    this.extractedData.profils[profileIndex].criteres_evaluation.splice(criterionIndex, 1);
  }

  // --- SAUVEGARDE EN BASE ---
  onSave(): void {
    this.tenderService.updateTenderData(this.tenderId, this.extractedData).subscribe({
      next: () => alert('✅ Modifications enregistrées avec succès !'),
      error: (err) => console.error('Erreur lors de la sauvegarde', err)
    });
  }
  onValidate(): void {
    // 1. On lance l'animation de chargement
    this.isSaving = true;
    this.showSuccessMessage = false;

    // 2. On fait une copie propre des données et on enlève la variable d'édition
    const cleanedData = JSON.parse(JSON.stringify(this.extractedData));
    if (cleanedData.profils) {
      cleanedData.profils.forEach((p: any) => delete p.isEditing);
    }

    // 🚨 3. LE CORRECTIF : On emballe les données dans "extracted_data"
    const payload = {
      extracted_data: cleanedData
    };

    // 4. On envoie le "payload" bien emballé au backend
    this.tenderService.updateTenderData(this.tenderId, payload).subscribe({
      next: () => {
        // Succès ! Le backend a accepté le JSON
        this.isSaving = false;
        this.showSuccessMessage = true;
        
        // Fait disparaître le message de succès après 4 secondes
        setTimeout(() => {
          this.showSuccessMessage = false;
        }, 4000);
      },
      error: (err) => {
        console.error('Erreur lors de la validation', err);
        this.isSaving = false;
        alert("❌ Une erreur est survenue lors de l'enregistrement. Vérifie la console.");
      }
    });
  }
}