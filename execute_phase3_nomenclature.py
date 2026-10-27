"""
GLOFCast Refactoring Workflow - Phase 3: Nomenclature Refactoring
==================================================================
Globally replaces legacy terms with the finalized thesis nomenclature:
  * GLOFCast   -> GLOFCast
  * CryoFormer  -> CryoFormer
  * ThermoSeq   -> ThermoSeq
  * HydroFusion   -> HydroFusion
"""

import os
from pathlib import Path

REPO_ROOT = Path(r"c:\Users\arpit\Downloads\GLOFCast-Forecasting-Catastrophe-using-AI-main (3)\GLOFCast-Forecasting-Catastrophe-using-AI-main")

# Target replacement mappings across code, comments, and schemas
EXACT_REPLACEMENTS = [
    # PascalCase / Proper Nouns
    ("GLOFCast", "GLOFCast"),
    ("CryoFormer", "CryoFormer"),
    ("ThermoSeq", "ThermoSeq"),
    ("HydroFusion", "HydroFusion"),
    
    # lowercase identifiers
    ("glofcast", "glofcast"),
    ("cryoformer", "cryoformer"),
    ("thermoseq", "thermoseq"),
    ("hydrofusion", "hydrofusion"),
    
    # UPPERCASE identifiers
    ("GLOFCAST", "GLOFCAST"),
    ("CRYOFORMER", "CRYOFORMER"),
    ("THERMOSEQ", "THERMOSEQ"),
    ("HYDROFUSION", "HYDROFUSION"),
    
    # Model Identifier strings in schemas/logs
    ("CryoFormer-5.5M", "CryoFormer-5.5M"),
    ("ThermoSeq-LSTM", "ThermoSeq-LSTM"),
    ("HydroFusion-Engine", "HydroFusion-Engine"),
]

# File extensions subject to refactoring
TARGET_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".json", 
    ".md", ".yml", ".yaml", ".env", ".toml", "Dockerfile"
}

# Directories to strictly exclude
EXCLUDED_DIRS = {
    ".git", ".next", "node_modules", "venv", "__pycache__", 
    "_legacy_archive", ".devcontainer"
}

def refactor_file(file_path: Path) -> int:
    """Reads a file, applies replacements, and writes back if modified."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception as e:
        print(f"[-] Could not read {file_path}: {e}")
        return 0

    original_content = content
    changes_count = 0

    for old_str, new_str in EXACT_REPLACEMENTS:
        if old_str in content:
            count = content.count(old_str)
            content = content.replace(old_str, new_str)
            changes_count += count

    # Add descriptive systems engineering docstrings if backend module
    if file_path.name == "hydrofusion.py" or file_path.name == "hydrofusion.py":
        content = content.replace(
            "Deterministic Fusion Engine",
            "HydroFusion: Zero-Training Deterministic Hazard Fusion Engine"
        )
    elif file_path.name == "model_registry.py":
        content = content.replace(
            "Transformer Regressor for Ice Velocity Prediction",
            "CryoFormer: 5.5M-Parameter Cryospheric Kinematics Transformer Encoder"
        )

    if content != original_content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[+] Refactored ({changes_count} changes): {file_path.relative_to(REPO_ROOT)}")
        return changes_count
    return 0

def run_phase_3():
    print("=" * 70)
    print("PHASE 3: GLOBAL NOMENCLATURE REFACTORING")
    print("=" * 70)

    # 1. Update backend module filename: hydrofusion.py -> hydrofusion.py (with backward-compatible bridge)
    backend_dir = REPO_ROOT / "src" / "backend"
    old_hydrofusion = backend_dir / "hydrofusion.py"
    new_hydrofusion = backend_dir / "hydrofusion.py"
    if old_hydrofusion.exists() and not new_hydrofusion.exists():
        old_hydrofusion.rename(new_hydrofusion)
        print(f"[+] Renamed Module: hydrofusion.py -> hydrofusion.py")
        
        # Create a shim for backward compatibility if any legacy import lingers
        with open(old_hydrofusion, "w", encoding="utf-8") as f:
            f.write("# Backward-compatibility alias for GLOFCast HydroFusion\nfrom hydrofusion import *\n")

    # 2. Iterate and update all active files
    total_files_updated = 0
    total_replacements = 0

    for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
        # Prune excluded directories in-place
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]
        
        for filename in filenames:
            file_path = Path(dirpath) / filename
            if file_path.suffix in TARGET_EXTENSIONS or filename in {"Dockerfile", "Dockerfile.backend", "Dockerfile.frontend"}:
                replaced = refactor_file(file_path)
                if replaced > 0:
                    total_files_updated += 1
                    total_replacements += replaced

    print("\n" + "=" * 70)
    print(f"[SUCCESS] Global refactoring complete: {total_replacements} substitutions across {total_files_updated} files.")
    print("=" * 70)

if __name__ == "__main__":
    run_phase_3()