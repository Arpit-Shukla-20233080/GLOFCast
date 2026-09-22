"""
GLOFCast Backend — Pydantic Response Schemas
=============================================
Strongly-typed contracts between the FastAPI backend and the Next.js frontend.
Every response is serializable JSON with explicit field descriptions for
OpenAPI documentation generation.
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


# ─── Risk classification enum ────────────────────────────────────────────────
class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ─── Time-series data point (shared by CryoFormer & ThermoSeq) ─────────────────
class TimeSeriesPoint(BaseModel):
    date: str = Field(..., description="ISO date string YYYY-MM-DD")
    value: float = Field(..., description="Measurement value (m/yr for velocity, °C for temperature)")


# ─── Glacial Lake record from the CSV inventory ──────────────────────────────
class GlacialLakeRecord(BaseModel):
    id: str = Field(..., description="Unique lake identifier from GL_ID")
    name: str = Field(..., description="Human-readable lake name or GL_ID fallback")
    lat: float
    lng: float
    elevation: float = Field(..., description="Lake elevation in meters (GL_Elev)")
    area: float = Field(..., description="Lake area in m² (GL_Area)")
    area_km2: float = Field(..., description="Lake area in km²")
    glof_weight: float = Field(..., description="Morphological GLOF risk weight from dataset")
    has_glof: bool = Field(..., description="Whether this lake has historical GLOF record")
    region: str = Field(..., description="Sub-region identifier")
    lake_type: str = Field(..., description="Lake type classification")
    year: int = Field(..., description="Year of observation")
    distance: float = Field(0.0, description="Distance metric from dataset")
    perimeter: float = Field(0.0, description="Lake perimeter in meters")
    risk_score: float = Field(0.0, description="Computed HydroFusion fusion score (0.0-1.0)")
    risk_level: RiskLevel = Field(RiskLevel.LOW, description="Categorical risk level")


# ─── Sub-model score breakdown ────────────────────────────────────────────────
class SubModelScores(BaseModel):
    cryoformer: float = Field(..., description="Kinematic anomaly score (0.0-1.0)")
    thermoseq: float = Field(..., description="Thermal anomaly score (0.0-1.0)")
    morphological: float = Field(..., description="Lake morphology baseline risk (0.0-1.0)")
    fusion: float = Field(..., description="Final HydroFusion fusion score (0.0-1.0)")


# ─── Full telemetry response for a single lake ───────────────────────────────
class FullTelemetryResponse(BaseModel):
    lake: GlacialLakeRecord
    velocity_series: list[TimeSeriesPoint] = Field(
        ..., description="CryoFormer ice velocity time series (30 days)"
    )
    temperature_series: list[TimeSeriesPoint] = Field(
        ..., description="ThermoSeq surface temperature time series (30 days)"
    )
    risk_scores: SubModelScores
    alert_triggered: bool = Field(
        False, description="True if fusion score >= 0.85 (hydrodynamic routing trigger)"
    )
    alert_payload: Optional[dict] = Field(
        None, description="r.avaflow-formatted payload if alert_triggered"
    )


# ─── Velocity prediction response ────────────────────────────────────────────
class VelocityPredictionResponse(BaseModel):
    lat: float
    lng: float
    predictions: list[TimeSeriesPoint]
    model: str = Field("CryoFormer-5.5M", description="Model identifier")
    status: str = Field("success")


# ─── Temperature prediction response ─────────────────────────────────────────
class TemperaturePredictionResponse(BaseModel):
    lat: float
    lng: float
    predictions: list[TimeSeriesPoint]
    model: str = Field("ThermoSeq-LSTM", description="Model identifier")
    status: str = Field("success")


# ─── Historical GLOF validation event ────────────────────────────────────────
class HistoricalGLOFEvent(BaseModel):
    lake_id: str
    lake_name: str
    event_date: str
    causes: list[str]
    downstream_effects: str
    casualties: Optional[str] = None
    description: str
    velocity_replay: list[TimeSeriesPoint] = Field(
        ..., description="Simulated CryoFormer readings 30 days before event"
    )
    temperature_replay: list[TimeSeriesPoint] = Field(
        ..., description="Simulated ThermoSeq readings 30 days before event"
    )
    would_have_flagged: bool = Field(
        True, description="Whether GLOFCast would have triggered an alert"
    )
    peak_risk_score: float = Field(
        ..., description="Maximum fusion score in the 30-day window"
    )


# ─── Live API Trigger Signals ─────────────────────────────────────────────────
class LiveTriggers(BaseModel):
    """Real-time environmental signals from Open-Meteo and USGS APIs."""
    meteo_temp_c: Optional[float] = Field(None, description="Current 2m temperature from Open-Meteo (°C)")
    meteo_above_freezing: bool = Field(False, description="True if current temp > 0°C")
    meteo_api_ok: bool = Field(False, description="Whether the Open-Meteo API call succeeded")
    usgs_quake_count: int = Field(0, description="Number of recent earthquakes within 200km")
    usgs_max_magnitude: Optional[float] = Field(None, description="Maximum earthquake magnitude")
    usgs_nearest_km: Optional[float] = Field(None, description="Distance to nearest quake in km")
    usgs_seismic_flag: bool = Field(False, description="True if any M >= 3.0 quake nearby")
    usgs_api_ok: bool = Field(False, description="Whether the USGS API call succeeded")
    delta_meteo: float = Field(0.0, description="Risk adjustment from temperature (+0.0 to +0.08)")
    delta_seismic: float = Field(0.0, description="Risk adjustment from seismicity (+0.0 to +0.10)")


class EnvironmentalSnapshot(BaseModel):
    """Summary of current environmental conditions for UI display."""
    current_temp_c: Optional[float] = None
    recent_quake_count: int = 0
    max_quake_magnitude: Optional[float] = None


# ─── Enhanced Telemetry Response (with live triggers) ─────────────────────────
class TelemetryResponse(BaseModel):
    """Response from /api/lake/{id}/telemetry — includes live environmental triggers."""
    lake: GlacialLakeRecord
    velocity_series: list[TimeSeriesPoint] = Field(
        ..., description="CryoFormer ice velocity time series"
    )
    temperature_series: list[TimeSeriesPoint] = Field(
        ..., description="ThermoSeq surface temperature time series"
    )
    risk_scores: SubModelScores
    live_triggers: LiveTriggers
    environmental: EnvironmentalSnapshot
    r_base: float = Field(..., description="Base fusion score before live adjustments")
    r_adjusted: float = Field(..., description="Final composite score with live adjustments")
    alert_triggered: bool = Field(
        False, description="True if composite score >= 0.85"
    )
    alert_payload: Optional[dict] = Field(
        None, description="r.avaflow-formatted payload if alert_triggered"
    )


# ─── API Health check ────────────────────────────────────────────────────────
class HealthResponse(BaseModel):
    status: str = "ok"
    cryoformer_loaded: bool = False
    thermoseq_loaded: bool = False
    lakes_loaded: int = 0
    version: str = "2.0.0"
