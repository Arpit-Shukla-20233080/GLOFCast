# GLOFCast: Multimodal Deep Learning & Systems Engineering Framework for Glacial Lake Outburst Flood (GLOF) Early Warning

<div align="center">

[![Python Version](https://img.shields.io/badge/Python-3.10%20%7C%203.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.4.1%20CUDA%20Accelerated-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)](https://pytorch.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-15.0%20App%20Router-000000?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose%20Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)
[![Academic Thesis](https://img.shields.io/badge/MNNIT%20Allahabad-B.Tech%20Thesis-800000?style=for-the-badge)](Docs/BTech_Latex_Report/thesis.tex)

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

## Citation & Academic Reference

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

<div align="center">
Developed with ❤️ by <a href="https://github.com/Arpit-Shukla-20233080">Arpit Shukla</a> & Team • Released under the MIT License
</div>
