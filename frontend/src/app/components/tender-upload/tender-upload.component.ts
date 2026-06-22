import { Component } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router'; 
import { TenderService } from '../../services/tender.service';

@Component({
  selector: 'app-tender-upload',
  standalone: true,
  imports: [ReactiveFormsModule, CommonModule, RouterModule], 
  templateUrl: './tender-upload.component.html'
})
export class TenderUploadComponent {
  uploadForm: FormGroup;
  selectedFile: File | null = null;

  constructor(private fb: FormBuilder, private tenderService: TenderService) {
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
    const formData = new FormData();
    formData.append('title', this.uploadForm.get('title')?.value || '');
    formData.append('pages', this.uploadForm.get('pages')?.value || '');
    
    if (this.selectedFile) {
      formData.append('file', this.selectedFile);
    }

    this.tenderService.uploadTender(formData).subscribe({
      next: (res) => {
        alert('Upload réussi !');
        this.onCancel();
      },
      error: (err) => console.error('Erreur lors de l\'upload', err)
    });
  }
}