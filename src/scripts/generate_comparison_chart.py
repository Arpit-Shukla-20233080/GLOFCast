"""
GLOFCast — Baseline vs. Proposed Architecture: Comparative Performance Bar Chart
================================================================================
Generates a publication-quality grouped bar chart comparing classification
metrics (Accuracy, Precision, Recall, F1-Score) between the Baseline
(CNN + XGBoost) and Proposed (CryoFormer + ThermoSeq) architectures.

Output: comparison_chart.png (300 DPI, journal-ready)
"""

import matplotlib.pyplot as plt
import matplotlib
import numpy as np

# Use non-interactive backend for script execution
matplotlib.use('Agg')

# ─── Mock Evaluation Metrics ────────────────────────────────────────────────
# These values represent expected performance based on architectural analysis.
# Replace with actual evaluation results when available.

metrics = ['Accuracy', 'Precision', 'Recall', 'F1-Score']

baseline_scores = [0.782, 0.801, 0.714, 0.755]   # CNN + XGBoost
proposed_scores = [0.891, 0.903, 0.837, 0.869]    # CryoFormer + ThermoSeq

# ─── Chart Configuration ────────────────────────────────────────────────────

# Academic color palette
COLOR_BASELINE = '#6B7280'    # Neutral grey
COLOR_PROPOSED = '#0455BF'    # GLOFCast primary blue
COLOR_BG = '#FAFAFA'

fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
fig.patch.set_facecolor(COLOR_BG)
ax.set_facecolor(COLOR_BG)

x = np.arange(len(metrics))
bar_width = 0.32

# Draw bars
bars_baseline = ax.bar(
    x - bar_width / 2, baseline_scores, bar_width,
    label='Baseline (CNN + XGBoost)',
    color=COLOR_BASELINE, edgecolor='white', linewidth=0.8,
    zorder=3
)
bars_proposed = ax.bar(
    x + bar_width / 2, proposed_scores, bar_width,
    label='Proposed (CryoFormer + ThermoSeq)',
    color=COLOR_PROPOSED, edgecolor='white', linewidth=0.8,
    zorder=3
)

# ─── Value Labels ────────────────────────────────────────────────────────────

def add_value_labels(bars, color='#333333'):
    for bar in bars:
        height = bar.get_height()
        ax.annotate(
            f'{height:.3f}',
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 6),
            textcoords='offset points',
            ha='center', va='bottom',
            fontsize=9, fontweight='600', color=color,
            fontfamily='sans-serif'
        )

add_value_labels(bars_baseline, '#4B5563')
add_value_labels(bars_proposed, '#1E3A5F')

# ─── Improvement Annotations ────────────────────────────────────────────────

for i, (b, p) in enumerate(zip(baseline_scores, proposed_scores)):
    improvement = (p - b) * 100
    ax.annotate(
        f'+{improvement:.1f}%',
        xy=(x[i] + bar_width / 2, p),
        xytext=(28, 16),
        textcoords='offset points',
        ha='center', va='bottom',
        fontsize=8, fontweight='bold', color='#059669',
        fontfamily='sans-serif',
        arrowprops=dict(arrowstyle='->', color='#059669', lw=1.2)
    )

# ─── Axes & Labels ──────────────────────────────────────────────────────────

ax.set_xlabel('Evaluation Metric', fontsize=12, fontweight='600',
              fontfamily='sans-serif', labelpad=12)
ax.set_ylabel('Score', fontsize=12, fontweight='600',
              fontfamily='sans-serif', labelpad=12)
ax.set_title(
    'Model Performance Comparison: Baseline vs. Proposed Architecture',
    fontsize=14, fontweight='700', fontfamily='sans-serif', pad=20
)

ax.set_xticks(x)
ax.set_xticklabels(metrics, fontsize=11, fontfamily='sans-serif')
ax.set_ylim(0.55, 1.02)
ax.set_yticks(np.arange(0.55, 1.05, 0.05))
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'{v:.2f}'))
ax.tick_params(axis='y', labelsize=9)

# Grid
ax.grid(axis='y', linestyle='--', alpha=0.3, zorder=0)
ax.set_axisbelow(True)

# Spine styling
for spine in ['top', 'right']:
    ax.spines[spine].set_visible(False)
for spine in ['bottom', 'left']:
    ax.spines[spine].set_color('#D1D5DB')
    ax.spines[spine].set_linewidth(0.8)

# Legend
ax.legend(
    loc='upper left', frameon=True, framealpha=0.9,
    edgecolor='#E5E7EB', fontsize=10, fancybox=True,
    borderpad=0.8
)

# ─── Save ────────────────────────────────────────────────────────────────────

plt.tight_layout()
output_path = 'comparison_chart.png'
fig.savefig(output_path, dpi=300, bbox_inches='tight',
            facecolor=COLOR_BG, edgecolor='none')
print(f"[OK] Chart saved to: {output_path}")
plt.close()
