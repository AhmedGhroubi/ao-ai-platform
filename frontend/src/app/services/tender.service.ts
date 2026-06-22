import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class TenderService {
  // Garde cette URL de base
  private apiUrl = 'http://127.0.0.1:8000'; 

  constructor(private http: HttpClient) {}

  // 1. Uploader un nouveau PDF 
  uploadTender(formData: FormData): Observable<any> {
    return this.http.post(`${this.apiUrl}/api/tenders/upload/`, formData);
  }

  // 2. Récupérer un appel d'offres par son ID
  getTenderById(id: number): Observable<any> {
    return this.http.get(`${this.apiUrl}/api/tenders/${id}`);
  }

  // 3. Récupérer la liste des Tenders 
  getAllTenders(): Observable<any> {
    return this.http.get(`${this.apiUrl}/api/tenders/`); 
  }

  // 4. Sauvegarder les modifications 
  updateTenderData(tenderId: number, data: any): Observable<any> {
    return this.http.put(`${this.apiUrl}/api/tenders/${tenderId}/save-extracted-data`, data);
  }
  
  // 5. Supprimer
  deleteTender(id: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/api/tenders/${id}`);
  }
}