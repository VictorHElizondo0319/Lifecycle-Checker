import { FieldConfig } from '@/components/FieldSelector';
import { Product, AnalysisResult, ExcelUploadResponse, AnalyzeResponse } from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';

export async function uploadExcelFile(file: File): Promise<ExcelUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE_URL}/api/excel/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to upload file');
  }

  return response.json();
}

export async function analyzeProducts(
  products: Product[],
  stream: boolean = false
): Promise<AnalyzeResponse> {
  if (stream) {
    throw new Error('Streaming analysis should use analyzeProductsStream');
  }

  const response = await fetch(`${API_BASE_URL}/api/analyze`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      products,
      stream: false,
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to analyze products');
  }

  return response.json();
}

export function analyzeProductsStream(
  products: Product[],
  onEvent: (event: any) => void,
  onError?: (error: Error) => void
): () => void {
  const abortController = new AbortController();

  fetch(`${API_BASE_URL}/api/analyze`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      products,
      stream: true,
    }),
    signal: abortController.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        throw new Error('Failed to start analysis');
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('No response body');
      }

      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              onEvent(data);
            } catch (e) {
              console.error('Failed to parse SSE data:', e);
            }
          }
        }
      }
    })
    .catch((error) => {
      if (error.name !== 'AbortError' && onError) {
        onError(error);
      }
    });

  return () => {
    abortController.abort();
  };
}

export function findReplacementsStream(
  products: Product[],
  onEvent: (event: any) => void,
  onError?: (error: Error) => void
): () => void {
  const abortController = new AbortController();
  fetch(`${API_BASE_URL}/api/find_replacements`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      products,
    }),
    signal: abortController.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        throw new Error('Failed to start replacement finding');
      }
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('No response body');
      }
      
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              onEvent(data);
            }
            catch (e) {
              console.error('Failed to parse SSE data:', e);
            }
          }
        }
      }
    }
    )
    .catch((error) => {
      if (error.name !== 'AbortError' && onError) {
        onError(error);
      }
    });
  return () => {
    abortController.abort();
  }
}
export async function exportExcelFile({cols, products}: {cols: FieldConfig[], products: any[]}): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/excel/export`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      cols,
      products,
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Failed to export Excel file' }));
    throw new Error(error.error || 'Failed to export Excel file');
  }

  // Get the filename from Content-Disposition header or use default
  const contentDisposition = response.headers.get('Content-Disposition');
  let filename = 'export.xlsx';
  if (contentDisposition) {
    const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
    if (filenameMatch && filenameMatch[1]) {
      filename = filenameMatch[1].replace(/['"]/g, '');
    }
  }

  // Convert response to blob and trigger download
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  
  // Cleanup
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
}

export interface SaveDataRequest {
  general_info?: {
    eam_equipment_id?: string;
    equipment_description?: string;
    alias?: string;
    plant?: string;
    group_responsible?: string;
    participating_associates?: {
      initiator?: { name?: string };
    };
  };
  products: any[];
  create_log?: boolean;
}

export interface SaveDataResponse {
  success: boolean;
  machine_id?: number | null;
  parts_saved: number;
  parts_updated: number;
  machine_parts_linked: number;
  log_id?: number | null;
  error?: string;
}

export async function saveData(data: SaveDataRequest): Promise<SaveDataResponse> {
  const response = await fetch(`${API_BASE_URL}/api/save`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Failed to save data' }));
    throw new Error(error.error || 'Failed to save data');
  }

  return response.json();
}

export interface Part {
  id: number;
  part_manufacturer: string;
  manufacturer_part_number: string;
  part_description?: string;
  ai_status?: string;
  machines?: Array<{
    id: number;
    equipment_id: string;
    equipment_alias?: string;
    machine_description?: string;
    plant?: string;
    quantity: number;
  }>;
  [key: string]: any;
}

export interface GetPartsRequest {
  ai_status?: string;
  machine_id?: number;
  search?: string;
  limit?: number;
  offset?: number;
}

export interface GetPartsResponse {
  success: boolean;
  parts: Part[];
  total: number;
  limit: number;
  offset: number;
  filters_applied: {
    ai_status?: string | null;
    machine_id?: number | null;
    search?: string | null;
  };
  error?: string;
}

export interface Machine {
  id: number;
  equipment_id: string;
  equipment_alias?: string;
  machine_description?: string;
  plant?: string;
  group_responsibility?: string;
  parts_count: number;
}

export interface GetMachinesResponse {
  success: boolean;
  machines: Machine[];
  total: number;
  error?: string;
}

export async function getParts(filters?: GetPartsRequest): Promise<GetPartsResponse> {
  const params = new URLSearchParams();
  if (filters?.ai_status) params.append('ai_status', filters.ai_status);
  if (filters?.machine_id) params.append('machine_id', filters.machine_id.toString());
  if (filters?.search) params.append('search', filters.search);
  if (filters?.limit) params.append('limit', filters.limit.toString());
  if (filters?.offset) params.append('offset', filters.offset.toString());

  const response = await fetch(`${API_BASE_URL}/api/parts?${params.toString()}`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Failed to fetch parts' }));
    throw new Error(error.error || 'Failed to fetch parts');
  }

  return response.json();
}

export async function getMachines(): Promise<GetMachinesResponse> {
  const response = await fetch(`${API_BASE_URL}/api/parts/machines`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Failed to fetch machines' }));
    throw new Error(error.error || 'Failed to fetch machines');
  }

  return response.json();
}

export interface UpdatePartsRequest {
  parts: Array<{
    id: number;
    recommended_replacement?: string;
    replacement_manufacturer?: string;
    replacement_price?: number | null;
    replacement_currency?: string | null;
    replacement_source_type?: string;
    replacement_source_url?: string;
    replacement_notes?: string;
    replacement_confidence?: string;
  }>;
}

export interface UpdatePartsResponse {
  success: boolean;
  updated: number;
  errors: string[];
  error?: string;
}

export async function updateParts(data: UpdatePartsRequest): Promise<UpdatePartsResponse> {
  const response = await fetch(`${API_BASE_URL}/api/parts/update`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Failed to update parts' }));
    throw new Error(error.error || 'Failed to update parts');
  }

  return response.json();
}