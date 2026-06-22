import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common'; 
import { RouterModule, ActivatedRoute } from '@angular/router'; 
import { TenderService } from '../../services/tender.service';
@Component({
  selector: 'app-tender-details',
  standalone: true, // Requis pour Angular moderne sans module
  imports: [CommonModule, RouterModule], 
  templateUrl: './tender-details.component.html',
  styleUrls: ['./tender-details.component.css'] // (Optionnel, tu peux supprimer cette ligne si le fichier css n'existe pas)
})
export class TenderDetailsComponent implements OnInit {
  tender: any;
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
          this.tender = data;

          // 🛡️ SÉCURITÉ 1 : Si la base de données renvoie un texte au lieu d'un objet JSON, on le transforme.
          if (typeof this.tender.extracted_data === 'string') {
            try {
              this.tender.extracted_data = JSON.parse(this.tender.extracted_data);
            } catch (e) {
              console.error("Erreur de parsing JSON", e);
            }
          }

          // 🛡️ SÉCURITÉ 2 : On corrige la "double imbrication" (extracted_data dans extracted_data)
          if (this.tender.extracted_data && this.tender.extracted_data.extracted_data) {
            this.tender.extracted_data = this.tender.extracted_data.extracted_data;
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
}