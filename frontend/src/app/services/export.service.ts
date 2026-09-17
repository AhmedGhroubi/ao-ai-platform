import { Injectable } from '@angular/core';

export interface TeamMemberExport {
  profil: string;
  expertName: string;
  scoreMatch: string | number;
  experience?: string | number;
  email?: string;
}

@Injectable({
  providedIn: 'root'
})
export class ExportService {

  /**
   * Exporte l'équipe au format CSV (compatible Excel avec encodage UTF-8)
   */
  exportTeamToCsv(teamMembers: TeamMemberExport[], tenderTitle: string = 'Equipe'): void {
    if (!teamMembers || teamMembers.length === 0) {
      alert("Aucune donnée d'équipe à exporter.");
      return;
    }

    // En-têtes du fichier CSV
    const headers = ['Profil Requis', 'Expert Affecté', 'Score d\'Adéquation (%)'];

    // Lignes de données
    const rows = teamMembers.map(m => [
      `"${m.profil || ''}"`,
      `"${m.expertName || 'Non assigné'}"`,
      `"${m.scoreMatch ? m.scoreMatch + '%' : '-'}"`,
      `"${m.experience ? m.experience + ' ans' : '-'}"`,
      `"${m.email || '-'}"`
    ]);

    // UTF-8 BOM (\uFEFF) pour garantir le bon affichage des accents dans Excel
    const csvContent = '\uFEFF' + [headers.join(';'), ...rows.map(r => r.join(';'))].join('\n');

    // Création du lien de téléchargement
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    
    // Formatage du nom de fichier
    const formattedTitle = tenderTitle.toLowerCase().replace(/[^a-z0-9]/g, '_');
    const fileName = `Equipe_${formattedTitle}_${new Date().toISOString().slice(0, 10)}.csv`;

    link.setAttribute('href', url);
    link.setAttribute('download', fileName);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  /**
   * Lance l'impression / sauvegarde en PDF
   */
  exportToPdf(): void {
    window.print();
  }
}