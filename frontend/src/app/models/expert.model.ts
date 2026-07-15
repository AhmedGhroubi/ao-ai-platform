export interface ProjetMission {
  nom_projet: string;
  client_ou_bailleur: string;
  annee: string;
  pays: string;
  poste_occupe: string;
}

export interface ExperienceProfessionnelle {
  periode: string;
  employeur: string;
  poste: string;
  pays: string;
  resume_activites: string[];
}

export interface Etude {
  annee: string;
  diplome: string;
  institution: string;
}

export interface ExtractedData {
  nom_expert: string;
  date_naissance: string;
  nationalite: string;
  langues: string[];
  etudes: Etude[];
  certifications: string[];
  titre_poste_principal: string;
  annees_experience_total: number;
  competences_techniques: string[];
  pays_d_intervention: string[];
  experiences_professionnelles: ExperienceProfessionnelle[];
  projets_et_missions: ProjetMission[];
}

export interface Expert {
  id: number;
  slug_unique: string | null;
  nom_expert: string | null;
  filename: string;
  status: 'En attente' | "En cours d'analyse" | 'Analysé' | 'Erreur'|'Quota journalier dépassé (En pause)' ;
  extracted_data: ExtractedData | null;
}