#!/usr/bin/env python3
"""
PCI Chart Generator — replicates the YoY PCE Inflation chart
from 01a-YoY-PCE.png using data in 01a-YoY-PCE.csv.
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
from datetime import datetime

# ── Paths ──────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(SCRIPT_DIR, "01a-YoY-PCE.csv")
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "pci_chart_output.png")

# ── Load & pivot data ─────────────────────────────────────────────────
df = pd.read_csv(CSV_PATH)
df["date"] = pd.to_datetime(df["date"])

headline = df[df["key"] == "YoY_pce_headline"].sort_values("date")
core = df[df["key"] == "YoY_pce_core"].sort_values("date")

# ── Colour palette (matched to the reference image) ───────────────────
COLOR_HEADLINE = "#1F3864"      # dark navy blue
COLOR_CORE = "#7B8B2E"          # olive / dark yellow-green
COLOR_RECESSION = "#D9D9D9"     # light grey recession shading
COLOR_TARGET = "#000000"        # black dashed 2 % target line

# ── Chart dimensions & styling ────────────────────────────────────────
fig, ax = plt.subplots(figsize=(15.5, 7.0))
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

# Line widths matched to the reference image (~2.5 pt)
LINE_WIDTH = 2.5

# Plot the two series
ax.plot(headline["date"], headline["value"], color=COLOR_HEADLINE,
        linewidth=LINE_WIDTH, label="Headline", zorder=3)
ax.plot(core["date"], core["value"], color=COLOR_CORE,
        linewidth=LINE_WIDTH, label="Core", zorder=3)

# ── 2 % target line (dashed) ─────────────────────────────────────────
ax.axhline(y=2.0, color=COLOR_TARGET, linewidth=1.2, linestyle="--", zorder=2)

# ── Recession bar (approx. Feb 2020 – Apr 2020) ──────────────────────
rec_start = datetime(2020, 2, 1)
rec_end = datetime(2020, 4, 30)
ax.axvspan(rec_start, rec_end, color=COLOR_RECESSION, alpha=0.9, zorder=1)

# ── Y-axis formatting ────────────────────────────────────────────────
ax.set_ylim(0, 8)
ax.yaxis.set_major_locator(mticker.MultipleLocator(1))
ax.yaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))
ax.tick_params(axis="y", labelsize=13, length=0)

# ── X-axis formatting ────────────────────────────────────────────────
ax.set_xlim(datetime(2019, 1, 1), datetime(2026, 1, 1))
ax.xaxis.set_major_locator(mdates.YearLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
ax.tick_params(axis="x", labelsize=13, length=0)

# ── Grid & spines ────────────────────────────────────────────────────
ax.grid(axis="y", color="#E0E0E0", linewidth=0.6, zorder=0)
ax.grid(axis="x", visible=False)
for spine in ax.spines.values():
    spine.set_visible(False)

# ── Inline series labels (positioned where the reference shows them) ─
ax.text(datetime(2021, 1, 1), 5.55, "Headline",
        fontsize=14, fontweight="bold", color=COLOR_HEADLINE, zorder=5)
ax.text(datetime(2021, 6, 1), 4.0, "Core",
        fontsize=14, fontweight="bold", color=COLOR_CORE, zorder=5)

# ── Summary table in the lower-right corner ──────────────────────────
#  Compute the values shown in the table
headline_oct = headline[headline["date"] == "2025-10-01"]["value"].values[0]
headline_nov = headline[headline["date"] == "2025-11-01"]["value"].values[0]
core_oct = core[core["date"] == "2025-10-01"]["value"].values[0]
core_nov = core[core["date"] == "2025-11-01"]["value"].values[0]

headline_chg = round((headline_nov - headline_oct) * 100)  # basis points
core_chg = round((core_nov - core_oct) * 100)

# Table location (axes coordinates)
table_x = 0.98   # near right edge
table_y = 0.06   # near bottom

col_headers = ["", "Oct 2025", "Nov 2025", "Chg."]
row1 = ["Headline", f"{headline_oct:.2f}%", f"{headline_nov:.2f}%",
        f"{abs(headline_chg)} b.p."]
row2 = ["Core", f"{core_oct:.2f}%", f"{core_nov:.2f}%",
        f"{abs(core_chg)} b.p."]

table = ax.table(
    cellText=[col_headers, row1, row2],
    loc="lower right",
    bbox=[0.64, 0.02, 0.35, 0.18],   # [left, bottom, width, height]
    edges="open",
)

# Style header row
for j in range(4):
    cell = table[0, j]
    cell.set_text_props(fontweight="bold", fontsize=12, color="#333333",
                        ha="right")
    cell.set_facecolor("white")
    cell.set_edgecolor("white")

# Style data rows
for i, row_color in enumerate([COLOR_HEADLINE, COLOR_CORE], start=1):
    for j in range(4):
        cell = table[i, j]
        cell.set_facecolor("white")
        cell.set_edgecolor("white")
        if j == 0:
            cell.set_text_props(fontweight="bold", fontsize=12,
                                color=row_color, ha="left")
        else:
            cell.set_text_props(fontweight="bold", fontsize=12,
                                color=row_color, ha="right")

# ── End-of-line labels ("2.8%") ──────────────────────────────────────
last_headline = headline.iloc[-1]
last_core = core.iloc[-1]

ax.text(last_headline["date"] + pd.Timedelta(days=12),
        last_headline["value"] + 0.05, f'{last_headline["value"]:.1f}%',
        fontsize=11, fontweight="bold", color=COLOR_HEADLINE, va="center")
ax.text(last_core["date"] + pd.Timedelta(days=12),
        last_core["value"] - 0.05, f'{last_core["value"]:.1f}%',
        fontsize=11, fontweight="bold", color=COLOR_CORE, va="center")

# ── Save ──────────────────────────────────────────────────────────────
plt.tight_layout()
fig.savefig(OUTPUT_PATH, dpi=150, bbox_inches="tight", facecolor="white")
print(f"Chart saved to {OUTPUT_PATH}")
plt.show()
