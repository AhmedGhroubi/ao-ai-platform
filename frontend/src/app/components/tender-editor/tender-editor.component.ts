import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { TenderService } from '../../services/tender.service';

@Component({
  selector: 'app-tender-editor',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './tender-editor.component.html',
  styleUrls: ['./tender-editor.component.css']
})
export class TenderEditorComponent implements OnInit {
  tenderId!: number;
  tenderData: any = null;
  isSaving: boolean = false;
  showSuccessMessage: boolean = false;
  
  // 🟢 Gestion dynamique du périmètre géographique (liste d'inputs)
  regionsList: string[] = [];
  
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
    if (this.tenderId) {
      this.loadTender();
    }
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

        // Assignation des données à notre variable
        this.extractedData = rawData || { contexte_mission_globale: "", profils: [] };
        
        // Synchronisation de la liste des régions depuis la base de données
        this.syncScopeGeographiqueFromData();
        
        // Sécurité sur la structure des profils
        if (!this.extractedData.profils) {
          this.extractedData.profils = [];
        } else {
          this.extractedData.profils.forEach((p: any) => p.isEditing = false);
        }
      },
      error: (err) => console.error('Erreur lors du chargement de l’appel d’offres', err)
    });
  }

  // --- GESTION DU PÉRIMÈTRE GÉOGRAPHIQUE ---

  // ⚠️ Important pour *ngFor : évite de perdre le focus pendant la saisie dans un tableau de chaînes
  trackByIndex(index: number, item: any): number {
    return index;
  }

  private syncScopeGeographiqueFromData(): void {
    // Lecture prioritaire à la racine (regions_ciblees) puis fallback sur extracted_data
    const values = this.tenderData?.regions_ciblees || this.extractedData?.scope_geographique;
    
    if (Array.isArray(values)) {
      this.regionsList = values
        .filter((v: any) => v && typeof v === 'string')
        .map((v: string) => v.trim());
      return;
    }

    if (typeof values === 'string' && values.trim()) {
      // Si d'anciennes données étaient sous forme de chaîne de caractères
      this.regionsList = values
        .split(/[,;\n]+/)
        .map((v: string) => v.trim())
        .filter(Boolean);
      return;
    }

    this.regionsList = [];
  }

  addRegion(): void {
    this.regionsList.push('');
  }

  removeRegion(index: number): void {
    this.regionsList.splice(index, 1);
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

  // --- SAUVEGARDE EN BASE DE DONNÉES ---

  onValidate(): void {
    this.isSaving = true;
    this.showSuccessMessage = false;

    // 1. Copie propre des données
    const cleanedData = JSON.parse(JSON.stringify(this.extractedData));
    if (cleanedData.profils) {
      cleanedData.profils.forEach((p: any) => delete p.isEditing);
    }
    delete cleanedData.scope_geographique;

    // 2. Nettoyage + SUPPRESSION DES DOUBLONS (insensible à la casse)
    const seen = new Set<string>();
    const cleanedRegions: string[] = [];

    for (const r of this.regionsList) {
      const trimmed = r ? r.trim() : '';
      if (trimmed) {
        const lower = trimmed.toLowerCase();
        // Si le pays n'a pas encore été ajouté, on l'ajoute
        if (!seen.has(lower)) {
          seen.add(lower);
          cleanedRegions.push(trimmed); // On conserve la casse originale (ex: "Ghana")
        }
      }
    }

    // On remet la liste nettoyée dans le composant
    this.regionsList = [...cleanedRegions];

    // 3. Emballage du payload
    const payload = {
      extracted_data: cleanedData,
      regions_ciblees: cleanedRegions
    };

    // 4. Envoi via le service Angular
    this.tenderService.updateTenderData(this.tenderId, payload).subscribe({
      next: () => {
        this.isSaving = false;
        this.showSuccessMessage = true;
        setTimeout(() => this.showSuccessMessage = false, 4000);
      },
      error: (err) => {
        console.error('Erreur lors de la validation', err);
        this.isSaving = false;
        alert("❌ Une erreur est survenue lors de l'enregistrement.");
      }
    });
  }

  // Vérifie si la région à un index donné est déjà présente ailleurs dans la liste
  isDuplicateRegion(index: number): boolean {
    const currentValue = this.regionsList[index]?.trim().toLowerCase();
    if (!currentValue) return false;

    return this.regionsList.some((region, i) => {
      return i !== index && region?.trim().toLowerCase() === currentValue;
    });
  }
}