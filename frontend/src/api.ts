/**
 * Typed API client for the Document Intake Assistant backend.
 * Components never call fetch directly.
 */

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

// ── Types ────────────────────────────────────────────────────────────────────

export interface FieldSnapshot {
  value: unknown;
  status: 'unknown' | 'unconfirmed' | 'confirmed';
}

export interface StateSnapshot {
  full_name: FieldSnapshot;
  home_address: FieldSnapshot;
  covers_worldwide_assets: FieldSnapshot;
  has_children: FieldSnapshot;
  children: FieldSnapshot;
  executor_name: FieldSnapshot;
  executor_relationship: FieldSnapshot;
  specific_gifts: FieldSnapshot;
  additional_wishes: FieldSnapshot;
}

export interface MessageInfo {
  role: 'user' | 'assistant';
  content: string;
}

export interface SessionResponse {
  id: string;
  state: StateSnapshot;
  document: string;
  missing_fields: string[];
  messages: MessageInfo[];
}

export interface MessageResponse {
  reply: string;
  state: StateSnapshot;
  document: string;
  missing_fields: string[];
  warnings: string[];
}

export interface HealthResponse {
  status: string;
  provider: string;
  configured: boolean;
}

export interface ApiError {
  error: {
    code: string;
    message: string;
  };
}

// ── Helpers ──────────────────────────────────────────────────────────────────

class ApiClientError extends Error {
  code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  let resp: Response;
  try {
    resp = await fetch(`${API_BASE}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });
  } catch (err) {
    throw new ApiClientError(
      'CONNECTION_ERROR',
      'Cannot connect to the server. Is the backend running?'
    );
  }

  if (!resp.ok) {
    let body: ApiError | null = null;
    try {
      body = await resp.json();
    } catch {
      // ignore parse error
    }
    const detail = body?.error ?? (resp.status === 404 ? body : null);
    if (detail && typeof detail === 'object' && 'code' in detail) {
      throw new ApiClientError(
        (detail as { code: string }).code,
        (detail as { message: string }).message
      );
    }
    throw new ApiClientError(
      'HTTP_ERROR',
      `Server error: ${resp.status} ${resp.statusText}`
    );
  }

  return resp.json();
}

// ── API Functions ────────────────────────────────────────────────────────────

export async function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/api/health');
}

export async function createSession(): Promise<SessionResponse> {
  return request<SessionResponse>('/api/sessions', { method: 'POST' });
}

export async function getSession(id: string): Promise<SessionResponse> {
  return request<SessionResponse>(`/api/sessions/${id}`);
}

export async function sendMessage(
  sessionId: string,
  message: string
): Promise<MessageResponse> {
  return request<MessageResponse>(`/api/sessions/${sessionId}/messages`, {
    method: 'POST',
    body: JSON.stringify({ message }),
  });
}

export async function editField(
  sessionId: string,
  field: string,
  value: unknown
): Promise<{
  state: StateSnapshot;
  document: string;
  missing_fields: string[];
  warnings: string[];
}> {
  return request(`/api/sessions/${sessionId}/state`, {
    method: 'PATCH',
    body: JSON.stringify({ field, value }),
  });
}

export async function resetSession(sessionId: string): Promise<SessionResponse> {
  return request<SessionResponse>(`/api/sessions/${sessionId}/reset`, {
    method: 'POST',
  });
}

export { ApiClientError };
