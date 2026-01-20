export interface Product {
  original_order: string;
  parent_folder: string;
  machine_equipment_number: string;
  equipment_number: string;
  equipment_alias: string;
  machine_description: string;
  group_responsibility: string;
  plant: string;
  initiator: string;
  cspl_line_number: string;
  part_description: string;
  part_manufacturer: string;
  manufacturer_part_number: string;
  qty_on_machine: string;
  suggested_supplier: string;
  supplier_part_number: string;
  gore_stock_number: string;
  is_part_likely_to_fail: string;
  will_failures_stop_machine: string;
  stocking_decision: string;
  min_qty_to_stock: string;
  part_preplacement_line_number: string;
  notes: string;
  part_number_ai_modified: string;
  manufacturer: string;
  ai_status?: string | null;
  notes_by_ai?: string | null;
  ai_confidence?: string | null;
  ai_confidence_confirmed?: string | null;
  will_notes: string;
  nejat_notes: string;
  kc_notes: string;
  initial_email_communication: string;
  follow_up_email_communication_date: string;
  ricky_notes: string;
  stephanie_notes: string;
  pit_notes: string;
  row_index?: number;
  // Replacement Information
  recommended_replacement?: string;
  replacement_manufacturer?: string;
  replacement_price?: number | null;
  replacement_currency?: string | null;
  replacement_source_type?: string;
  replacement_source_url?: string;
  replacement_notes?: string;
  replacement_confidence?: string;
}

export interface AnalysisResult {
  manufacturer: string; // AI returns 'manufacturer' but we map from 'manufacture'
  part_number: string;
  ai_status: "Active" | "🔴 Obsolete" | "Review";
  notes_by_ai: string;
  ai_confidence: "High" | "Medium" | "Low";
}

export interface ParticipatingAssociate {
  name: string;
  id: string;
}

export interface GeneralInfo {
  document_no?: string;
  revision_no?: string;
  title?: string;
  equipment_description?: string;
  eam_equipment_id?: string;
  alias?: string;
  plant?: string;
  group_responsible?: string;
  participating_associates?: {
    initiator?: ParticipatingAssociate;
    pe?: ParticipatingAssociate;
    d_and_a?: ParticipatingAssociate;
    maintenance_tech?: ParticipatingAssociate;
    indirect_procurement?: ParticipatingAssociate;
  };
}

export interface ExcelUploadResponse {
  success: boolean;
  products: Product[];
  total?: number;
  total_products?: number;
  general_info?: GeneralInfo;
  error?: string;
}

export interface AnalyzeResponse {
  success: boolean;
  results: AnalysisResult[];
  total_analyzed: number;
  error?: string;
}

export interface StreamEvent {
  type: 'start' | 'chunk_start' | 'chunk_complete' | 'progress' | 'result' | 'complete' | 'error';
  message?: string;
  chunk?: number;
  total_chunks?: number;
  products_in_chunk?: number;
  total_products?: number;
  data?: {
    results: AnalysisResult[];
  };
  results?: AnalysisResult[];
  total_analyzed?: number;
}

