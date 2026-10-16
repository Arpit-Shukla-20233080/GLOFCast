export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

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
  hasGlof?: boolean;
  areaKm2?: number;
  glofWeight?: number;
  lakeType?: string;
  perimeter?: number;
}

export interface TimeSeriesPoint {
  date: string;
  value: number;
}

export const GLACIAL_LAKES: GlacialLake[] = [
  {
    id: 'south_lhonak',
    name: 'South Lhonak Lake',
    region: 'North Sikkim',
    country: 'India',
    lat: 27.9167,
    lng: 88.2167,
    elevation: 5200,
    area: 1.68,
    riskScore: 0.94,
    riskLevel: 'critical',
    lastUpdated: '2026-10-01T18:30:00Z',
    modelStatus: { cryoformer: true, thermoseq: true, hydrofusion: true },
    hasGlof: true,
  },
  {
    id: 'l-01',
    name: 'Shishper Glacier Lake',
    region: 'Hunza Valley',
    country: 'Pakistan',
    lat: 36.345,
    lng: 74.8045,
    elevation: 4200,
    area: 0.24,
    riskScore: 0.87,
    riskLevel: 'critical',
    lastUpdated: '2026-10-01T18:30:00Z',
    modelStatus: { cryoformer: true, thermoseq: true, hydrofusion: true },
    hasGlof: true,
  },
  {
    id: 'l-02',
    name: 'Attabad Lake',
    region: 'Hunza Valley',
    country: 'Pakistan',
    lat: 36.31,
    lng: 74.84,
    elevation: 2500,
    area: 21.0,
    riskScore: 0.42,
    riskLevel: 'medium',
    lastUpdated: '2026-10-01T18:30:00Z',
    modelStatus: { cryoformer: true, thermoseq: true, hydrofusion: true }
  },
  {
    id: 'l-03',
    name: 'Imja Tsho',
    region: 'Khumbu',
    country: 'Nepal',
    lat: 27.90,
    lng: 86.93,
    elevation: 5010,
    area: 1.28,
    riskScore: 0.73,
    riskLevel: 'high',
    lastUpdated: '2026-10-01T18:30:00Z',
    modelStatus: { cryoformer: true, thermoseq: true, hydrofusion: true }
  },
  {
    id: 'l-04',
    name: 'Tsho Rolpa',
    region: 'Rolwaling Valley',
    country: 'Nepal',
    lat: 27.86,
    lng: 86.47,
    elevation: 4580,
    area: 1.54,
    riskScore: 0.61,
    riskLevel: 'medium',
    lastUpdated: '2026-10-01T18:30:00Z',
    modelStatus: { cryoformer: true, thermoseq: true, hydrofusion: true }
  },
  {
    id: 'l-05',
    name: 'Palcacocha',
    region: 'Cordillera Blanca',
    country: 'Peru',
    lat: -9.40,
    lng: -77.38,
    elevation: 4560,
    area: 0.51,
    riskScore: 0.78,
    riskLevel: 'high',
    lastUpdated: '2026-10-01T18:30:00Z',
    modelStatus: { cryoformer: true, thermoseq: true, hydrofusion: true }
  },
  {
    id: 'l-06',
    name: 'Jökulsárlón',
    region: 'Vatnajökull',
    country: 'Iceland',
    lat: 64.08,
    lng: -16.18,
    elevation: 0,
    area: 18.0,
    riskScore: 0.15,
    riskLevel: 'low',
    lastUpdated: '2026-10-01T18:30:00Z',
    modelStatus: { cryoformer: true, thermoseq: true, hydrofusion: true }
  }
];

export function getLakeById(id: string): GlacialLake | undefined {
  return GLACIAL_LAKES.find(lake => lake.id === id);
}

// Pseudo-random function for deterministic noise based on index
function seededRandom(seed: number): number {
  const x = Math.sin(seed++) * 10000;
  return x - Math.floor(x);
}

export function generateVelocityData(days: number): TimeSeriesPoint[] {
  const data: TimeSeriesPoint[] = [];
  const now = new Date();
  const baseVelocity = 82;
  const seasonalVariation = 15;
  const noiseLevel = 5;

  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(now.getTime() - i * 24 * 60 * 60 * 1000);
    const dayOfYear = Math.floor((d.getTime() - new Date(d.getFullYear(), 0, 0).getTime()) / 1000 / 60 / 60 / 24);
    
    // Sine wave over 365 days
    const sineValue = Math.sin((dayOfYear / 365) * 2 * Math.PI) * seasonalVariation;
    // Deterministic noise based on index
    const noise = (seededRandom(i * 100) * 2 - 1) * noiseLevel;
    
    const value = baseVelocity + sineValue + noise;
    
    data.push({
      date: d.toISOString().split('T')[0],
      value: Number(value.toFixed(2))
    });
  }

  return data;
}

export function generateTemperatureData(days: number): TimeSeriesPoint[] {
  const data: TimeSeriesPoint[] = [];
  const now = new Date();
  const baseTemp = -3;
  const seasonalVariation = 8;
  const noiseLevel = 2;

  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(now.getTime() - i * 24 * 60 * 60 * 1000);
    const dayOfYear = Math.floor((d.getTime() - new Date(d.getFullYear(), 0, 0).getTime()) / 1000 / 60 / 60 / 24);
    
    // Sine wave over 365 days
    const sineValue = Math.sin(((dayOfYear - 100) / 365) * 2 * Math.PI) * seasonalVariation;
    const noise = (seededRandom(i * 200 + 42) * 2 - 1) * noiseLevel;
    
    const value = baseTemp + sineValue + noise;
    
    data.push({
      date: d.toISOString().split('T')[0],
      value: Number(value.toFixed(2))
    });
  }

  return data;
}

/**
 * Create a dynamic GlacialLake from any lat/lng coordinates.
 * Generates realistic mock data based on the location's properties.
 */
export function createDynamicLake(lat: number, lng: number): GlacialLake {
  // Generate a deterministic risk score based on coordinates
  const seed = Math.abs(lat * 1000 + lng * 500);
  const riskScore = Number((seededRandom(seed) * 0.6 + 0.2).toFixed(2)); // 0.20 - 0.80 range

  // Estimate elevation based on latitude (rough heuristic)
  const absLat = Math.abs(lat);
  let estimatedElevation: number;
  if (absLat > 60) estimatedElevation = Math.floor(500 + seededRandom(seed + 1) * 1500);
  else if (absLat > 25 && absLat < 45) estimatedElevation = Math.floor(2000 + seededRandom(seed + 2) * 3500);
  else estimatedElevation = Math.floor(1000 + seededRandom(seed + 3) * 2500);

  // Determine risk level
  let riskLevel: RiskLevel;
  if (riskScore >= 0.7) riskLevel = 'critical';
  else if (riskScore >= 0.5) riskLevel = 'high';
  else if (riskScore >= 0.3) riskLevel = 'medium';
  else riskLevel = 'low';

  // Estimate area
  const area = Number((seededRandom(seed + 4) * 5 + 0.1).toFixed(2));

  return {
    id: `dynamic-${lat.toFixed(4)}-${lng.toFixed(4)}`,
    name: `Location ${lat.toFixed(3)}°, ${lng.toFixed(3)}°`,
    region: `${lat > 0 ? 'N' : 'S'}${absLat.toFixed(0)}° ${lng > 0 ? 'E' : 'W'}${Math.abs(lng).toFixed(0)}°`,
    country: 'Custom Pin',
    lat,
    lng,
    elevation: estimatedElevation,
    area,
    riskScore,
    riskLevel,
    lastUpdated: new Date().toISOString(),
    modelStatus: { cryoformer: true, thermoseq: true, hydrofusion: true },
  };
}
