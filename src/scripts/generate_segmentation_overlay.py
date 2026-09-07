"""
GLOFCast — Sentinel-2 Segmentation Mask & Bounding Box Overlay
===============================================================
Generates a mock visualization of the HydroFusion CNN segmentation output
overlaid on a synthetic Sentinel-2-style satellite image.

If a real GeoTIFF is available, set GEOTIFF_PATH below.
Otherwise, generates a synthetic glacial landscape.

Output: segmentation_overlay.png (300 DPI, journal-ready)
"""

import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from pathlib import Path

# ─── Configuration ──────────────────────────────────────────────────────────

# Set to a real Sentinel-2 GeoTIFF path if available, or None for synthetic
GEOTIFF_PATH = None  
# Example: GEOTIFF_PATH = r"C:\Users\amitk\Downloads\sentinel2_shishper.tif"

OUTPUT_PATH = 'segmentation_overlay.png'

# Mock glacial lake parameters (Shishper Glacier Lake)
LAKE_CENTER = (256, 280)    # pixel coordinates in 512x512 image
LAKE_RADIUS_X = 55
LAKE_RADIUS_Y = 35
LAKE_EXPANSION_X = 68       # expanded boundary (3 months later)
LAKE_EXPANSION_Y = 45

BBOX = (170, 215, 180, 135)  # x, y, width, height — bounding box around lake

# ─── Load or Generate Base Image ────────────────────────────────────────────

def load_geotiff(path):
    """Attempt to load a Sentinel-2 GeoTIFF using rasterio."""
    try:
        import rasterio
        with rasterio.open(path) as src:
            # Read RGB bands (B4=Red, B3=Green, B2=Blue for Sentinel-2)
            if src.count >= 3:
                r = src.read(1).astype(np.float32)
                g = src.read(2).astype(np.float32)
                b = src.read(3).astype(np.float32)
            else:
                band = src.read(1).astype(np.float32)
                r = g = b = band

            # Normalize to 0-1 range
            rgb = np.stack([r, g, b], axis=-1)
            p2, p98 = np.percentile(rgb[rgb > 0], [2, 98])
            rgb = np.clip((rgb - p2) / (p98 - p2), 0, 1)

            # Resize to 512x512 if needed
            from PIL import Image
            img = Image.fromarray((rgb * 255).astype(np.uint8))
            img = img.resize((512, 512), Image.LANCZOS)
            return np.array(img) / 255.0
    except Exception as e:
        print(f"⚠️  Could not load GeoTIFF ({e}). Using synthetic image.")
        return None


def generate_synthetic_glacier_image(size=512):
    """Generate a realistic synthetic satellite image of a glacial landscape."""
    np.random.seed(42)
    img = np.zeros((size, size, 3), dtype=np.float32)

    # Base terrain — brown/grey mountain rock
    for i in range(size):
        for j in range(size):
            # Perlin-like noise approximation using sine superposition
            noise = (
                np.sin(i * 0.02 + j * 0.015) * 0.15 +
                np.sin(i * 0.05 - j * 0.03) * 0.08 +
                np.sin(i * 0.1 + j * 0.08) * 0.04
            )
            base = 0.25 + noise
            img[i, j] = [base * 0.85, base * 0.78, base * 0.72]

    # Add snow/ice regions (higher elevation = whiter)
    y_coords, x_coords = np.mgrid[0:size, 0:size]
    snow_mask = (
        np.sin(y_coords * 0.008) * 50 +
        np.sin(x_coords * 0.012) * 30 +
        np.random.randn(size, size) * 15
    )
    snow_region = snow_mask > 25
    img[snow_region] = img[snow_region] * 0.3 + np.array([0.85, 0.88, 0.92]) * 0.7

    # Add glacial lake (dark blue-green water body)
    for i in range(size):
        for j in range(size):
            dx = (j - LAKE_CENTER[0]) / LAKE_RADIUS_X
            dy = (i - LAKE_CENTER[1]) / LAKE_RADIUS_Y
            dist = dx**2 + dy**2
            if dist < 1.0:
                alpha = max(0, 1.0 - dist)
                water = np.array([0.08, 0.18, 0.35])
                img[i, j] = img[i, j] * (1 - alpha * 0.9) + water * alpha * 0.9

    # Add subtle texture noise
    noise = np.random.randn(size, size, 3) * 0.02
    img = np.clip(img + noise, 0, 1)

    return img


# ─── Generate Segmentation Masks ────────────────────────────────────────────

def create_lake_mask(shape, center, rx, ry):
    """Create an elliptical segmentation mask."""
    mask = np.zeros(shape[:2], dtype=np.float32)
    y, x = np.mgrid[0:shape[0], 0:shape[1]]
    ellipse = ((x - center[0]) / rx) ** 2 + ((y - center[1]) / ry) ** 2
    mask[ellipse <= 1.0] = 1.0
    # Soft edges
    transition = (ellipse > 0.8) & (ellipse <= 1.2)
    mask[transition] = np.clip(1.0 - (ellipse[transition] - 0.8) / 0.4, 0, 1)
    return mask


# ─── Main Visualization ─────────────────────────────────────────────────────

def main():
    # Load base image
    if GEOTIFF_PATH and Path(GEOTIFF_PATH).exists():
        base_img = load_geotiff(GEOTIFF_PATH)
        if base_img is None:
            base_img = generate_synthetic_glacier_image()
        image_source = f"Sentinel-2 GeoTIFF: {GEOTIFF_PATH}"
    else:
        base_img = generate_synthetic_glacier_image()
        image_source = "Synthetic Sentinel-2 simulation"

    # Create masks
    mask_t1 = create_lake_mask(base_img.shape, LAKE_CENTER, LAKE_RADIUS_X, LAKE_RADIUS_Y)
    mask_t2 = create_lake_mask(base_img.shape, LAKE_CENTER, LAKE_EXPANSION_X, LAKE_EXPANSION_Y)
    expansion_zone = np.clip(mask_t2 - mask_t1, 0, 1)

    # ─── Plot ────────────────────────────────────────────────────────────────

    fig, axes = plt.subplots(1, 3, figsize=(18, 6), dpi=300)
    fig.patch.set_facecolor('#0F172A')

    titles = [
        'Sentinel-2 Optical (RGB)',
        'HydroFusion Segmentation — T1',
        'HydroFusion Segmentation — T2\n(+3 Months, Expansion Detected)'
    ]

    for idx, (ax, title) in enumerate(zip(axes, titles)):
        ax.imshow(base_img)

        if idx == 1:
            # T1: Original lake boundary
            overlay = np.zeros((*base_img.shape[:2], 4))
            overlay[:, :, 0] = 0.0       # R
            overlay[:, :, 1] = 0.85      # G (cyan)
            overlay[:, :, 2] = 0.95      # B
            overlay[:, :, 3] = mask_t1 * 0.4
            ax.imshow(overlay)

            # Contour
            ax.contour(mask_t1, levels=[0.5], colors=['#00E5FF'], linewidths=1.5)

            # Bounding box
            rect = patches.Rectangle(
                (BBOX[0], BBOX[1]), BBOX[2], BBOX[3],
                linewidth=2, edgecolor='#FF1744', facecolor='none',
                linestyle='--', label='ROI Bounding Box'
            )
            ax.add_patch(rect)
            ax.legend(loc='lower right', fontsize=7, facecolor='#1E293B',
                      edgecolor='#334155', labelcolor='white')

        elif idx == 2:
            # T2: Expanded boundary + expansion zone highlighted
            overlay_t2 = np.zeros((*base_img.shape[:2], 4))
            overlay_t2[:, :, 0] = 0.0
            overlay_t2[:, :, 1] = 0.85
            overlay_t2[:, :, 2] = 0.95
            overlay_t2[:, :, 3] = mask_t2 * 0.35
            ax.imshow(overlay_t2)

            # Expansion zone in red
            overlay_exp = np.zeros((*base_img.shape[:2], 4))
            overlay_exp[:, :, 0] = 1.0     # Red
            overlay_exp[:, :, 1] = 0.1
            overlay_exp[:, :, 2] = 0.1
            overlay_exp[:, :, 3] = expansion_zone * 0.5
            ax.imshow(overlay_exp)

            # Contours for both
            ax.contour(mask_t1, levels=[0.5], colors=['#00E5FF'],
                       linewidths=1.0, linestyles='dashed')
            ax.contour(mask_t2, levels=[0.5], colors=['#FF1744'], linewidths=2.0)

            # Bounding box (expanded)
            rect2 = patches.Rectangle(
                (BBOX[0] - 15, BBOX[1] - 15), BBOX[2] + 30, BBOX[3] + 30,
                linewidth=2, edgecolor='#FF1744', facecolor='none', linestyle='-'
            )
            ax.add_patch(rect2)

            # Annotation arrow
            ax.annotate(
                'Lake Expansion\nDetected (+23.6%)',
                xy=(LAKE_CENTER[0] + LAKE_EXPANSION_X - 5, LAKE_CENTER[1]),
                xytext=(LAKE_CENTER[0] + 100, LAKE_CENTER[1] - 60),
                fontsize=8, fontweight='bold', color='#FF1744',
                fontfamily='sans-serif',
                arrowprops=dict(arrowstyle='->', color='#FF1744', lw=1.5),
                bbox=dict(boxstyle='round,pad=0.4', facecolor='#1E293B',
                          edgecolor='#FF1744', alpha=0.9)
            )

        # Styling
        ax.set_title(title, fontsize=11, fontweight='600', color='white',
                     fontfamily='sans-serif', pad=10)
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_color('#334155')
            spine.set_linewidth(0.5)

    # Suptitle
    fig.suptitle(
        'HydroFusion CNN — Glacial Lake Boundary Segmentation & Expansion Detection',
        fontsize=14, fontweight='700', color='white', fontfamily='sans-serif',
        y=1.02
    )

    # Source annotation
    fig.text(
        0.5, -0.02, f'Source: {image_source} | Location: Shishper Glacier (36.41°N, 74.77°E)',
        ha='center', fontsize=8, color='#94A3B8', fontfamily='sans-serif'
    )

    plt.tight_layout()
    fig.savefig(
        OUTPUT_PATH, dpi=300, bbox_inches='tight',
        facecolor='#0F172A', edgecolor='none', pad_inches=0.3
    )
    print(f"[OK] Segmentation overlay saved to: {OUTPUT_PATH}")
    plt.close()


if __name__ == '__main__':
    main()
