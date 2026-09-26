"""
GLOFCast API Gateway — FastAPI Main Application (Deliverable 2)
=================================================================
Production-grade REST API serving the Next.js frontend.

Enhanced with:
  - /api/lake/{id}/telemetry endpoint (Zero-Training Fusion Formula)
  - Live Open-Meteo temperature API integration
  - Live USGS Earthquake API integration
  - Composite risk score with real-time environmental adjustments

Architecture:
  ┌─────────────────────────────────────────────────────────┐
  │  Next.js Frontend (port 3000)                           │
  │  └─ api.ts → fetch() ──────────────────────┐            │
  └────────────────────────────────────────────┼────────────┘
                                               │
  ┌────────────────────────────────────────────▼────────────┐
  │  FastAPI Gateway (port 8000)                            │
  │  ├─ /api/health          → System status               │
  │  ├─ /api/lakes           → CSV inventory (cached)      │
  │  ├─ /api/lakes/search    → Lake search                 │
  │  ├─ /api/predict/velocity       → CryoFormer inference  │
  │  ├─ /api/predict/temperature    → ThermoSeq inference   │
  │  ├─ /api/lake/{id}/telemetry    → Fusion telemetry     │
  │  ├─ /api/lake/{id}/full-telemetry → Full pipeline      │
  │  ├─ /api/historical/events      → GLOF event database  │
  │  └─ /api/historical/replay/{id} → Validation replay    │
  │                                                        │
  │  Live API Triggers:                                     │
  │  ├─ Open-Meteo → Current temperature > 0°C check       │
  │  └─ USGS Earthquake → Recent tremor detection           │
  └─────────────────────────────────────────────────────────┘
"""

from __future__ import annotations
import os
import logging
import time
import math
from contextlib import asynccontextmanager
from pathlib import Path
from functools import lru_cache
from datetime import datetime, timedelta, timezone

import httpx
import pandas as pd
import numpy as np
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from cachetools import TTLCache

from schemas import (
    GlacialLakeRecord, FullTelemetryResponse, VelocityPredictionResponse,
    TemperaturePredictionResponse, SubModelScores, HealthResponse,
    TimeSeriesPoint, HistoricalGLOFEvent, RiskLevel,
    TelemetryResponse, LiveTriggers, EnvironmentalSnapshot,
)
from model_registry import (
    load_cryoformer, load_thermoseq, is_cryoformer_loaded, is_thermoseq_loaded,
    cryoformer_predict_sequence, thermoseq_predict_sequence,
)
from hydrofusion import compute_fusion_risk
from historical_glof import get_historical_events, get_event_by_lake_id, generate_validation_replay

# ─── Logging Configuration ───────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-20s | %(levelname)-7s | %(message)s",
)
logger = logging.getLogger("glofcast.api")

# ─── Path Configuration ──────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# Support environment variables for Docker deployments with sensible local defaults
MODELS_DIR_ENV = os.environ.get("MODELS_DIR")
if MODELS_DIR_ENV and Path(MODELS_DIR_ENV).exists():
    MODELS_DIR = Path(MODELS_DIR_ENV)
elif (BASE_DIR / "models").exists():
    MODELS_DIR = BASE_DIR / "models"
else:
    MODELS_DIR = Path(__file__).resolve().parent / "models"

CSV_PATH_ENV = os.environ.get("CSV_PATH")
if CSV_PATH_ENV and os.path.exists(CSV_PATH_ENV):
    CSV_PATH = CSV_PATH_ENV
elif (BASE_DIR / "prepared_dataset.csv").exists():
    CSV_PATH = str(BASE_DIR / "prepared_dataset.csv")
else:
    CSV_PATH = str(Path(__file__).resolve().parent / "prepared_dataset.csv")

# Model weight paths
CRYOFORMER_PATH = os.environ.get("CRYOFORMER_PATH", str(MODELS_DIR / "cryoformer-5.5M.pth"))
THERMOSEQ_PATH = os.environ.get("THERMOSEQ_PATH", str(MODELS_DIR / "best_thermoseq_model1.keras"))
THERMOSEQ_SCALER_PATH = os.environ.get("THERMOSEQ_SCALER_PATH", str(MODELS_DIR / "thermoseq_features_scaler.save"))

# ─── In-Memory Cache (TTL = 300s for API data, 3600s for CSV) ────────────────
_prediction_cache = TTLCache(maxsize=256, ttl=300)
_lake_data_cache: dict = {}  # Populated at startup, no TTL needed
_live_api_cache = TTLCache(maxsize=64, ttl=600)  # 10-minute TTL for live triggers


# ──────────────────────────────────────────────────────────────────────────────
# Live API Integration — Open-Meteo & USGS
# ──────────────────────────────────────────────────────────────────────────────

async def fetch_open_meteo_temperature(lat: float, lng: float) -> dict:
    """
    Query the Open-Meteo API for current temperature at the given coordinates.

    Returns:
        dict with keys:
            - current_temp_c: float (current 2m temperature in °C)
            - above_freezing: bool (True if temp > 0°C)
            - api_success: bool
    """
    cache_key = f"meteo_{lat:.2f}_{lng:.2f}"
    if cache_key in _live_api_cache:
        return _live_api_cache[cache_key]

    result = {
        "current_temp_c": None,
        "above_freezing": False,
        "api_success": False,
    }

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": round(lat, 4),
                    "longitude": round(lng, 4),
                    "current_weather": "true",
                    "temperature_unit": "celsius",
                },
            )
            if response.status_code == 200:
                data = response.json()
                current_weather = data.get("current_weather", {})
                temp = current_weather.get("temperature")
                if temp is not None:
                    result["current_temp_c"] = float(temp)
                    result["above_freezing"] = float(temp) > 0.0
                    result["api_success"] = True
                    logger.info(f"Open-Meteo: {lat:.2f},{lng:.2f} → {temp}°C")
    except Exception as e:
        logger.warning(f"Open-Meteo API error: {e}")

    _live_api_cache[cache_key] = result
    return result


async def fetch_usgs_earthquakes(lat: float, lng: float, radius_km: float = 200.0) -> dict:
    """
    Query USGS Earthquake Hazards API for recent seismic events near coordinates.

    Checks for earthquakes within `radius_km` in the past 7 days.

    Returns:
        dict with keys:
            - recent_quake_count: int (number of events in the window)
            - max_magnitude: float | None
            - nearest_km: float | None (distance of closest quake)
            - seismic_activity: bool (True if any recent quakes M >= 3.0)
            - api_success: bool
    """
    cache_key = f"usgs_{lat:.2f}_{lng:.2f}"
    if cache_key in _live_api_cache:
        return _live_api_cache[cache_key]

    result = {
        "recent_quake_count": 0,
        "max_magnitude": None,
        "nearest_km": None,
        "seismic_activity": False,
        "api_success": False,
    }

    try:
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=7)

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://earthquake.usgs.gov/fdsnws/event/1/query",
                params={
                    "format": "geojson",
                    "starttime": start_time.strftime("%Y-%m-%d"),
                    "endtime": end_time.strftime("%Y-%m-%d"),
                    "latitude": round(lat, 4),
                    "longitude": round(lng, 4),
                    "maxradiuskm": int(radius_km),
                    "minmagnitude": 2.5,
                    "limit": 50,
                    "orderby": "magnitude",
                },
            )
            if response.status_code == 200:
                data = response.json()
                features = data.get("features", [])
                result["recent_quake_count"] = len(features)
                result["api_success"] = True

                if features:
                    magnitudes = [f["properties"]["mag"] for f in features if f["properties"].get("mag")]
                    result["max_magnitude"] = max(magnitudes) if magnitudes else None

                    # Calculate closest quake distance
                    min_dist = float("inf")
                    for f in features:
                        coords = f["geometry"]["coordinates"]
                        dist = _haversine_km(lat, lng, coords[1], coords[0])
                        if dist < min_dist:
                            min_dist = dist
                    result["nearest_km"] = round(min_dist, 1) if min_dist < float("inf") else None

                    # Seismic activity flag: M >= 3.0 within radius
                    result["seismic_activity"] = any(
                        m >= 3.0 for m in magnitudes
                    )

                logger.info(
                    f"USGS: {lat:.2f},{lng:.2f} → {result['recent_quake_count']} quakes, "
                    f"max M{result['max_magnitude']}"
                )
    except Exception as e:
        logger.warning(f"USGS API error: {e}")

    _live_api_cache[cache_key] = result
    return result


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine formula for great-circle distance in km."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ──────────────────────────────────────────────────────────────────────────────
# Zero-Training Fusion Formula with Live Adjustments
# ──────────────────────────────────────────────────────────────────────────────

def compute_composite_risk_with_triggers(
    morphological_score: float,
    kinematic_score: float,
    thermal_score: float,
    meteo_result: dict,
    usgs_result: dict,
) -> dict:
    """
    Zero-Training Fusion Formula — combines morphological, kinematic, and
    thermal sub-scores with live environmental triggers.

    Formula:
        R_base = λ₁·M + λ₂·K + λ₃·T
        R_adjusted = R_base + δ_meteo + δ_seismic

    Where:
        M = morphological risk score (lake geometry + GLOF history)
        K = CryoFormer kinematic acceleration score
        T = ThermoSeq thermal anomaly score
        δ_meteo = +0.05 if current temperature > 0°C (melting boost)
        δ_seismic = +0.03–0.08 based on nearby earthquake magnitude

    Returns a composite dict with sub-scores and adjustments.
    """
    # Base fusion weights
    LAMBDA_M = 0.35
    LAMBDA_K = 0.40
    LAMBDA_T = 0.25

    r_base = LAMBDA_M * morphological_score + LAMBDA_K * kinematic_score + LAMBDA_T * thermal_score

    # Live trigger adjustments
    delta_meteo = 0.0
    delta_seismic = 0.0

    # Open-Meteo: temperature above freezing increases melt risk
    if meteo_result.get("api_success") and meteo_result.get("above_freezing"):
        temp = meteo_result.get("current_temp_c", 0)
        # Scale: +0.03 at 1°C, up to +0.08 at 10°C+
        delta_meteo = min(0.08, 0.03 + max(0, temp - 1) * 0.005)

    # USGS: seismic activity increases moraine destabilization risk
    if usgs_result.get("api_success") and usgs_result.get("seismic_activity"):
        max_mag = usgs_result.get("max_magnitude", 0) or 0
        nearest = usgs_result.get("nearest_km", 200) or 200
        # Proximity factor: closer quake = higher risk
        proximity_factor = max(0, 1 - nearest / 200)
        # Magnitude factor: M3=0.03, M5=0.06, M7=0.10
        magnitude_factor = min(0.10, max(0, (max_mag - 2.5) * 0.02))
        delta_seismic = magnitude_factor * (0.5 + 0.5 * proximity_factor)

    r_adjusted = min(1.0, max(0.0, r_base + delta_meteo + delta_seismic))

    # Risk level classification
    if r_adjusted >= 0.80:
        risk_level = "critical"
    elif r_adjusted >= 0.60:
        risk_level = "high"
    elif r_adjusted >= 0.35:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "morphological": round(morphological_score, 4),
        "kinematic": round(kinematic_score, 4),
        "thermal": round(thermal_score, 4),
        "r_base": round(r_base, 4),
        "delta_meteo": round(delta_meteo, 4),
        "delta_seismic": round(delta_seismic, 4),
        "composite": round(r_adjusted, 4),
        "risk_level": risk_level,
        "alert_triggered": r_adjusted >= 0.85,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Lifespan Context Manager — Load all models and data at startup
# ──────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan handler. Loads models + CSV into memory at startup
    to prevent cold-start latency on first request.
    """
    logger.info("=" * 60)
    logger.info("GLOFCast API Gateway — Starting up...")
    logger.info("=" * 60)

    # 1. Load CryoFormer (PyTorch)
    t0 = time.time()
    try:
        load_cryoformer(CRYOFORMER_PATH)
        logger.info(f"CryoFormer loaded in {time.time() - t0:.2f}s")
    except Exception as e:
        logger.error(f"CryoFormer load failed: {e}")

    # 2. Load ThermoSeq (TensorFlow/Keras)
    t0 = time.time()
    try:
        load_thermoseq(THERMOSEQ_PATH, THERMOSEQ_SCALER_PATH)
        logger.info(f"ThermoSeq loaded in {time.time() - t0:.2f}s")
    except Exception as e:
        logger.error(f"ThermoSeq load failed: {e}")

    # 3. Load and process CSV lake inventory
    t0 = time.time()
    try:
        _load_lake_inventory()
        logger.info(f"Lake inventory loaded in {time.time() - t0:.2f}s — {len(_lake_data_cache)} unique lakes")
    except Exception as e:
        logger.error(f"Lake inventory load failed: {e}")

    logger.info("=" * 60)
    logger.info("GLOFCast API Gateway — Ready to serve")
    logger.info("=" * 60)

    yield  # Application runs

    logger.info("GLOFCast API Gateway — Shutting down...")


def _load_lake_inventory():
    """
    Parse prepared_dataset.csv into an in-memory dict of unique lakes.
    The CSV has ~150k rows (multiple observations per lake); we deduplicate
    by GL_ID and take the latest observation for each.
    """
    global _lake_data_cache

    if not os.path.exists(CSV_PATH):
        logger.warning(f"CSV not found at {CSV_PATH}")
        return

    df = pd.read_csv(CSV_PATH, low_memory=False)
    logger.info(f"Raw CSV: {len(df)} rows, {len(df.columns)} columns")

    # Identify sub-region columns for readable region names
    subr_cols = [c for c in df.columns if c.startswith("GL_SubR_")]
    type_cols = [c for c in df.columns if c.startswith("GL_Type_")]

    # Group by GL_ID and take the latest year's observation
    latest = df.sort_values("GL_Year", ascending=False).drop_duplicates(subset=["GL_ID"], keep="first")
    logger.info(f"Unique lakes after dedup: {len(latest)}")

    # Sample a manageable subset for the API (top risk + geographic diversity)
    # Full dataset is 30k+ unique lakes — we serve a curated subset of ~500
    # sorted by GLOF_Weight descending for risk-first display
    latest_sorted = latest.sort_values("GLOF_Weight", ascending=False)
    top_lakes = latest_sorted.head(500)

    for _, row in top_lakes.iterrows():
        gl_id = str(row.get("GL_ID", "unknown"))

        # Extract sub-region name
        region = "Unknown Region"
        for col in subr_cols:
            if row.get(col, 0) == 1:
                region = col.replace("GL_SubR_", "").replace("_", " ")
                break

        # Extract lake type
        lake_type = "Unknown"
        for col in type_cols:
            if row.get(col, 0) == 1:
                lake_type = col.replace("GL_Type_", "").replace("_", " ").title()
                break

        area_m2 = float(row.get("GL_Area", 0))
        elevation = float(row.get("GL_Elev", 0))
        glof_weight = float(row.get("GLOF_Weight", 0))
        has_glof = bool(row.get("has_GLOF", 0))

        _lake_data_cache[gl_id] = {
            "id": gl_id,
            "name": _humanize_lake_id(gl_id),
            "lat": float(row.get("Latitude", 0)),
            "lng": float(row.get("Longitude", 0)),
            "elevation": elevation,
            "area": area_m2,
            "area_km2": round(area_m2 / 1e6, 4),
            "glof_weight": glof_weight,
            "has_glof": has_glof,
            "region": region,
            "lake_type": lake_type,
            "year": int(row.get("GL_Year", 0)),
            "distance": float(row.get("Distance", 0)),
            "perimeter": float(row.get("GL_Peri", 0)),
            "risk_score": 0.0,  # Computed on-demand via HydroFusion
            "risk_level": "low",
        }


def _humanize_lake_id(gl_id: str) -> str:
    """Convert GL_ID like 'GL067469E38933N' to a readable name."""
    if not gl_id.startswith("GL"):
        return gl_id
    try:
        # Extract coordinates from the ID pattern
        parts = gl_id[2:]  # Remove 'GL'
        # Parse lon/lat from the encoded format
        if 'E' in parts:
            lon_str, lat_str = parts.split('E')
            lon = float(lon_str) / 1000
            lat = float(lat_str.rstrip('NS')) / 1000
            return f"Glacial Lake {lon:.2f}°E {lat:.2f}°N"
        elif 'W' in parts:
            lon_str, lat_str = parts.split('W')
            lon = float(lon_str) / 1000
            lat = float(lat_str.rstrip('NS')) / 1000
            return f"Glacial Lake {lon:.2f}°W {lat:.2f}°{'S' if 'S' in parts else 'N'}"
        return gl_id
    except Exception:
        return gl_id


# ──────────────────────────────────────────────────────────────────────────────
# FastAPI Application
# ──────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="GLOFCast API Gateway",
    description=(
        "AI-powered GLOF prediction and monitoring — "
        "serving CryoFormer, ThermoSeq, HydroFusion models with live environmental triggers"
    ),
    version="2.0.0",
    lifespan=lifespan,
)

# CORS — Allow Next.js dev server and production origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────────────────────────────────────
# API Routes
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/api/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """System health and model status endpoint."""
    return HealthResponse(
        status="ok",
        cryoformer_loaded=is_cryoformer_loaded(),
        thermoseq_loaded=is_thermoseq_loaded(),
        lakes_loaded=len(_lake_data_cache),
        version="2.0.0",
    )


@app.get("/api/lakes", tags=["Lake Inventory"])
async def get_lakes(
    limit: int = Query(100, ge=1, le=500, description="Max lakes to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    min_risk: float = Query(0.0, ge=0.0, le=1.0, description="Minimum GLOF_Weight filter"),
    region: str = Query(None, description="Filter by sub-region name"),
    has_glof: bool = Query(None, description="Filter by historical GLOF presence"),
):
    """
    Serve the glacial lake inventory from prepared_dataset.csv.
    Returns a paginated, filterable list of lakes with pre-computed morphological risk.
    """
    lakes = list(_lake_data_cache.values())

    # Apply filters
    if min_risk > 0:
        lakes = [l for l in lakes if l["glof_weight"] >= min_risk / 100]
    if region:
        lakes = [l for l in lakes if region.lower() in l["region"].lower()]
    if has_glof is not None:
        lakes = [l for l in lakes if l["has_glof"] == has_glof]

    # Sort by GLOF weight descending (highest risk first)
    lakes.sort(key=lambda x: x["glof_weight"], reverse=True)

    total = len(lakes)
    paginated = lakes[offset:offset + limit]

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "lakes": paginated,
    }


@app.get("/api/lakes/search", tags=["Lake Inventory"])
async def search_lakes(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(20, ge=1, le=100),
):
    """Full-text search across lake names, IDs, and regions."""
    q_lower = q.lower()
    results = [
        lake for lake in _lake_data_cache.values()
        if q_lower in lake["name"].lower()
        or q_lower in lake["id"].lower()
        or q_lower in lake["region"].lower()
    ]
    results.sort(key=lambda x: x["glof_weight"], reverse=True)
    return {"results": results[:limit], "total": len(results)}


@app.get("/api/predict/velocity", response_model=VelocityPredictionResponse, tags=["Predictions"])
async def predict_velocity(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    days: int = Query(30, ge=7, le=90, description="Prediction horizon in days"),
):
    """
    CryoFormer velocity prediction for a given coordinate.
    Returns a time series of predicted ice velocity (m/yr).
    """
    cache_key = f"vel_{lat:.4f}_{lng:.4f}_{days}"
    if cache_key in _prediction_cache:
        predictions = _prediction_cache[cache_key]
    else:
        predictions = cryoformer_predict_sequence(lat, lng, days)
        _prediction_cache[cache_key] = predictions

    return VelocityPredictionResponse(
        lat=lat,
        lng=lng,
        predictions=[TimeSeriesPoint(**p) for p in predictions],
        model="CryoFormer-5.5M",
    )


@app.get("/api/predict/temperature", response_model=TemperaturePredictionResponse, tags=["Predictions"])
async def predict_temperature(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    days: int = Query(30, ge=7, le=90, description="Prediction horizon in days"),
):
    """
    ThermoSeq temperature prediction for a given coordinate.
    Returns a time series of predicted surface temperature (°C).
    """
    cache_key = f"temp_{lat:.4f}_{lng:.4f}_{days}"
    if cache_key in _prediction_cache:
        predictions = _prediction_cache[cache_key]
    else:
        predictions = thermoseq_predict_sequence(lat, lng, days)
        _prediction_cache[cache_key] = predictions

    return TemperaturePredictionResponse(
        lat=lat,
        lng=lng,
        predictions=[TimeSeriesPoint(**p) for p in predictions],
        model="ThermoSeq-LSTM",
    )


# ──────────────────────────────────────────────────────────────────────────────
# NEW: /api/lake/{id}/telemetry — Zero-Training Fusion with Live Triggers
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/api/lake/{lake_id}/telemetry", response_model=TelemetryResponse, tags=["Telemetry"])
async def get_lake_telemetry(
    lake_id: str,
    days: int = Query(30, ge=7, le=90),
):
    """
    Comprehensive telemetry endpoint with Zero-Training Fusion Formula.

    Pipeline:
    1. Look up lake metadata from CSV inventory
    2. Generate CryoFormer velocity predictions (kinematic score)
    3. Generate ThermoSeq temperature predictions (thermal score)
    4. Compute morphological baseline from GLOF_Weight + lake geometry
    5. Call Open-Meteo API for live temperature (above-freezing check)
    6. Call USGS Earthquake API for recent seismic activity
    7. Fuse all signals into a composite risk score with live adjustments

    Returns: TelemetryResponse with sub-scores, live triggers, and composite risk.
    """
    # Look up lake in inventory
    lake = _lake_data_cache.get(lake_id)
    if not lake:
        raise HTTPException(status_code=404, detail=f"Lake '{lake_id}' not found in inventory")

    lat, lng = lake["lat"], lake["lng"]

    # Run prediction pipelines (with caching)
    vel_cache_key = f"vel_{lat:.4f}_{lng:.4f}_{days}"
    temp_cache_key = f"temp_{lat:.4f}_{lng:.4f}_{days}"

    if vel_cache_key in _prediction_cache:
        velocity_series = _prediction_cache[vel_cache_key]
    else:
        velocity_series = cryoformer_predict_sequence(lat, lng, days)
        _prediction_cache[vel_cache_key] = velocity_series

    if temp_cache_key in _prediction_cache:
        temperature_series = _prediction_cache[temp_cache_key]
    else:
        temperature_series = thermoseq_predict_sequence(lat, lng, days)
        _prediction_cache[temp_cache_key] = temperature_series

    # Compute sub-model scores via HydroFusion
    risk_result = compute_fusion_risk(
        glof_weight=lake["glof_weight"],
        has_glof=lake["has_glof"],
        area=lake["area"],
        elevation=lake["elevation"],
        velocity_series=velocity_series,
        temperature_series=temperature_series,
    )

    # ── Live API Triggers ─────────────────────────────────────────────────
    meteo_result = await fetch_open_meteo_temperature(lat, lng)
    usgs_result = await fetch_usgs_earthquakes(lat, lng, radius_km=200)

    # ── Composite Risk with Live Adjustments ──────────────────────────────
    composite = compute_composite_risk_with_triggers(
        morphological_score=risk_result["morphological"],
        kinematic_score=risk_result["kinematic"],
        thermal_score=risk_result["thermal"],
        meteo_result=meteo_result,
        usgs_result=usgs_result,
    )

    # Build lake record
    lake_record = GlacialLakeRecord(
        **{**lake, "risk_score": composite["composite"],
           "risk_level": RiskLevel(composite["risk_level"])}
    )

    # Construct alert payload if triggered
    alert_payload = None
    if composite["alert_triggered"]:
        from hydrofusion import generate_avaflow_payload
        alert_payload = generate_avaflow_payload(
            fusion_score=composite["composite"],
            morphological=composite["morphological"],
            kinematic=composite["kinematic"],
            thermal=composite["thermal"],
            velocity_series=velocity_series,
            temperature_series=temperature_series,
        )

    return TelemetryResponse(
        lake=lake_record,
        velocity_series=[TimeSeriesPoint(**p) for p in velocity_series],
        temperature_series=[TimeSeriesPoint(**p) for p in temperature_series],
        risk_scores=SubModelScores(
            cryoformer=composite["kinematic"],
            thermoseq=composite["thermal"],
            morphological=composite["morphological"],
            fusion=composite["composite"],
        ),
        live_triggers=LiveTriggers(
            meteo_temp_c=meteo_result.get("current_temp_c"),
            meteo_above_freezing=meteo_result.get("above_freezing", False),
            meteo_api_ok=meteo_result.get("api_success", False),
            usgs_quake_count=usgs_result.get("recent_quake_count", 0),
            usgs_max_magnitude=usgs_result.get("max_magnitude"),
            usgs_nearest_km=usgs_result.get("nearest_km"),
            usgs_seismic_flag=usgs_result.get("seismic_activity", False),
            usgs_api_ok=usgs_result.get("api_success", False),
            delta_meteo=composite["delta_meteo"],
            delta_seismic=composite["delta_seismic"],
        ),
        environmental=EnvironmentalSnapshot(
            current_temp_c=meteo_result.get("current_temp_c"),
            recent_quake_count=usgs_result.get("recent_quake_count", 0),
            max_quake_magnitude=usgs_result.get("max_magnitude"),
        ),
        r_base=composite["r_base"],
        r_adjusted=composite["composite"],
        alert_triggered=composite["alert_triggered"],
        alert_payload=alert_payload,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Existing: /api/lake/{id}/full-telemetry — Legacy endpoint
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/api/lake/{lake_id}/full-telemetry", response_model=FullTelemetryResponse, tags=["Telemetry"])
async def get_full_telemetry(
    lake_id: str,
    days: int = Query(30, ge=7, le=90),
):
    """
    Full telemetry pipeline for a specific lake.

    Runs the complete GLOFCast pipeline:
    1. Look up lake metadata from CSV inventory
    2. Generate CryoFormer velocity predictions
    3. Generate ThermoSeq temperature predictions
    4. Compute deterministic HydroFusion fusion score
    5. Check hydrodynamic routing trigger threshold

    This is the primary endpoint consumed by the frontend's telemetry panels.
    """
    # Look up lake in inventory
    lake = _lake_data_cache.get(lake_id)
    if not lake:
        raise HTTPException(status_code=404, detail=f"Lake '{lake_id}' not found in inventory")

    lat, lng = lake["lat"], lake["lng"]

    # Run prediction pipelines (with caching)
    vel_cache_key = f"vel_{lat:.4f}_{lng:.4f}_{days}"
    temp_cache_key = f"temp_{lat:.4f}_{lng:.4f}_{days}"

    if vel_cache_key in _prediction_cache:
        velocity_series = _prediction_cache[vel_cache_key]
    else:
        velocity_series = cryoformer_predict_sequence(lat, lng, days)
        _prediction_cache[vel_cache_key] = velocity_series

    if temp_cache_key in _prediction_cache:
        temperature_series = _prediction_cache[temp_cache_key]
    else:
        temperature_series = thermoseq_predict_sequence(lat, lng, days)
        _prediction_cache[temp_cache_key] = temperature_series

    # Compute HydroFusion fusion
    risk_result = compute_fusion_risk(
        glof_weight=lake["glof_weight"],
        has_glof=lake["has_glof"],
        area=lake["area"],
        elevation=lake["elevation"],
        velocity_series=velocity_series,
        temperature_series=temperature_series,
    )

    # Build response
    lake_record = GlacialLakeRecord(
        **{**lake, "risk_score": risk_result["fusion"],
           "risk_level": RiskLevel(risk_result["risk_level"])}
    )

    return FullTelemetryResponse(
        lake=lake_record,
        velocity_series=[TimeSeriesPoint(**p) for p in velocity_series],
        temperature_series=[TimeSeriesPoint(**p) for p in temperature_series],
        risk_scores=SubModelScores(
            cryoformer=risk_result["kinematic"],
            thermoseq=risk_result["thermal"],
            morphological=risk_result["morphological"],
            fusion=risk_result["fusion"],
        ),
        alert_triggered=risk_result["alert_triggered"],
        alert_payload=risk_result["alert_payload"],
    )


@app.get("/api/coordinate/full-telemetry", response_model=FullTelemetryResponse, tags=["Telemetry"])
async def get_coordinate_telemetry(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    days: int = Query(30, ge=7, le=90),
):
    """
    Full telemetry pipeline for an arbitrary coordinate (custom map click).
    Uses default morphological parameters since the location may not be in the CSV.
    """
    # Generate predictions
    velocity_series = cryoformer_predict_sequence(lat, lng, days)
    temperature_series = thermoseq_predict_sequence(lat, lng, days)

    # Default morphological params for unknown locations
    risk_result = compute_fusion_risk(
        glof_weight=0.003,
        has_glof=False,
        area=200000,
        elevation=abs(lat) * 100 + 2000,
        velocity_series=velocity_series,
        temperature_series=temperature_series,
    )

    lake_record = GlacialLakeRecord(
        id=f"custom-{lat:.4f}-{lng:.4f}",
        name=f"Location {lat:.3f}°, {lng:.3f}°",
        lat=lat,
        lng=lng,
        elevation=abs(lat) * 100 + 2000,
        area=200000,
        area_km2=0.2,
        glof_weight=0.003,
        has_glof=False,
        region=f"{'N' if lat >= 0 else 'S'}{abs(lat):.0f}° {'E' if lng >= 0 else 'W'}{abs(lng):.0f}°",
        lake_type="Custom Pin",
        year=2024,
        risk_score=risk_result["fusion"],
        risk_level=RiskLevel(risk_result["risk_level"]),
    )

    return FullTelemetryResponse(
        lake=lake_record,
        velocity_series=[TimeSeriesPoint(**p) for p in velocity_series],
        temperature_series=[TimeSeriesPoint(**p) for p in temperature_series],
        risk_scores=SubModelScores(
            cryoformer=risk_result["kinematic"],
            thermoseq=risk_result["thermal"],
            morphological=risk_result["morphological"],
            fusion=risk_result["fusion"],
        ),
        alert_triggered=risk_result["alert_triggered"],
        alert_payload=risk_result["alert_payload"],
    )


# ──────────────────────────────────────────────────────────────────────────────
# Historical GLOF Validation Endpoints
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/api/historical/events", tags=["Historical Validation"])
async def list_historical_events():
    """List all curated historical GLOF events available for validation replay."""
    events = get_historical_events()
    return {
        "total": len(events),
        "events": [
            {
                "lake_id": e["lake_id"],
                "lake_name": e["lake_name"],
                "event_date": e["event_date"],
                "causes": e["causes"],
                "lat": e["lat"],
                "lng": e["lng"],
            }
            for e in events
        ],
    }


@app.get("/api/historical/replay/{lake_id}", response_model=HistoricalGLOFEvent, tags=["Historical Validation"])
async def get_historical_replay(lake_id: str):
    """
    Generate a full validation replay for a historical GLOF event.
    Shows how CryoFormer + ThermoSeq + HydroFusion would have performed
    in the 30 days preceding the documented event.
    """
    event = get_event_by_lake_id(lake_id)
    if not event:
        raise HTTPException(
            status_code=404,
            detail=f"No historical GLOF event found for lake_id '{lake_id}'"
        )

    replay = generate_validation_replay(event)
    return HistoricalGLOFEvent(**replay)


# ──────────────────────────────────────────────────────────────────────────────
# Entrypoint
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
