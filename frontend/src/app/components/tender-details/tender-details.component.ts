import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common'; 
import { RouterModule, ActivatedRoute } from '@angular/router'; 
import { TenderService, TenderResponse } from '../../services/tender.service';

@Component({
  selector: 'app-tender-details',
  standalone: true, // Requis pour Angular moderne sans module
  imports: [CommonModule, RouterModule], 
  templateUrl: './tender-details.component.html',
  styleUrls: ['./tender-details.component.css']
})
export class TenderDetailsComponent implements OnInit {
  // Remplacement de 'any' par notre type fort multi-agents
  tender: TenderResponse | null = null;
  isLoading: boolean = true;
  hasError: boolean = false;

  constructor(
    private route: ActivatedRoute,
    private tenderService: TenderService
  ) {}

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    
    if (id) {
      this.tenderService.getTenderById(+id).subscribe({
        next: (data) => {
          // On utilise une variable temporaire 'any' pour exécuter tes filtres 
          // de sécurité sans que TypeScript ne lève d'erreur de compilation.
          let cleanData: any = data;

          // 🛡️ SÉCURITÉ 1 : Si la base de données renvoie un texte au lieu d'un objet JSON, on le transforme.
          if (typeof cleanData.extracted_data === 'string') {
            try {
              cleanData.extracted_data = JSON.parse(cleanData.extracted_data);
            } catch (e) {
              console.error("Erreur de parsing JSON", e);
            }
          }

          // 🛡️ SÉCURITÉ 2 : On corrige la "double imbrication" (extracted_data dans extracted_data)
          if (cleanData.extracted_data && cleanData.extracted_data.extracted_data) {
            cleanData.extracted_data = cleanData.extracted_data.extracted_data;
          }

          // Affectation finale aux données typées
          this.tender = cleanData as TenderResponse;

          console.log("🟢 Données nettoyées prêtes pour le HTML (Multi-Agents) :", this.tender);
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
}