export interface ScoreBreakdown {
  critere: string;
  score_obtenu: number;
  score_maximal: number;
  explication: string;
}

export interface JustificationIa {
  resume: string;
  points_forts: string[];
  points_faibles: string[];
  criteres_non_satisfaits?: string[];
}

export interface ExpertNode {
  expert_id: number;
  nom_expert: string;
  score_global: number;
  confidence: number;
  score_breakdown: ScoreBreakdown[];
  justification_ia: JustificationIa;
  selectionne_par_defaut: boolean;
  selectionne_par_user?: boolean;
}

export interface AlternativeCandidate {
  expert_id: number;
  nom_expert: string;
  score_global: number;
  confidence: number;
  score_breakdown: ScoreBreakdown[];
  selectionne_par_defaut: boolean;
  justification_ia?: JustificationIa;
}

export interface StaffingSlot {
  poste: string;
  required_profile_id: number;
  expert_selectionne: ExpertNode;
  alternatives: AlternativeCandidate[];
  showAlternatives?: boolean; 
}

export interface ConflictArbitration {
  expert_id: number;
  nom_expert: string;
  poste_concerne: string;
  raison: string;
}

export interface StaffingGenerationResponse {
  status: string;
  score_global_equipe: number;
  conflits_arbitres: ConflictArbitration[];
  proposition_equipe: StaffingSlot[];
}

export interface ExpertSelectionResponse {
  status: string;
  message: string;
  expert_id: number;
  required_profile_id: number;
  score_global: number;
  justification_ia: JustificationIa;
}