"""
GLOFCast Backend — HydroFusion HydroFusion: Zero-Training Deterministic Hazard Fusion Engine
========================================================
Implements a zero-training mathematical fusion that combines:
  1. Morphological risk (from prepared_dataset.csv GLOF_Weight)
  2. CryoFormer velocity acceleration anomalies
  3. ThermoSeq thermal spike detection

The fusion produces a final risk score in [0.0, 1.0] and triggers
hydrodynamic routing alerts when the score breaches 0.85.

Weight Configuration:
  - Morphological (λ₁ = 0.35): Static lake geometry & historical GLOF probability
  - Kinematic    (λ₂ = 0.40): Ice velocity acceleration relative to baseline
  - Thermal      (λ₃ = 0.25): Temperature anomaly above freezing threshold

Academic Reference Hooks:
  - TODO: PINN penalty functions for energy-conservation constraints
  - TODO: Multi-Head Cross-Attention for CryoFormer × ThermoSeq fusion
"""

from __future__ import annotations
import numpy as np
import logging

logger = logging.getLogger("glofcast.hydrofusion")

# ─── Fusion weights (sum must equal 1.0) ─────────────────────────────────────
LAMBDA_MORPHOLOGICAL = 0.35  # λ₁: Static lake morphology baseline
LAMBDA_KINEMATIC = 0.40      # λ₂: Ice velocity acceleration anomaly
LAMBDA_THERMAL = 0.25        # λ₃: Thermal spike anomaly

# ─── Alert threshold for hydrodynamic routing trigger ─────────────────────────
ALERT_THRESHOLD = 0.85


def compute_morphological_score(glof_weight: float, has_glof: bool, area: float,
                                 elevation: float) -> float:
    """
    Normalize the morphological risk from raw CSV features.

    Combines GLOF_Weight (pre-computed in dataset) with area/elevation
    heuristics. Lakes with prior GLOF history receive a +0.15 bias.

    Returns: float in [0.0, 1.0]
    """
    # GLOF_Weight is already a probability-like score; normalize to [0, 1]
    base = min(1.0, glof_weight * 100)  # Raw weights are typically 0.001-0.01

    # Area factor: smaller lakes are more susceptible to rapid level changes
    area_km2 = area / 1e6  # Convert m² to km²
    area_factor = max(0, 1.0 - area_km2 / 50.0)  # Inversely proportional, capped

    # Elevation factor: higher elevation → more glacial melt risk
    elev_factor = min(1.0, elevation / 6000.0)

    score = 0.5 * base + 0.25 * area_factor + 0.25 * elev_factor

    # Historical GLOF bias
    if has_glof:
        score = min(1.0, score + 0.15)

    return round(min(1.0, max(0.0, score)), 4)


def compute_kinematic_score(velocity_series: list[dict]) -> float:
    """
    Detect velocity acceleration anomalies from CryoFormer output.

    Method: Compare the mean velocity of the last 7 days against the
    full-window baseline. A z-score approach flags deviations > 1.5σ.

    Returns: float in [0.0, 1.0]
    """
    if not velocity_series or len(velocity_series) < 7:
        return 0.3  # Insufficient data → moderate uncertainty default

    values = [p["value"] for p in velocity_series]
    baseline_mean = np.mean(values)
    baseline_std = np.std(values) + 1e-6  # Prevent division by zero

    recent_mean = np.mean(values[-7:])

    # Z-score of recent acceleration relative to baseline
    z_score = (recent_mean - baseline_mean) / baseline_std

    # Map z-score to [0, 1] via sigmoid-like scaling
    # z > 2.0 → ~0.88, z > 3.0 → ~0.95
    score = 1.0 / (1.0 + np.exp(-1.5 * (z_score - 1.0)))

    # Also detect sustained acceleration trend (regression slope)
    if len(values) >= 14:
        x = np.arange(len(values[-14:]))
        slope = np.polyfit(x, values[-14:], 1)[0]
        # Positive slope = accelerating → increase score
        trend_bonus = max(0, min(0.2, slope / (baseline_mean * 0.1)))
        score = min(1.0, score + trend_bonus)

    return round(min(1.0, max(0.0, float(score))), 4)


def compute_thermal_score(temperature_series: list[dict]) -> float:
    """
    Detect thermal spike anomalies from ThermoSeq output.

    Method: Count days above 0°C (melting threshold) in the recent window
    and measure the amplitude of positive temperature excursions.

    Returns: float in [0.0, 1.0]
    """
    if not temperature_series or len(temperature_series) < 7:
        return 0.3  # Insufficient data → moderate uncertainty default

    values = [p["value"] for p in temperature_series]

    # Count days above freezing in the last 14 days
    recent = values[-14:] if len(values) >= 14 else values
    days_above_zero = sum(1 for v in recent if v > 0)
    melt_fraction = days_above_zero / len(recent)

    # Max positive temperature spike
    max_temp = max(recent)
    spike_score = min(1.0, max(0, max_temp) / 15.0)  # 15°C normalizer

    # Rate of temperature increase
    if len(values) >= 7:
        temp_delta = np.mean(values[-3:]) - np.mean(values[:3])
        warming_score = max(0, min(1.0, temp_delta / 10.0))
    else:
        warming_score = 0.0

    score = 0.4 * melt_fraction + 0.35 * spike_score + 0.25 * warming_score

    return round(min(1.0, max(0.0, float(score))), 4)


# ──────────────────────────────────────────────────────────────────────────────
# HydroFusion Fusion — Main scoring function
# ──────────────────────────────────────────────────────────────────────────────

def compute_fusion_risk(
    glof_weight: float,
    has_glof: bool,
    area: float,
    elevation: float,
    velocity_series: list[dict],
    temperature_series: list[dict],
) -> dict:
    """
    Deterministic HydroFusion Fusion — the mathematical heart of GLOFCast.

    Combines three independent risk signals into a single score:
        R = λ₁·M + λ₂·K + λ₃·T

    Where:
        M = morphological_score (lake geometry + GLOF history)
        K = kinematic_score    (CryoFormer velocity anomalies)
        T = thermal_score      (ThermoSeq temperature anomalies)

    Returns a dict with sub-scores, fusion score, risk level, and alert status.
    """
    morphological = compute_morphological_score(glof_weight, has_glof, area, elevation)
    kinematic = compute_kinematic_score(velocity_series)
    thermal = compute_thermal_score(temperature_series)

    # ── Weighted linear fusion ────────────────────────────────────────────
    fusion = (
        LAMBDA_MORPHOLOGICAL * morphological +
        LAMBDA_KINEMATIC * kinematic +
        LAMBDA_THERMAL * thermal
    )
    fusion = round(min(1.0, max(0.0, fusion)), 4)

    # ── TODO: Physics-Informed Neural Network (PINN) Penalty ──────────────
    # In a future iteration, add a physics-consistency penalty term:
    #
    #   R_pinn = R + α·penalty(conservation_of_energy(velocity, temperature))
    #
    # This would penalize predictions where high velocity doesn't correlate
    # with expected thermal energy budgets, enforcing Glen's Flow Law:
    #
    #   ε̇ = A·τⁿ  (where n ≈ 3 for glacial ice)
    #
    # def pinn_penalty(velocity_pred, temp_pred, lake_geometry):
    #     # Glen's flow law consistency check
    #     expected_strain_rate = A * (shear_stress ** n)
    #     observed_strain_rate = velocity_pred / ice_thickness
    #     return alpha * (expected_strain_rate - observed_strain_rate) ** 2

    # ── Risk level classification ─────────────────────────────────────────
    if fusion >= 0.8:
        risk_level = "critical"
    elif fusion >= 0.6:
        risk_level = "high"
    elif fusion >= 0.35:
        risk_level = "medium"
    else:
        risk_level = "low"

    # ── Hydrodynamic routing trigger ──────────────────────────────────────
    alert_triggered = fusion >= ALERT_THRESHOLD
    alert_payload = None

    if alert_triggered:
        alert_payload = generate_avaflow_payload(
            fusion_score=fusion,
            morphological=morphological,
            kinematic=kinematic,
            thermal=thermal,
            velocity_series=velocity_series,
            temperature_series=temperature_series,
        )

    return {
        "morphological": morphological,
        "kinematic": kinematic,
        "thermal": thermal,
        "fusion": fusion,
        "risk_level": risk_level,
        "alert_triggered": alert_triggered,
        "alert_payload": alert_payload,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Hydrodynamic Routing Payload (r.avaflow bridge)
# ──────────────────────────────────────────────────────────────────────────────

def generate_avaflow_payload(
    fusion_score: float,
    morphological: float,
    kinematic: float,
    thermal: float,
    velocity_series: list[dict],
    temperature_series: list[dict],
) -> dict:
    """
    Generate an alert payload formatted for the r.avaflow hydrodynamic
    routing engine. This bridges AI prediction → physical disaster mapping.

    In production, this payload would be sent to a GRASS GIS instance
    running r.avaflow for debris flow / flood wave simulation.
    """
    recent_velocity = velocity_series[-1]["value"] if velocity_series else 0
    recent_temp = temperature_series[-1]["value"] if temperature_series else 0

    return {
        "engine": "r.avaflow",
        "version": "2.4",
        "trigger": {
            "type": "GLOF_RISK_THRESHOLD_BREACH",
            "fusion_score": fusion_score,
            "timestamp_utc": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        },
        "sub_scores": {
            "morphological": morphological,
            "kinematic": kinematic,
            "thermal": thermal,
        },
        "initial_conditions": {
            "ice_velocity_m_yr": recent_velocity,
            "surface_temperature_c": recent_temp,
            "estimated_discharge_m3_s": _estimate_discharge(fusion_score, recent_velocity),
        },
        "simulation_params": {
            "flow_model": "Voellmy",
            "rheology": "Bingham",
            "resolution_m": 10,
            "time_steps": 3600,
            "manning_n": 0.04,
        },
        "priority": "P0_CRITICAL",
        "actions": [
            "NOTIFY_NDMA",
            "ACTIVATE_EARLY_WARNING_SIRENS",
            "DOWNSTREAM_EVACUATION_ADVISORY",
        ],
    }


def _estimate_discharge(fusion_score: float, velocity: float) -> float:
    """
    Back-of-envelope discharge estimate for r.avaflow initial conditions.
    Uses empirical scaling: Q ∝ velocity × risk_factor².
    """
    return round(velocity * (fusion_score ** 2) * 100, 1)
