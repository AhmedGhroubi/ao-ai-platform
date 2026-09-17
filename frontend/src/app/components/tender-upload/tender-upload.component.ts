import { Component } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router'; 
import { TenderService } from '../../services/tender.service';

@Component({
  selector: 'app-tender-upload',
  standalone: true,
  imports: [ReactiveFormsModule, CommonModule, RouterModule], 
  templateUrl: './tender-upload.component.html',
  styleUrls: ['./tender-upload.component.css']
})
export class TenderUploadComponent {
  uploadForm: FormGroup;
  selectedFile: File | null = null;

  constructor(
    private fb: FormBuilder, 
    private tenderService: TenderService,
    private router: Router 
  ) {
    this.uploadForm = this.fb.group({
      title: [''],
      pages: [''] 
    });
  }

  onFileSelected(event: any) {
    this.selectedFile = event.target.files[0];
  }

  clearFile() {
    this.selectedFile = null;
  }

  onCancel() {
    this.uploadForm.reset();
    this.clearFile();
  }

  onSubmit() {
    if (!this.selectedFile) {
      alert("Veuillez d'abord sélectionner un fichier PDF.");
      return;
    }

    const formData = new FormData();
    
    // 1. Récupération des valeurs depuis ton FormGroup
    const titleValue = this.uploadForm.get('title')?.value;
    const pagesValue = this.uploadForm.get('pages')?.value;

    if (titleValue) {
      formData.append('title', titleValue);
    }
    
    if (pagesValue) {
      formData.append('pages', pagesValue);
    }
    
    // 2. Ajout du fichier PDF
    formData.append('file', this.selectedFile);

    // 3. Envoi au backend et redirection
    this.tenderService.uploadTender(formData).subscribe({
      next: (res) => {
        // Redirection immédiate dès que FastAPI répond
        this.router.navigate(['/list']); 
      },
      error: (err) => {
        console.error("Erreur lors de l'upload", err);
        alert("Une erreur est survenue lors de l'envoi du fichier.");
      }
    });
  }
}