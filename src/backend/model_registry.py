"""
GLOFCast Backend — Model Registry
===================================
Handles loading and lifecycle of the CryoFormer (PyTorch) and ThermoSeq (TensorFlow)
models. Uses a singleton pattern with lifespan context manager to prevent cold starts.

Architecture Decision: Models are loaded once at startup and held in module-level
globals accessible to all request handlers via dependency injection.
"""

from __future__ import annotations
import os
import logging
import numpy as np
import torch
import torch.nn as nn

logger = logging.getLogger("glofcast.models")

# ─── Module-level model state (populated at startup) ─────────────────────────
_cryoformer_model = None
_cryoformer_device = None
_thermoseq_model = None
_thermoseq_scaler = None


# ──────────────────────────────────────────────────────────────────────────────
# CryoFormer — CryoFormer: 5.5M-Parameter Cryospheric Kinematics Transformer Encoder
# Architecture: 5.5M param Transformer Encoder with positional embeddings
# Input: 32-step sequence of [lon, lat, year, month_sin, month_cos, day_sin, day_cos, avg_velocity]
# Output: Next-day velocity prediction (m/yr)
# ──────────────────────────────────────────────────────────────────────────────
class TransformerRegressor(nn.Module):
    """
    Mirrors the exact architecture from dashboard/cryoformer.py to ensure
    weight compatibility with cryoformer-5.5M.pth.
    """
    def __init__(self, input_dim: int = 8, d_model: int = 256, nhead: int = 8,
                 num_layers: int = 4, dropout: float = 0.1):
        super(TransformerRegressor, self).__init__()
        self.embedding = nn.Linear(input_dim, d_model)
        self.pos_encoder = nn.Parameter(torch.zeros(1, 1000, d_model))
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=nhead, dropout=dropout, batch_first=True
        )
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.fc = nn.Linear(d_model, 1)
        self._init_weights()

    def _init_weights(self):
        for p in self.parameters():
            if p.dim() > 1:
                nn.init.xavier_uniform_(p)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        batch_size, seq_len, _ = x.size()
        x = self.embedding(x)
        x = x + self.pos_encoder[:, :seq_len, :]
        x = self.transformer_encoder(x)
        x = self.fc(x[:, -1, :])  # Use last token for regression
        return x

    # ── TODO: Multi-Head Cross-Attention Layer ────────────────────────────
    # In a future iteration, insert a cross-attention module here that
    # attends to ThermoSeq's climate embedding, enabling the kinematic
    # model to condition its predictions on thermal context.
    #
    # class CrossAttentionFusion(nn.Module):
    #     def __init__(self, d_model=256, nhead=4):
    #         super().__init__()
    #         self.cross_attn = nn.MultiheadAttention(d_model, nhead, batch_first=True)
    #     def forward(self, kinematic_emb, climate_emb):
    #         fused, _ = self.cross_attn(kinematic_emb, climate_emb, climate_emb)
    #         return fused


# ──────────────────────────────────────────────────────────────────────────────
# Model Loading Functions
# ──────────────────────────────────────────────────────────────────────────────

def load_cryoformer(model_path: str) -> tuple:
    """Load the CryoFormer PyTorch model from disk."""
    global _cryoformer_model, _cryoformer_device

    _cryoformer_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    _cryoformer_model = TransformerRegressor(
        input_dim=8, d_model=256, nhead=8, num_layers=4, dropout=0.1
    ).to(_cryoformer_device)

    if os.path.exists(model_path):
        _cryoformer_model.load_state_dict(
            torch.load(model_path, map_location=_cryoformer_device, weights_only=True)
        )
        logger.info(f"CryoFormer loaded on {_cryoformer_device} from {model_path}")
    else:
        logger.warning(f"CryoFormer weights not found at {model_path}, using random init")

    _cryoformer_model.eval()
    return _cryoformer_model, _cryoformer_device


def load_thermoseq(model_path: str, scaler_path: str) -> tuple:
    """Load the ThermoSeq TensorFlow/Keras model and its feature scaler."""
    global _thermoseq_model, _thermoseq_scaler
    import joblib

    if os.path.exists(model_path):
        # Suppress TF logging noise during load
        os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
        import tensorflow as tf
        _thermoseq_model = tf.keras.models.load_model(model_path)
        logger.info(f"ThermoSeq loaded from {model_path}")
    else:
        logger.warning(f"ThermoSeq weights not found at {model_path}")

    if os.path.exists(scaler_path):
        _thermoseq_scaler = joblib.load(scaler_path)
        logger.info(f"ThermoSeq scaler loaded from {scaler_path}")
    else:
        logger.warning(f"ThermoSeq scaler not found at {scaler_path}")

    return _thermoseq_model, _thermoseq_scaler


# ──────────────────────────────────────────────────────────────────────────────
# Accessor functions for dependency injection
# ──────────────────────────────────────────────────────────────────────────────

def get_cryoformer():
    return _cryoformer_model, _cryoformer_device

def get_thermoseq():
    return _thermoseq_model, _thermoseq_scaler

def is_cryoformer_loaded() -> bool:
    return _cryoformer_model is not None

def is_thermoseq_loaded() -> bool:
    return _thermoseq_model is not None


# ──────────────────────────────────────────────────────────────────────────────
# Inference helpers (deterministic prediction for API endpoints)
# ──────────────────────────────────────────────────────────────────────────────

def cryoformer_predict_sequence(lat: float, lon: float, days: int = 30) -> list[dict]:
    """
    Generate a velocity prediction sequence using CryoFormer.
    Uses synthetic baseline data when ITS_LIVE is unavailable,
    producing deterministic output suitable for UI rendering.
    """
    model, device = get_cryoformer()
    if model is None:
        return _synthetic_velocity_series(lat, lon, days)

    predictions = []
    from datetime import datetime, timedelta

    # Build a synthetic 32-day seed sequence (baseline + seasonal component)
    base_velocity = 50.0 + abs(lat) * 1.5  # Higher latitudes → higher base velocity
    seed_sequence = []
    now = datetime.utcnow()

    for i in range(32):
        d = now - timedelta(days=32 - i)
        month_sin = np.sin(2 * np.pi * d.month / 12)
        month_cos = np.cos(2 * np.pi * d.month / 12)
        days_in_month = (d.replace(month=d.month % 12 + 1, day=1) - timedelta(days=1)).day if d.month < 12 else 31
        day_sin = np.sin(2 * np.pi * d.day / days_in_month)
        day_cos = np.cos(2 * np.pi * d.day / days_in_month)
        vel = base_velocity + 10 * np.sin(2 * np.pi * d.timetuple().tm_yday / 365)
        seed_sequence.append([lon, lat, d.year, month_sin, month_cos, day_sin, day_cos, vel])

    current_sequence = np.array(seed_sequence, dtype=np.float32)

    # Autoregressive rollout for `days` steps
    for i in range(days):
        target_date = now + timedelta(days=i)
        input_tensor = torch.tensor(current_sequence, dtype=torch.float32).unsqueeze(0).to(device)

        with torch.no_grad():
            pred = model(input_tensor).item()

        predictions.append({
            "date": target_date.strftime("%Y-%m-%d"),
            "value": round(pred, 2)
        })

        # Roll the window forward
        next_date = target_date + timedelta(days=1)
        days_in_month = 31 if next_date.month == 12 else (
            next_date.replace(month=next_date.month % 12 + 1, day=1) - timedelta(days=1)
        ).day
        new_row = [
            lon, lat, next_date.year,
            np.sin(2 * np.pi * next_date.month / 12),
            np.cos(2 * np.pi * next_date.month / 12),
            np.sin(2 * np.pi * next_date.day / days_in_month),
            np.cos(2 * np.pi * next_date.day / days_in_month),
            pred
        ]
        current_sequence = np.roll(current_sequence, -1, axis=0)
        current_sequence[-1] = new_row

    return predictions


def thermoseq_predict_sequence(lat: float, lon: float, days: int = 30) -> list[dict]:
    """
    Generate a temperature prediction sequence using ThermoSeq.
    Falls back to synthetic generation when model/scaler unavailable.
    """
    model, scaler = get_thermoseq()
    if model is None or scaler is None:
        return _synthetic_temperature_series(lat, lon, days)

    from datetime import datetime, timedelta

    predictions = []
    now = datetime.utcnow()

    # Build a 30-day seed of scaled features
    seed_features = []
    for i in range(30):
        d = now - timedelta(days=30 - i)
        row = {
            'Latitude': lat, 'Longitude': lon, 'year': d.year,
            'month_sin': np.sin(2 * np.pi * d.month / 12),
            'month_cos': np.cos(2 * np.pi * d.month / 12),
            'dayofyear_sin': np.sin(2 * np.pi * d.timetuple().tm_yday / 365.25),
            'dayofyear_cos': np.cos(2 * np.pi * d.timetuple().tm_yday / 365.25),
        }
        seed_features.append(row)

    import pandas as pd
    df = pd.DataFrame(seed_features)
    feature_columns = ['Latitude', 'Longitude', 'year', 'month_sin', 'month_cos',
                        'dayofyear_sin', 'dayofyear_cos']

    try:
        current_seq = scaler.transform(df[feature_columns])
    except Exception:
        return _synthetic_temperature_series(lat, lon, days)

    # Autoregressive rollout
    for i in range(days):
        target_date = now + timedelta(days=i)
        pred = model.predict(current_seq[np.newaxis, :, :], verbose=0)[0][0]

        predictions.append({
            "date": target_date.strftime("%Y-%m-%d"),
            "value": round(float(pred), 2)
        })

        # Slide window
        new_features = {
            'Latitude': lat, 'Longitude': lon, 'year': target_date.year,
            'month_sin': np.sin(2 * np.pi * target_date.month / 12),
            'month_cos': np.cos(2 * np.pi * target_date.month / 12),
            'dayofyear_sin': np.sin(2 * np.pi * target_date.timetuple().tm_yday / 365.25),
            'dayofyear_cos': np.cos(2 * np.pi * target_date.timetuple().tm_yday / 365.25),
        }
        new_row = pd.DataFrame([new_features])
        scaled_row = scaler.transform(new_row[feature_columns])
        current_seq = np.vstack([current_seq[1:], scaled_row])

    return predictions


# ──────────────────────────────────────────────────────────────────────────────
# Synthetic fallbacks (deterministic, no model required)
# ──────────────────────────────────────────────────────────────────────────────

def _synthetic_velocity_series(lat: float, lon: float, days: int) -> list[dict]:
    """Deterministic velocity series based on coordinates and seasonal cycle."""
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    base = 50.0 + abs(lat) * 1.2
    results = []
    for i in range(days):
        d = now - timedelta(days=days - 1 - i)
        doy = d.timetuple().tm_yday
        seasonal = 15 * np.sin(2 * np.pi * doy / 365)
        # Deterministic noise from coordinate hash
        noise = 5 * np.sin(lat * 1000 + lon * 500 + i * 7.3)
        results.append({
            "date": d.strftime("%Y-%m-%d"),
            "value": round(base + seasonal + noise, 2)
        })
    return results


def _synthetic_temperature_series(lat: float, lon: float, days: int) -> list[dict]:
    """Deterministic temperature series based on coordinates and seasonal cycle."""
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    # Base temp decreases with latitude and elevation proxy
    base = 15.0 - abs(lat) * 0.35
    results = []
    for i in range(days):
        d = now - timedelta(days=days - 1 - i)
        doy = d.timetuple().tm_yday
        # Northern vs southern hemisphere phase offset
        phase_offset = 0 if lat >= 0 else 182
        seasonal = 8 * np.sin(2 * np.pi * (doy - 100 + phase_offset) / 365)
        noise = 2 * np.sin(lat * 800 + lon * 400 + i * 11.7)
        results.append({
            "date": d.strftime("%Y-%m-%d"),
            "value": round(base + seasonal + noise, 2)
        })
    return results
