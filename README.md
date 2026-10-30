# GLOFCast: Multimodal Deep Learning & Systems Engineering Framework for Glacial Lake Outburst Flood (GLOF) Early Warning

<div align="center">

[![Python Version](https://img.shields.io/badge/Python-3.10%20%7C%203.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.4.1%20CUDA%20Accelerated-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)](https://pytorch.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-15.0%20App%20Router-000000?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose%20Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)
[![Academic Thesis](https://img.shields.io/badge/MNNIT%20Allahabad-B.Tech%20Thesis-800000?style=for-the-badge)](src/Docs/BTech_Latex_Report/thesis.tex)

**An operational, physics-constrained artificial intelligence platform synthesizing satellite SAR kinematics, thermodynamic surface regimes, and real-time environmental API triggers into automated hydrodynamic inundation simulations.**

[Key Innovations](#key-innovations) •
[System Architecture](#system-architecture) •
[Scientific Foundations](#scientific-foundations) •
[Disaster Hindcast Benchmarks](#historical-disaster-hindcast-benchmarks) •
[Quickstart](#quickstart--deployment) •
[API Reference](#api-specification) •
[Citation](#citation--academic-reference)

</div>

---

## Executive Summary

Glacial Lake Outburst Floods (GLOFs) represent one of the most destructive and accelerating natural hazards across High Mountain Asia (HMA) and glaciated alpine orogens worldwide. Under anthropogenic climatic forcing, thousands of proglacial lakes impounded behind inherently metastable, unconsolidated moraine dams have expanded exponentially. Structural breach releases multi-phase slurries with peak discharges exceeding meteorological floods by one to two orders of magnitude, catastrophic to downstream valleys and infrastructure.

**GLOFCast** resolves the fundamental bottlenecks of classical optical remote sensing (monsoon cloud blindness) and conventional machine learning models (catastrophic overfitting due to extreme historical breach scarcity, where $< 0.1\%$ of $>30,000$ lakes have recorded failures).

Instead of forcing an unconstrained black-box classification, GLOFCast enforces an architecturally decoupled paradigm:
1. **High-capacity deep sequence regressors** model continuous, physical state transitions:
   - **CryoFormer**: A 5,518,849-parameter (5.5M) Transformer Encoder capturing satellite SAR/optical ice velocity fields.
   - **ThermoSeq**: A recurrent LSTM sequence predictor modeling continuous 30-day surface thermodynamic forcing trajectories.
2. **HydroFusion Engine**: A mathematically normalized, zero-training deterministic hazard engine synthesizing morphological baseline risk, kinematic acceleration z-scores with trend bonuses, and thermal melt amplitudes.
3. **Live Environmental API Triggers**: Asynchronous real-time REST integration with the **USGS Earthquake Hazards** network and **Open-Meteo High-Resolution Weather** APIs for dynamic risk adjustment ($\delta_{\text{meteo}}, \delta_{\text{seismic}}$).
4. **Physical Hydrodynamic Routing Bridge**: An automated software translator converting critical AI alert breaches ($R_{\text{adjusted}} \ge 0.85$) directly into Voellmy-Salm rheological parameters and estimated discharge hydrographs ($Q_{\text{peak}} = v_{\text{recent}} \cdot R^2 \cdot 100$) for the **$r.avaflow$** two-phase mass flow solver.

---

## Key Innovations

- **Massive Cryospheric Preprocessing Pipeline**: Harmonized and consolidated **73,590,934** raw NASA ITS\_LIVE satellite feature-tracking observations down to **11,964,156** high-confidence daily records, incorporating cyclical harmonic ($\sin/\cos$) day and month encodings to preserve sub-annual seasonal ice acceleration phases.
- **CryoFormer (5.5M Transformer Encoder)**: Designed, trained, and benchmarked a 5.5M-parameter Transformer with learnable positional encodings, achieving a holdout test MAE of **20.54 m/yr** across global glacier regimes with an inference throughput of **8,600 predictions/sec** on GPU.
- **Zero-Training HydroFusion Engine**: Eliminated the overfitting trap of scarce classification labels by formulating an analytical hazard fusion equation ($R_{\text{base}} = 0.35M + 0.40K + 0.25T$) combining static morphometry ($M$), 7-day velocity acceleration z-scores with 14-day trend bonuses ($K$), and thermal melt amplitudes ($T$).
- **100% Historical Disaster Hindcast Accuracy**: Validated against landmark global disasters—including the **October 2023 South Lhonak disaster** (Sikkim, India; peak $R = 0.9412$), Dig Tsho (Nepal), Lake 513 (Peru), Luggye Tsho (Bhutan), and Shishper (Pakistan)—delivering actionable operational early warnings **4 to 8 days prior to dam breach**.
- **Low-Latency Production Stack**: Sub-5ms in-memory cached response times, 32.4ms neural inference latency, and full end-to-end telemetry resolution under 150ms served via an asynchronous FastAPI gateway and Next.js 15 command dashboard.

---

## System Architecture

```
                                  DATA ACQUISITION & INGESTION TIER
  ┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
  │  NASA ITS_LIVE (73.5M records)    High Mountain Asia Lake Inventory       Copernicus / ERA5     │
  │   - 120m/240m SAR Velocity Grids   - 30,000+ Lakes (prepared_dataset.csv)  - 2m Air Temperature  │
  └─────────────────┬───────────────────────────────┬───────────────────────────────┬───────────────┘
                    │                               │                               │
                    ▼                               ▼                               ▼
       [Daily Harmonic Cyclical]        [Morphological Feature Tuple]    [StandardScaler Normalizer]
       sin/cos(month), sin/cos(day)      Elevation, Area, Dam Distance     tempflow_features_scaler
                    │                               │                               │
  ══════════════════╪═══════════════════════════════╪═══════════════════════════════╪════════════════
                    ▼                               │                               ▼
      CRYOFORMER KINEMATIC MODEL                    │                  THERMOSEQ REGRESSOR
    ┌──────────────────────────────┐                │             ┌──────────────────────────────┐
    │ 5.5M Transformer Encoder     │                │             │ Multi-Layer Recurrent LSTM   │
    │  - 4 Layers, 8 MHSA Heads    │                │             │  - 30-Day Sliding History    │
    │  - Learnable Positional Emb  │                │             │  - Melt Fraction / Spikes    │
    │  - Holdout Test MAE: 20.5m/y │                │             │  - Scaled Feature Prediction │
    └──────────────┬───────────────┘                │             └──────────────┬───────────────┘
                   │                                │                            │
                   │ Kinematic Trajectory v(t)      │ Morphological Tuple m      │ Thermal Traj τ(t)
                   ▼                                ▼                            ▼
  ════════════════════════════════════════════════════════════════════════════════════════════════════
                             HYDROFUSION DETERMINISTIC HAZARD ENGINE
    ┌────────────────────────────────────────────────────────────────────────────────────────────┐
    │ Analytical Formulation: R_base = 0.35 * M + 0.40 * K(z_vel, m_trend) + 0.25 * T(f_melt, s)  │
    └──────────────────────────────────────────────┬─────────────────────────────────────────────┘
                                                   │
                        DYNAMIC ASYNCHRONOUS LIVE TELEMETRY HOOKS
           ┌───────────────────────────────────────┴───────────────────────────────────────┐
           ▼                                                                               ▼
   [Open-Meteo REST API]                                                           [USGS Hazards API]
   Ambient Temperature Trigger (δ_meteo: +0.03 to +0.08)                           M ≥ 2.5, r ≤ 200km (δ_seismic)
           └───────────────────────────────────────┬───────────────────────────────────────┘
                                                   │
                                                   ▼
                                       R_adjusted in [0.0, 1.0]
                   ┌───────────────────────────────┴───────────────────────────────┐
                   ▼                                                               ▼
        [Operational Severity Alert]                                   [Emergency Breach: R ≥ 0.85]
        Low (<0.35) | Med (0.35-0.60)                                              │
        High (0.60-0.80) | Critical (≥0.80)                                         ▼
                   │                                                   AUTOMATED r.avaflow BRIDGE
                   ▼                                                  ┌───────────────────────────────┐
       NEXT.JS 15 GIS DASHBOARD                                       │ Peak Discharge Q_peak Formula │
   - Interactive MapLibre GL 3D Map                                   │ Voellmy-Salm Parameter JSON   │
   - Turf.js Geospatial Hazard Buffers                                │ Direct Dispatch to GRASS GIS  │
   - Live Telemetry & Historical Replay                               └───────────────────────────────┘
```

---

## Scientific Foundations

### 1. CryoFormer: Cryospheric Kinematic Transformer

Glacial ice deformation obeys Glen's Flow Law ($\dot{\varepsilon} = A \tau^n$), exhibiting non-linear accelerations prior to terminal calving, structural detachment, or moraine shear collapse.

CryoFormer models a 32-day temporal window $\mathbf{X} \in \mathbb{R}^{32 \times 8}$ using a 4-layer Transformer Encoder:

$$\mathbf{H}_0 = \mathbf{X} \mathbf{W}_e + \mathbf{b}_e + \mathbf{P}_{1:L}$$

$$\mathbf{Q}_i = \mathbf{H}_{l-1} \mathbf{W}_i^Q, \quad \mathbf{K}_i = \mathbf{H}_{l-1} \mathbf{W}_i^K, \quad \mathbf{V}_i = \mathbf{H}_{l-1} \mathbf{W}_i^V$$

$$\text{head}_i = \text{Softmax}\left(\frac{\mathbf{Q}_i \mathbf{K}_i^T}{\sqrt{d_k}}\right) \mathbf{V}_i, \quad \text{MHSA}(\mathbf{H}_{l-1}) = [\text{head}_1 \,\|\, \dots \,\|\, \text{head}_h] \mathbf{W}^O$$

$$\hat{v}_{t+1} = \mathbf{h}_{4, 32} \mathbf{w}_{\text{fc}} + b_{\text{fc}}$$

| Parameter | Specification | Description |
| :--- | :--- | :--- |
| **Input Dimension ($d_{\text{in}}$)** | `8` | `[lon, lat, year, month_sin, month_cos, day_sin, day_cos, v_avg]` |
| **Model Dimension ($d_{\text{model}}$)** | `256` | Latent projection embedding space |
| **Attention Heads ($h$)** | `8` | Subspace head dimension $d_k = 32$ |
| **Encoder Layers ($N$)** | `4` | Pre-LayerNorm stack with GELU activations |
| **FFN Expansion ($d_{\text{ff}}$)** | `2048` | Intermediate feed-forward expansion ($8 \times d_{\text{model}}$) |
| **Total Parameters** | **`5,518,849`** | Exactly ~5.52M trainable weights |

### 2. ThermoSeq: Thermodynamic Sequence Regressor

ThermoSeq forecasts continuous 2-meter air temperature trajectories ($T_{2m}$ in $^\circ\text{C}$) over a 30-day sliding window, ingesting coordinates and harmonic temporal encodings through dual standardized feature scalers:

$$\tilde{\mathbf{u}}_t = \mathbf{\Sigma}_X^{-1/2} (\mathbf{u}_t - \mathbf{\mu}_X), \quad \tilde{y}_t = \frac{y_t - \mu_y}{\sigma_y}$$

The LSTM hidden state $\mathbf{h}_{30}$ autoregressively predicts 30-day thermal forcing, quantifying melt fraction ($f_{\text{melt}}$), peak thermal excursion spikes ($s_{\text{spike}}$), and differential warming rates ($s_{\text{warm}}$).

### 3. HydroFusion: Zero-Training Deterministic Hazard Engine

Due to extreme historical label sparsity ($< 0.1\%$ positive breach cases across 30,000+ lakes), unconstrained deep classification networks inevitably overfit. HydroFusion implements a physics-grounded deterministic fusion formulation:

$$R_{\text{base}} = \lambda_1 M + \lambda_2 K + \lambda_3 T \quad \left(\sum_{i=1}^3 \lambda_i = 1.0\right)$$

- **$\lambda_1 = 0.35$ (Morphological Score $M$):**
  $$M = 0.50 \cdot \min(1.0, 100 \cdot w_{\text{GLOF}}) + 0.25 \cdot \max\left(0, 1.0 - \frac{A_{\text{km}^2}}{50.0}\right) + 0.25 \cdot \min\left(1.0, \frac{E}{6000.0}\right) + \delta_{\text{hist}}$$
- **$\lambda_2 = 0.40$ (Kinematic Anomaly Score $K$):**
  Evaluates 7-day localized velocity acceleration relative to the 30-day baseline ($z_{\text{vel}} = \frac{\mu_{\text{recent}} - \mu_v}{\sigma_v}$):
  $$K_{\text{sig}} = \frac{1}{1 + \exp\left(-1.5 \cdot (z_{\text{vel}} - 1.0)\right)}$$
  $$K = \min\left(1.0, \, K_{\text{sig}} + \max\left(0, \min\left(0.20, \frac{m_{\text{trend}}}{0.10 \cdot \mu_v}\right)\right)\right)$$
- **$\lambda_3 = 0.25$ (Thermal Anomaly Score $T$):**
  $$T = 0.40 \cdot f_{\text{melt}} + 0.35 \cdot s_{\text{spike}} + 0.25 \cdot s_{\text{warm}}$$

### 4. Live Environmental REST Triggers

Dynamic adjustments are computed in real time without human intervention:

$$R_{\text{adjusted}} = \min\left(1.0, \, \max\left(0.0, \, R_{\text{base}} + \delta_{\text{meteo}} + \delta_{\text{seismic}}\right)\right)$$

- **Open-Meteo Ambient Thermal Trigger ($\delta_{\text{meteo}}$):**
  $$\delta_{\text{meteo}} = \min(0.08, \, 0.03 + \max(0, T_{\text{ambient}} - 1.0) \cdot 0.005)$$
- **USGS Seismic Proximity Trigger ($\delta_{\text{seismic}}$):**
  $$\delta_{\text{seismic}} = \min(0.10, \max(0, (M_{\max} - 2.5) \cdot 0.02)) \cdot \left(0.5 + 0.5 \cdot \max\left(0, 1 - \frac{d_{\min}}{200}\right)\right)$$

### 5. Automated $r.avaflow$ Hydrodynamic Bridge

When $R_{\text{adjusted}} \ge 0.85$, GLOFCast dynamically computes the peak breach discharge hydrograph:

$$Q_{\text{peak}} = v_{\text{recent}} \cdot (R_{\text{adjusted}})^2 \cdot 100 \quad \left[\text{m}^3/\text{s}\right]$$

and dispatches a structured Voellmy-Salm rheological parameter payload to the GRASS GIS numerical solver:

```json
{
  "engine": "r.avaflow",
  "version": "2.4",
  "flow_model": "Voellmy",
  "rheology": "Bingham",
  "resolution_m": 10,
  "time_steps": 3600,
  "manning_n": 0.04,
  "initial_conditions": {
    "v_ice_m_yr": 118.4,
    "T_surface_c": 3.2,
    "Q_peak_m3_s": 10486.2
  },
  "priority": "P0_CRITICAL",
  "actions": ["NOTIFY_DISASTER_MANAGEMENT", "ACTIVATE_DOWNSTREAM_SIRENS"]
}
```

---

## Historical Disaster Hindcast Benchmarks

To empirically validate operational reliability, GLOFCast was tested across historical 30-day pre-disaster hindcasts for documented global catastrophic breaches:

| Glacial Lake | Region / Country | Event Date | Elevation | Peak Score ($R$) | Early Warning Triggered | Lead Time |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **South Lhonak Lake** | Sikkim, India | 2023-10-04 | 5,200 m | **0.9412** | **YES** ($R \ge 0.85$) | **7 Days** |
| **Dig Tsho** | Khumbu, Nepal | 1985-08-04 | 4,366 m | **0.9120** | **YES** ($R \ge 0.85$) | **5 Days** |
| **Lake 513** | Cordillera Blanca, Peru | 2010-04-11 | 4,428 m | **0.8845** | **YES** ($R \ge 0.85$) | **4 Days** |
| **Luggye Tsho** | Punakha, Bhutan | 1994-10-07 | 4,540 m | **0.8970** | **YES** ($R \ge 0.85$) | **6 Days** |
| **Shishper Glacier** | Hunza, Pakistan | 2024-07-12 | 4,200 m | **0.8892** | **YES** ($R \ge 0.85$) | **8 Days** |

> **Hindcast Accuracy**: **100% detection rate** ($5/5$ benchmark disasters) with actionable operational lead times ranging between **4 and 8 days prior to catastrophic dam breach**.

---

## Empirical Benchmarks & Ablation Studies

### CryoFormer Training Convergence (30 Epochs on NVIDIA Tesla T4)

```
Epoch 01/30: Train Loss: 40.40 m/yr | Val Loss: 37.85 m/yr | Val MAE: 37.85 m/yr
Epoch 05/30: Train Loss: 28.04 m/yr | Val Loss: 24.83 m/yr | Val MAE: 24.83 m/yr
Epoch 10/30: Train Loss: 24.42 m/yr | Val Loss: 21.70 m/yr | Val MAE: 21.70 m/yr
Epoch 16/30: Train Loss: 22.83 m/yr | Val Loss: 20.36 m/yr | Val MAE: 20.36 m/yr
Epoch 23/30: Train Loss: 21.66 m/yr | Val Loss: 20.04 m/yr | Val MAE: 20.04 m/yr
Epoch 30/30: Train Loss: 21.43 m/yr | Val Loss: 20.05 m/yr | Val MAE: 20.05 m/yr
```

### Architectural Ablation Analysis

| Configuration | Parameters | Val Loss ($\text{m/yr}$) | Val MAE ($\text{m/yr}$) | Test MAE ($\text{m/yr}$) | Memory Overhead |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Baseline (3-dim input) | 2.50 M | 27.42 | 26.85 | 27.12 | Base |
| Shallow Transformer ($N=2, d=128$) | 1.25 M | 31.80 | 30.45 | 31.10 | -52% |
| Deep Transformer ($N=6, d=256$) | 8.15 M | 20.35 | 20.15 | 20.88 | +48% |
| **CryoFormer Proposed ($N=4, d=256$)** | **5.52 M** | **20.05** | **20.05** | **20.54** | **Optimal** |

### System Latency & Operational Throughput

| Pipeline Stage | Mean Latency | Execution Environment |
| :--- | :---: | :--- |
| **In-Memory Cache Hit** (`TTLCache`) | **4.8 ms** | Dual-tier retention (300s model / 600s APIs) |
| **Full Neural Inference** (Uncached) | **32.4 ms** | CryoFormer (PyTorch) + ThermoSeq (TensorFlow) |
| **Full Telemetry with Live REST APIs** | **148.6 ms** | Async Open-Meteo & USGS HTTPS querying |
| **Peak Operational Throughput** | **> 450 req/s** | Benchmark on single 4-core virtual instance |

---

## Interactive Command Dashboard

The frontend application (`src/glofcast-ui`) provides an operational GIS interface built with **Next.js 15**, **MapLibre GL**, **Turf.js**, and **Tailwind CSS v4**:

- **3D Satellite Terrain Mapping**: Vector tile visualization of High Mountain Asia glacier perimeters and proglacial lakes.
- **Dynamic Geospatial Hazard Buffers**: Automated geodesic calculation of 5km, 15km, and 30km downstream impact zones using Turf.js.
- **Multi-Signal Telemetry Inspector**: Real-time inspection of CryoFormer velocity acceleration charts, ThermoSeq temperature curves, and live weather/seismic adjustments.
- **Historical Hindcast Player**: Interactive simulation scrubber allowing disaster authorities to step through 30-day pre-disaster time windows for benchmark events.

---

## Repository Structure

```
.
├── Dockerfile.backend              # Production container recipe for FastAPI service
├── Dockerfile.frontend             # Multi-stage standalone build for Next.js 15 UI
├── docker-compose.yml              # Multi-container orchestration specification
├── .gitignore                      # Configured to guard credentials and large archives
├── README.md                       # Comprehensive framework documentation
├── src
│   ├── .devcontainer               # Reproducible VS Code DevContainer setup
│   ├── .gitattributes              # Git LFS & line ending normalization
│   ├── LICENSE                     # MIT License
│   ├── prepared_dataset.csv        # Consolidated High Mountain Asia lake inventory
│   ├── GLOFCast_Model_Training_Pipeline.ipynb  # End-to-end training notebook
│   │
│   ├── backend                     # FastAPI Asynchronous Service Tier
│   │   ├── main.py                 # REST application entrypoint & routing endpoints
│   │   ├── hydrofusion.py          # Zero-training HydroFusion deterministic hazard engine
│   │   ├── riskflow.py             # Backward-compatibility alias
│   │   ├── model_registry.py       # Singleton PyTorch & TensorFlow model lifecycle manager
│   │   ├── historical_glof.py      # Benchmark disaster validation & hindcasting suite
│   │   ├── schemas.py              # Pydantic data schemas & response contracts
│   │   └── requirements.txt        # Backend Python dependencies
│   │
│   ├── models                      # Neural Checkpoints & Scikit-Learn Scalers
│   │   ├── cryoformer-5.5M.pth     # CryoFormer 5.5M-parameter Transformer weights
│   │   ├── terraflow-5.5M.pth      # Kinematic baseline model checkpoint
│   │   ├── best_tempflow_model1.keras # Calibrated TempFlow model
│   │   ├── best_thermoseq_model1.keras# Finalized ThermoSeq LSTM weights
│   │   ├── tempflow.h5             # Intermediate thermodynamic weights
│   │   ├── tempflow_features_scaler.save # Input feature normalization scaler
│   │   ├── tempflow_temp_scaler.save     # Temperature target scaler
│   │   ├── thermoseq_features_scaler.save# ThermoSeq multi-feature scaler
│   │   └── thermoseq_temp_scaler.save    # ThermoSeq target scaler
│   │
│   ├── notebooks                   # Architectural Experimentation & Ablation Studies
│   │   ├── terraflow-new.ipynb     # Transformer encoder kinematics training
│   │   ├── terraflow_19M.ipynb     # 19M-parameter capacity ablation notebook
│   │   └── tempflow.ipynb          # Thermodynamic LSTM sequence training
│   │
│   ├── scripts                     # Visualizations & Report Generators
│   │   ├── generate_comparison_chart.py # Script for model performance charts
│   │   ├── generate_segmentation_overlay.py # Satellite mask processing
│   │   ├── create_pdf.py           # Automated PDF summary generator
│   │   ├── comparison_chart.png    # Benchmark visualization asset
│   │   └── segmentation_overlay.png# Cryospheric segmentation overlay asset
│   │
│   ├── glofcast-ui                 # Next.js 15 Command Dashboard
│   │   ├── src/app                 # Next.js App Router (layout, globals.css, page.tsx)
│   │   ├── src/components/map      # MapLibre GL geospatial glacier map component
│   │   ├── src/components/panels   # RiskPanel, HistoricalValidationPanel, LeftPanel
│   │   ├── src/lib                 # REST API client, Turf.js generators, mock data
│   │   └── package.json            # Node.js dependencies
│   │
│   └── Docs                        # Academic Thesis & Documentation
│       ├── PresentationSlides.txt  # Project presentation URL
│       └── BTech_Latex_Report      # Complete B.Tech Thesis in LaTeX
│           ├── thesis.tex          # Monograph source document (692 lines)
│           ├── references.bib      # Comprehensive academic bibliography
│           └── mnnit.cls           # MNNIT Allahabad thesis document class
```

---

## Quickstart & Deployment

### Prerequisites

- **Python**: `3.10` or `3.11`
- **Node.js**: `>= 20.0.0` (with `pnpm` or `npm`)
- **Docker & Docker Compose**: Recommended for production deployment
- **GPU (Optional)**: NVIDIA GPU with CUDA 12.x for accelerated neural inference (runs on CPU automatically if CUDA is unavailable)

---

### Option 1: One-Click Docker Compose Deployment (Recommended)

Clone the repository and spin up both the FastAPI backend and Next.js frontend:

```bash
git clone https://github.com/Arpit-Shukla-20233080/GLOFCast.git
cd GLOFCast

# Build and launch all containerized services
docker-compose up --build -d
```

- **Interactive Command Dashboard**: `http://localhost:3000`
- **FastAPI OpenAPI Swagger Documentation**: `http://localhost:8000/docs`
- **Backend Health Check**: `http://localhost:8000/api/health`

---

### Option 2: Local Manual Setup

#### 1. Backend Service Setup

```bash
cd src/backend

# Create and activate Python virtual environment
python -m venv venv
source venv/bin/activate       # On Windows: .\venv\Scripts\Activate.ps1

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Start FastAPI application with auto-reloading
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

#### 2. Frontend Dashboard Setup

```bash
cd src/glofcast-ui

# Install dependencies
npm install

# Start development server
npm run dev
```

Visit `http://localhost:3000` in your browser.

---

## API Specification

The FastAPI backend exposes fully documented asynchronous endpoints with interactive OpenAPI docs available at `/docs`:

### Core Endpoints

#### 1. Get Lakes Inventory
```http
GET /api/lakes?limit=50&offset=0
```
Returns a paginated list of cataloged glacial lakes across High Mountain Asia with coordinates, surface area, and morphological risk scores.

#### 2. Comprehensive Hazard Telemetry
```http
POST /api/predict
Content-Type: application/json

{
  "lake_id": "GL_HMA_002341",
  "coordinates": {
    "latitude": 27.9167,
    "longitude": 88.2167
  },
  "include_live_apis": true
}
```
**Response Sample**:
```json
{
  "lake_id": "GL_HMA_002341",
  "scores": {
    "morphological": 0.912,
    "kinematic": 0.954,
    "thermal": 0.842,
    "base_risk": 0.9113,
    "adjusted_risk": 0.9412
  },
  "alert_tier": "CRITICAL",
  "live_adjustments": {
    "meteo_delta": 0.03,
    "seismic_delta": 0.00
  },
  "cryoformer_velocity_m_yr": 118.4,
  "hydrodynamic_bridge_triggered": true,
  "estimated_peak_discharge_m3_s": 10486.2,
  "execution_time_ms": 32.4
}
```

#### 3. Historical Disaster Replay
```http
GET /api/historical/south_lhonak_2023?day_offset=-7
```
Replays telemetry frames evaluated 7 days prior to the South Lhonak dam breach, demonstrating the exact pre-disaster signal triggers.

---

## Citation & Academic Reference

This framework was formulated, implemented, and submitted as an undergraduate B.Tech. thesis at **Motilal Nehru National Institute of Technology (MNNIT) Allahabad, Prayagraj, India**.

If you utilize GLOFCast, CryoFormer, or HydroFusion in your research or production early warning systems, please cite:

```bibtex
@btechthesis{shukla2026glofcast,
  author    = {Shukla, Arpit},
  title     = {GLOFCast: A Multimodal Deep Learning Framework for Glacial Lake Outburst Flood Early Warning},
  school    = {Department of Computer Science and Engineering, Motilal Nehru National Institute of Technology Allahabad},
  address   = {Prayagraj, Uttar Pradesh, India},
  year      = {2026},
  month     = {October},
  supervisor= {Thakur, Dr. Deevansh},
  type      = {Bachelor of Technology Thesis}
}
```

---

## Acknowledgments & Data Sources

- **NASA Jet Propulsion Laboratory (JPL)**: For the [ITS\_LIVE](https://its-live.jpl.nasa.gov/) Inter-mission Time Series of Land Ice Velocity and Elevation archives.
- **USGS Earthquake Hazards Program**: For real-time seismic REST API feeds.
- **Open-Meteo**: For high-resolution numerical weather prediction REST APIs.
- **Department of Computer Science & Engineering, MNNIT Allahabad**: For high-performance computing facilities and academic mentorship under **Dr. Deevansh Thakur**.

---

<div align="center">
Developed with ❤️ by <a href="https://github.com/Arpit-Shukla-20233080">Arpit Shukla</a> & Team • Released under the MIT License
</div>
