export interface Product {
  manufacturer: string;
  part_number: string;
  row_index?: number;
  [key: string]: any;
}

export interface AnalysisResult {
  manufacturer: string;
  part_number: string;
  ai_status: "Active" | "🔴 Obsolete" | "Review";
  notes_by_ai: string;
  ai_confidence: "High" | "Medium" | "Low";
}

export interface ExcelUploadResponse {
  success: boolean;
  products: Product[];
  total: number;
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

