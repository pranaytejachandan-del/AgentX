import {
  ProcurementListResponse,
  ProcurementDetailResponse,
  GuardrailResult,
} from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  const response = await fetch(url, { ...options, headers });

  if (!response.ok) {
    let errorDetail = `API Request failed with status ${response.status}`;
    try {
      const errJson = await response.json();
      if (errJson.detail) {
        errorDetail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // ignore json parse error
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

export async function checkBackendHealth(): Promise<{ status: string }> {
  try {
    return await request<{ status: string }>('/api/health');
  } catch {
    return { status: 'offline' };
  }
}

export async function fetchProcurementRequests(
  statusFilter?: string,
  limit = 50,
  offset = 0
): Promise<ProcurementListResponse> {
  const query = new URLSearchParams();
  if (statusFilter && statusFilter !== 'ALL') {
    query.append('status_filter', statusFilter);
  }
  query.append('limit', limit.toString());
  query.append('offset', offset.toString());

  return request<ProcurementListResponse>(`/api/procurement?${query.toString()}`);
}

export async function fetchProcurementRequestDetail(id: number): Promise<ProcurementDetailResponse> {
  return request<ProcurementDetailResponse>(`/api/procurement/${id}`);
}

export async function parseProcurementPrompt(prompt: string, userId: number = 1) {
  return request('/api/procurement/parse', {
    method: 'POST',
    body: JSON.stringify({ prompt, user_id: userId }),
  });
}

export async function orchestrateProcurement(prompt: string, userId: number = 1): Promise<ProcurementDetailResponse> {
  return request<ProcurementDetailResponse>('/api/procurement/orchestrate', {
    method: 'POST',
    body: JSON.stringify({ prompt, user_id: userId }),
  });
}

export async function executePolicyCheck(requestId: number): Promise<GuardrailResult> {
  return request<GuardrailResult>(`/api/procurement/${requestId}/policy-check`, {
    method: 'POST',
  });
}

export async function approveProcurement(requestId: number, notes?: string) {
  return request(`/api/procurement/${requestId}/approve`, {
    method: 'POST',
    body: JSON.stringify({ notes: notes || 'Approved by Procurement Manager via Dashboard' }),
  });
}

export async function rejectProcurement(requestId: number, notes?: string) {
  return request(`/api/procurement/${requestId}/reject`, {
    method: 'POST',
    body: JSON.stringify({ notes: notes || 'Rejected by Procurement Manager via Dashboard' }),
  });
}

export async function createPaymentLink(requestId: number) {
  return request<{
    payment_link_id: string;
    short_url: string;
    status: string;
    amount: number;
  }>(`/api/procurement/${requestId}/payment`, {
    method: 'POST',
  });
}
