export interface RecentTender {
  id: number | string;
  tender_id?: number | string;
  reference?: string;
  title?: string;
  client?: string;
  profilesCount?: number;
  status?: 'NO_TEAM' | 'PAUSED' | 'GENERATED' | 'VALIDATED' | string;
  score?: number;
  score_match?: number;
  updatedAt?: string;
  extractedData?: any;
  extracted_data?: any;
}

export interface DashboardKpi {
  totalExperts: number;
  totalTenders: number;
  generatedTeams: number;
  avgMatchScore: number;
}

export interface DashboardResponse {
  kpis: DashboardKpi;
  recent_tenders: RecentTender[];
}