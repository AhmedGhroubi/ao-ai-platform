import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { CommonModule } from '@angular/common';
import { Expert } from '../../models/expert.model'; 
import { ExpertService } from '../../services/expert.service';

@Component({
  selector: 'app-expert-details',
  standalone: true,
  imports: [CommonModule, RouterLink], // 👈 On ajoute CommonModule ici
  templateUrl: './expert-details.component.html',
  styleUrls: ['./expert-details.component.css']
})
export class ExpertDetailsComponent implements OnInit {
  
  expert: Expert | null = null;
  isLoading: boolean = true;
  hasError: boolean = false;

  constructor(
    private route: ActivatedRoute,
    private expertService: ExpertService 
  ) {}

  ngOnInit(): void {
    const expertId = this.route.snapshot.paramMap.get('id');
    if (expertId) {
      this.loadExpertDetails(expertId);
    } else {
      this.isLoading = false;
      this.hasError = true;
    }
  }

  loadExpertDetails(id: string): void {
    this.isLoading = true;
    this.hasError = false;

    this.expertService.getExpertById(+id).subscribe({
      next: (data) => {
        this.expert = data;
        this.isLoading = false;
      },
      error: (err) => {
        console.error("Erreur lors de la récupération de l'expert :", err);
        this.isLoading = false;
        this.hasError = true;
      }
    });
  }
}