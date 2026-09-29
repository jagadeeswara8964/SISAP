/** Shared API types for SISAP (mirrors the FastAPI schemas). */

export type RecommendationType =
  | "Primary"
  | "Testing"
  | "Safety"
  | "Reference"
  | "Installation"
  | "Terminology"
  | "Related";

export type GapSeverity = "Critical" | "High" | "Medium" | "Low";

export interface RequirementObject {
  product: string;
  category: string;
  intended_use: string;
  materials: string[];
  technical_requirements: string[];
  performance_requirements: string[];
  safety_requirements: string[];
  testing_requirements: string[];
  installation_requirements: string[];
  certification_requirements: string[];
  extraction_method?: string;
}

export interface ValidationInfo {
  standard_id: string;
  status: string;
  version: string;
  amendments: string[];
  superseded_by: string[];
  certification: string;
  checks: string[];
  validation_source: string;
}

export interface ScoreBreakdown {
  semantic_similarity: number;
  requirement_coverage: number;
  product_match: number;
  application_match: number;
  category_match: number;
  weights: Record<string, number>;
}

export interface Recommendation {
  standard_id: string;
  standard_number: string;
  title: string;
  category: string;
  type: RecommendationType;
  score: number;
  status: string;
  score_breakdown?: ScoreBreakdown;
  explanation: string[];
  matched_requirements: string[];
  missing_requirements: string[];
  related_standards: string[];
  validation?: ValidationInfo;
  scope?: string;
  version?: string;
  amendments?: string[];
  certification?: string;
  source_url?: string;
  relationship_path?: string;
  materials?: string[];
  applications?: string[];
}

export interface RecommendationSummary {
  total: number;
  primary: number;
  testing: number;
  safety: number;
  reference: number;
  installation: number;
  terminology: number;
  related: number;
  high_relevance: number;
  potential_gaps: number;
}

export interface Gap {
  gap_type: string;
  severity: GapSeverity;
  description: string;
  suggested_action: string;
  related_standards: string[];
}

export interface RecommendationResponse {
  document_id: string;
  product: string;
  category: string;
  summary: RecommendationSummary;
  recommendations: Recommendation[];
  gaps: Gap[];
  sections: SectionInfo[];
  extraction_method: string;
  generated_at: string;
  review_note: string;
}

export interface UploadResponse {
  document_id: string;
  filename: string;
  page_count: number;
  char_count: number;
  is_scanned: boolean;
  extraction_status: string;
  message: string;
}

export interface SectionInfo {
  key: string;
  title: string;
  characters: number;
}

export interface ExtractResponse {
  document_id: string;
  requirements: RequirementObject;
  extraction_method: string;
  text_available: boolean;
  sections: SectionInfo[];
}

export interface DocumentInfo {
  id: string;
  filename: string;
  original_filename: string;
  page_count: number;
  char_count: number;
  is_scanned: boolean;
  extraction_status: string;
  source_type: string;
  uploaded_at: string;
  requirements?: RequirementObject | null;
  requirements_extracted: boolean;
  text_preview: string;
  message?: string;
}

export interface StandardSummary {
  id: string;
  standard_number: string;
  title: string;
  category: string;
  version: string;
  status: string;
  standard_types: string[];
}

export interface StandardsPage {
  total: number;
  page: number;
  page_size: number;
  standards: StandardSummary[];
}

export interface Standard extends StandardSummary {
  scope: string;
  certification: string;
  source: string;
  source_url: string;
  product_types: string[];
  materials: string[];
  applications: string[];
  requirements: string[];
  testing: string[];
  safety: string[];
  installation: string[];
  amendments: string[];
  related_standards: string[];
  referenced_standards: string[];
  superseded_by: string[];
  bis_verified: boolean;
  relationships?: { source: string; target: string; relationship_type: string }[];
}

export interface GraphNode {
  id: string;
  label: string;
  title: string;
  node_type: string;
  relationship: string;
  version: string;
  status: string;
  score: number | null;
  is_root: boolean;
}

export interface GraphEdge {
  source: string;
  target: string;
  relationship: string;
}

export interface GraphResponse {
  root: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface GapsResponse {
  document_id: string;
  total: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  gaps: Gap[];
  review_note: string;
}

export interface ReportResponse {
  document_id: string;
  report_id: string;
  filename: string;
  download_url: string;
  generated_at: string;
  sections: string[];
}

export interface RecentAnalysis {
  document_id: string;
  filename: string;
  product: string;
  standards: number;
  gaps: number;
  date: string;
  status: string;
}

export interface DashboardStats {
  documents_analyzed: number;
  standards_recommended: number;
  potential_gaps_found: number;
  validated_references: number;
  standards_in_database: number;
  categories: Record<string, number>;
  confidence: Record<string, number>;
  recent_analyses: RecentAnalysis[];
}

export interface HealthInfo {
  status: string;
  demo_mode: boolean;
  embedding_backend: string;
  embedding_model: string;
  standards_loaded: number;
  faiss_vectors: number;
  version: string;
  settings: {
    app_name: string;
    version: string;
    environment: string;
    demo_mode: boolean;
    embedding_model: string;
    embedding_backend: string;
    max_upload_mb: number;
    llm_configured: boolean;
  };
}

export interface DemoTender {
  filename: string;
  text: string;
  available_files: string[];
}
