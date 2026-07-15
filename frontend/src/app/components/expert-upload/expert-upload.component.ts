import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ExpertService } from '../../services/expert.service';
import { Expert } from '../../models/expert.model';
import { interval, Subscription } from 'rxjs';
import { switchMap, takeWhile } from 'rxjs/operators';
import { ActivatedRoute, Router, RouterModule } from '@angular/router'; // 👈 Ajout de Router ici

@Component({
  selector: 'app-expert-upload',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './expert-upload.component.html',
  styleUrls: ['./expert-upload.component.css']
})
export class ExpertUploadComponent implements OnInit, OnDestroy {
  selectedFile: File | null = null;
  currentExpert: Expert | null = null;
  isUploading = false;
  private pollingSubscription: Subscription | null = null;

  // 👈 Injection de "router" dans le constructeur
  constructor(
    private expertService: ExpertService, 
    private route: ActivatedRoute,
    private router: Router 
  ) {}

  ngOnInit(): void {
    // 🔄 Si on arrive sur cette page avec un ID (?id=1), on charge directement l'expert
    this.route.queryParams.subscribe(params => {
      if (params['id']) {
        this.expertService.getExpertById(+params['id']).subscribe(expert => {
          this.currentExpert = expert;
        });
      }
    });
  }

  onFileSelected(event: any): void {
    if (event.target.files && event.target.files.length > 0) {
      this.selectedFile = event.target.files[0];
    }
  }

  onUpload(): void {
    if (!this.selectedFile) return;

    this.isUploading = true;
    this.currentExpert = null;
    this.stopPolling();

    this.expertService.uploadCv(this.selectedFile).subscribe({
      next: (expert) => {
        this.currentExpert = expert;
        this.isUploading = false;
        
        // 🚀 REDIRECTION IMMÉDIATE VERS LA LISTE DES EXPERTS / CVS
        // Remplace '/experts' par le chemin exact de ton composant de liste (ex: '/cv-list')
        this.router.navigate(['/experts']); 

        // Note : Le polling local ci-dessous va s'arrêter automatiquement 
        // car le composant va être détruit par la redirection (via ngOnDestroy).
        if (expert.status !== 'Analysé' && expert.status !== 'Erreur') {
          this.startPolling(expert.id);
        }
      },
      error: (err) => {
        console.error(err);
        this.isUploading = false;
        alert("Erreur lors de l'envoi du fichier.");
      }
    });
  }

  startPolling(expertId: number): void {
    this.pollingSubscription = interval(3000)
      .pipe(
        switchMap(() => this.expertService.getExpertById(expertId)),
        takeWhile(expert => expert.status !== 'Analysé' && expert.status !== 'Erreur', true)
      )
      .subscribe({
        next: (expert) => {
          this.currentExpert = expert;
          if (expert.status === 'Analysé' || expert.status === 'Erreur') {
            this.stopPolling();
          }
        },
        error: (err) => {
          console.error("Erreur de polling:", err);
          this.stopPolling();
        }
      });
  }

  stopPolling(): void {
    if (this.pollingSubscription) {
      this.pollingSubscription.unsubscribe();
      this.pollingSubscription = null;
    }
  }

  ngOnDestroy(): void {
    this.stopPolling();
  }
}