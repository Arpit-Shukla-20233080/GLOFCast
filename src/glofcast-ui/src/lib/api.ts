/**
 * GLOFCast Frontend — API Client Layer
 * ======================================
 * Replaces all mock data in mock-data.ts with live API calls to the FastAPI backend.
 *
 * Architecture: Thin fetch wrapper with TypeScript types matching the Pydantic schemas.
 * Falls back to local mock data if the backend is unreachable (graceful degradation).
 */

// ─── Configuration ──────────────────────────────────────────────────────────

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ─── Type Definitions (mirror backend Pydantic schemas) ─────────────────────

export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

export interface TimeSeriesPoint {
  date: string;
  value: number;
}

export interface ModelStatus {
  cryoformer: boolean;
  thermoseq: boolean;
  hydrofusion: boolean;
}

export interface GlacialLake {
  id: string;
  name: string;
  region: string;
  country: string;
  lat: number;
  lng: number;
  elevation: number;
  area: number;
  riskScore: number;
  riskLevel: RiskLevel;
  lastUpdated: string;
  modelStatus: ModelStatus;
  // Extended fields from backend
  areaKm2?: number;
  glofWeight?: number;
  hasGlof?: boolean;
  lakeType?: string;
  perimeter?: number;
}

export interface SubModelScores {
  cryoformer: number;
  thermoseq: number;
  morphological: number;
  fusion: number;
}

export interface FullTelemetryResponse {
  lake: {
    id: string;
    name: string;
    lat: number;
    lng: number;
    elevation: number;
    area: number;
    area_km2: number;
    glof_weight: number;
    has_glof: boolean;
    region: string;
    lake_type: string;
    year: number;
    distance: number;
    perimeter: number;
    risk_score: number;
    risk_level: RiskLevel;
  };
  velocity_series: TimeSeriesPoint[];
  temperature_series: TimeSeriesPoint[];
  risk_scores: SubModelScores;
  alert_triggered: boolean;
  alert_payload: Record<string, unknown> | null;
}

export interface HistoricalGLOFEvent {
  lake_id: string;
  lake_name: string;
  event_date: string;
  causes: string[];
  downstream_effects: string;
  casualties: string | null;
  description: string;
  velocity_replay: TimeSeriesPoint[];
  temperature_replay: TimeSeriesPoint[];
  would_have_flagged: boolean;
  peak_risk_score: number;
}

export interface HealthResponse {
  status: string;
  cryoformer_loaded: boolean;
  thermoseq_loaded: boolean;
  lakes_loaded: number;
  version: string;
}

// ─── API fetch helper with timeout and error handling ────────────────────────

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000); // 15s timeout

  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status} ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error('API request timed out');
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

// ─── Backend → Frontend Type Transformer ────────────────────────────────────

function transformLakeRecord(record: Record<string, unknown>): GlacialLake {
  const riskLevel = String(record.risk_level || record.riskLevel || 'low') as RiskLevel;
  return {
    id: String(record.id || ''),
    name: String(record.name || ''),
    region: String(record.region || ''),
    country: String(record.lake_type || record.country || 'Unknown'),
    lat: Number(record.lat || 0),
    lng: Number(record.lng || 0),
    elevation: Number(record.elevation || 0),
    area: Number(record.area_km2 || record.area || 0),
    riskScore: Number(record.risk_score || record.riskScore || 0),
    riskLevel,
    lastUpdated: new Date().toISOString(),
    modelStatus: { cryoformer: true, thermoseq: true, hydrofusion: true },
    areaKm2: Number(record.area_km2 || 0),
    glofWeight: Number(record.glof_weight || record.glofWeight || 0),
    hasGlof: Boolean(record.has_glof || record.hasGlof || false),
    lakeType: String(record.lake_type || record.lakeType || ''),
    perimeter: Number(record.perimeter || 0),
  };
}

// ─── Exported API Functions ─────────────────────────────────────────────────

/**
 * Check backend health and model loading status.
 */
export async function checkHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>('/api/health');
}

/**
 * Fetch the global lake inventory from the CSV database.
 * Returns transformed lakes ready for UI rendering.
 */
export async function fetchLakes(params?: {
  limit?: number;
  offset?: number;
  minRisk?: number;
  region?: string;
  hasGlof?: boolean;
}): Promise<{ lakes: GlacialLake[]; total: number }> {
  const searchParams = new URLSearchParams();
  if (params?.limit) searchParams.set('limit', String(params.limit));
  if (params?.offset) searchParams.set('offset', String(params.offset));
  if (params?.minRisk) searchParams.set('min_risk', String(params.minRisk));
  if (params?.region) searchParams.set('region', params.region);
  if (params?.hasGlof !== undefined) searchParams.set('has_glof', String(params.hasGlof));

  const query = searchParams.toString();
  const data = await apiFetch<{ lakes: Record<string, unknown>[]; total: number }>(
    `/api/lakes${query ? `?${query}` : ''}`
  );

  return {
    lakes: data.lakes.map(transformLakeRecord),
    total: data.total,
  };
}

/**
 * Search lakes by name, ID, or region.
 */
export async function searchLakes(query: string): Promise<GlacialLake[]> {
  const data = await apiFetch<{ results: Record<string, unknown>[] }>(
    `/api/lakes/search?q=${encodeURIComponent(query)}`
  );
  return data.results.map(transformLakeRecord);
}

/**
 * Get CryoFormer velocity predictions for a coordinate.
 */
export async function fetchVelocityPrediction(
  lat: number, lng: number, days: number = 30
): Promise<TimeSeriesPoint[]> {
  const data = await apiFetch<{ predictions: TimeSeriesPoint[] }>(
    `/api/predict/velocity?lat=${lat}&lng=${lng}&days=${days}`
  );
  return data.predictions;
}

/**
 * Get ThermoSeq temperature predictions for a coordinate.
 */
export async function fetchTemperaturePrediction(
  lat: number, lng: number, days: number = 30
): Promise<TimeSeriesPoint[]> {
  const data = await apiFetch<{ predictions: TimeSeriesPoint[] }>(
    `/api/predict/temperature?lat=${lat}&lng=${lng}&days=${days}`
  );
  return data.predictions;
}

/**
 * Get full telemetry for a known lake (by ID from CSV inventory).
 */
export async function fetchLakeTelemetry(
  lakeId: string, days: number = 30
): Promise<FullTelemetryResponse> {
  return apiFetch<FullTelemetryResponse>(
    `/api/lake/${encodeURIComponent(lakeId)}/full-telemetry?days=${days}`
  );
}

/**
 * Get full telemetry for an arbitrary coordinate (custom map click).
 */
export async function fetchCoordinateTelemetry(
  lat: number, lng: number, days: number = 30
): Promise<FullTelemetryResponse> {
  return apiFetch<FullTelemetryResponse>(
    `/api/coordinate/full-telemetry?lat=${lat}&lng=${lng}&days=${days}`
  );
}

/**
 * Fetch all historical GLOF events available for validation.
 */
export async function fetchHistoricalEvents(): Promise<{
  total: number;
  events: Array<{
    lake_id: string;
    lake_name: string;
    event_date: string;
    causes: string[];
    lat: number;
    lng: number;
  }>;
}> {
  return apiFetch('/api/historical/events');
}

/**
 * Get the full validation replay for a historical GLOF event.
 */
export async function fetchHistoricalReplay(lakeId: string): Promise<HistoricalGLOFEvent> {
  return apiFetch<HistoricalGLOFEvent>(`/api/historical/replay/${encodeURIComponent(lakeId)}`);
}

// ─── Backend availability check with fallback ────────────────────────────────

let _backendAvailable: boolean | null = null;

/**
 * Check if the backend is reachable. Caches the result to avoid
 * repeated failed requests during a session.
 */
export async function isBackendAvailable(): Promise<boolean> {
  if (_backendAvailable !== null) return _backendAvailable;

  try {
    await checkHealth();
    _backendAvailable = true;
  } catch {
    _backendAvailable = false;
  }
  return _backendAvailable;
}

/**
 * Reset the backend availability cache (e.g., on retry).
 */
export function resetBackendCache(): void {
  _backendAvailable = null;
}
