import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Expert } from '../models/expert.model';

@Injectable({
  providedIn: 'root'
})
export class ExpertService {
  private apiUrl = 'http://127.0.0.1:8000/api/experts';

  constructor(private http: HttpClient) {}

  getExperts(): Observable<Expert[]> {
    return this.http.get<Expert[]>(`${this.apiUrl}/`);
  }

  getExpertById(id: number): Observable<Expert> {
    return this.http.get<Expert>(`${this.apiUrl}/${id}`);
  }

  uploadCv(file: File): Observable<Expert> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<Expert>(`${this.apiUrl}/upload`, formData);
  }

  updateExpert(id: number, data: any): Observable<Expert> {
    return this.http.put<Expert>(`${`${this.apiUrl}/${id}`}`, data);

  }

  deleteExpert(id: number): Observable<any> {
    return this.http.delete(`${`${this.apiUrl}/${id}`}`);
  }

  startAnalysis(id: number): Observable<any> {
    return this.http.post(`${this.apiUrl}/${id}/analyze`, {});
  }
  reanalyzeSection(expertId: number, sectionName: string): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/${expertId}/reanalyze-section/${sectionName}`, {});
  }

}