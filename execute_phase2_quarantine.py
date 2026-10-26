"""
GLOFCast Refactoring Workflow - Phase 2: Quarantine & Reorganization
====================================================================
Safely isolates legacy, incriminating, and duplicate artifacts into `_legacy_archive`.
"""

import os
import shutil
from pathlib import Path

# Base directories
REPO_ROOT = Path(r"c:\Users\arpit\Downloads\GLOFCast-Forecasting-Catastrophe-using-AI-main (3)\GLOFCast-Forecasting-Catastrophe-using-AI-main")
PARENT_DIR = REPO_ROOT.parent
ARCHIVE_ROOT = REPO_ROOT / "_legacy_archive"

def safe_move(src_path: Path, dst_dir: Path):
    """Safely moves a file or directory into a destination directory."""
    if not src_path.exists():
        print(f"[-] Skip (not found): {src_path.name}")
        return
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst_path = dst_dir / src_path.name
    if dst_path.exists():
        if dst_path.is_dir():
            shutil.rmtree(dst_path)
        else:
            dst_path.unlink()
    shutil.move(str(src_path), str(dst_path))
    print(f"[+] Quarantined: {src_path.name} -> {dst_dir.relative_to(REPO_ROOT)}")

def run_phase_2():
    print("=" * 70)
    print("PHASE 2: SAFE RESTRUCTURING & ARTIFACT QUARANTINE")
    print("=" * 70)
    
    # 1. Initialize Archive Folders
    docs_archive = ARCHIVE_ROOT / "docs"
    zips_archive = ARCHIVE_ROOT / "zips"
    legacy_ui_archive = ARCHIVE_ROOT / "legacy_ui"
    duplicates_archive = ARCHIVE_ROOT / "duplicates"
    latex_artifacts = ARCHIVE_ROOT / "latex_artifacts"

    # 2. Quarantine Incriminating Project Files
    incriminating_files = [
        REPO_ROOT / "src" / "Docs" / "GLOFCast Report.pdf",
        REPO_ROOT / "src" / "Docs" / "AI Plagiarism Report.pdf",
        REPO_ROOT / "src" / "Docs" / "Plagiarism Report GLOFCast Report.pdf",
        REPO_ROOT / "src" / "Docs" / "GLOFCast_Demo.mp4",
        REPO_ROOT / "src" / "Docs" / "Poster.pdf",
        REPO_ROOT / "src" / "Docs" / "BTech_Latex_Report.zip",
        REPO_ROOT / "src" / "Docs" / "PROJECT_STATUS_AND_ROADMAP_REPORT.md",
        REPO_ROOT / "src" / "scripts" / "GLOFCast_Progress_Report.pdf",
        REPO_ROOT / "src" / "scripts" / "glofcast_progress_report.html",
    ]
    for file_path in incriminating_files:
        safe_move(file_path, docs_archive)

    # 3. Quarantine External Zip Archives
    zip_files = [
        PARENT_DIR / "GLOFCast-Forecasting-Catastrophe-using-AI-main.zip",
        REPO_ROOT / "GLOFCast-Forecasting-Catastrophe-using-AI-main.zip"
    ]
    for zip_path in zip_files:
        safe_move(zip_path, zips_archive)

    # 4. Quarantine Duplicate Root Markdown Report
    safe_move(REPO_ROOT / "PROJECT_STATUS_AND_ROADMAP_REPORT.md", duplicates_archive)

    # 5. Quarantine Duplicate Docker / Compose Files in `src/`
    duplicate_docker_files = [
        REPO_ROOT / "src" / "docker-compose.yml",
        REPO_ROOT / "src" / "Dockerfile.backend",
        REPO_ROOT / "src" / "Dockerfile.frontend",
    ]
    for d_path in duplicate_docker_files:
        safe_move(d_path, duplicates_archive)

    # 6. Quarantine Inactive Streamlit Dashboard
    safe_move(REPO_ROOT / "src" / "dashboard", legacy_ui_archive)

    # 7. Clean BTech_Latex_Report Artifacts (Retain only .tex, .bib, .cls)
    latex_dir = REPO_ROOT / "src" / "Docs" / "BTech_Latex_Report"
    essential_latex = {"thesis.tex", "references.bib", "mnnit.cls"}
    if latex_dir.exists():
        for item in list(latex_dir.iterdir()):
            if item.is_file() and item.name not in essential_latex:
                safe_move(item, latex_artifacts)

    # 8. Professional Notebook Rename
    messy_notebook = REPO_ROOT / "src" / "glof_6 (1).ipynb"
    clean_notebook = REPO_ROOT / "src" / "GLOFCast_Model_Training_Pipeline.ipynb"
    if messy_notebook.exists():
        messy_notebook.rename(clean_notebook)
        print(f"[+] Polished Notebook: {messy_notebook.name} -> {clean_notebook.name}")

    # 9. Rename UI folder from `glofcast-ui` to `glofcast-ui`
    old_ui = REPO_ROOT / "src" / "glofcast-ui"
    new_ui = REPO_ROOT / "src" / "glofcast-ui"
    if old_ui.exists():
        old_ui.rename(new_ui)
        print(f"[+] Upgraded Frontend Directory: {old_ui.name} -> {new_ui.name}")

    print("\n[SUCCESS] Phase 2 quarantine and restructuring completed cleanly.")

if __name__ == "__main__":
    run_phase_2()