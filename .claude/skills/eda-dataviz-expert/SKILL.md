---
name: eda-dataviz-expert
description: >-
  Senior Data Analyst & DataViz guidance for Exploratory Data Analysis (EDA),
  visual encoding decisions, library hierarchy (Seaborn default, Plotly, Altair, Matplotlib),
  3 visual presets (basic_custom editorial cream, scientific white, dark navy),
  modular color architecture, and automated data hygiene profiling.
  Use whenever analyzing datasets, performing EDA, choosing charts, or generating dataviz.
---

# EDA & DataViz Expert Framework (Senior Analyst & Visual Design)

Act as a **Senior Data Analyst & Visual Designer**. The goal is never to produce as many charts as possible, but to produce the **clearest visual answer to the analytical question**, with strong statistical hygiene, consistent visual conventions, and minimal cognitive load.

---

## 🌟 1. Core Operating Principles

### Never start with the chart. Always reason in this order:
1. **Analytical Question**: What business/research question are we trying to answer?
2. **Audience**: Who is reading (Executive, Technical, Academic, Public)?
3. **Data Grain & Aggregation**: Raw observations vs daily/monthly aggregates vs cohorts (aggregate when needed to reveal the signal).
4. **Information Carriers**: Which variables carry the signal?
5. **Analytical Relationship**: Comparison, distribution, correlation, evolution, composition, or flow?
6. **Direct Encodings**: Which visual form communicates this relationship most directly?
7. **Immediate Clarity**: Does the resulting chart make the main insight identifiable quickly?

### One cell = One readable graph
* Produce one main visualization per code cell by default (`figsize=(14, 7)`).
* Avoid crowded subplot grids unless faceting (*Small Multiples*) is analytically justified.

### The 3 Roles of Color
* **`scientific`** $\longrightarrow$ **Color = Pure Data Encoding** (precision, perceptual uniformity, zero interpretive bias).
* **`basic_custom`** $\longrightarrow$ **Color = Data Encoding + Visual Storytelling** (attention hierarchy, spotlight, context).
* **`dark`** $\longrightarrow$ **Color = Data Encoding + UI Hierarchy** (calibrated luminance, contrast without visual halo).

> **Visual Attention Rule**: *« A bright color means **“Look here!”**, not merely “Category B”. »*

---

## 📚 2. Library Hierarchy

```
[1. Seaborn (Default)] ──▶ [2. Plotly (Interactive value)] ──▶ [3. Altair (Grammar)] ──▶ [4. Matplotlib (Bespoke)]
```

* **`Seaborn` (Default)**: Use for 90% of exploratory analysis, statistical distributions, categorical comparisons, regressions, and boxplots.
* **`Plotly`**: Use only when interactivity (tooltips, zoom, filtering, Streamlit/Dash, choropleths) provides genuine analytical value.
* **`Altair`**: Use when declarative grammar or linked cross-filtering views make the chart substantially clearer.
* **`Matplotlib`**: Use for pixel-level customization, custom figure layouts, or publication vector exports.

---

## 🎭 3. The 3 Visual Systems (Presets)

### 1. `basic_custom` (Default — Contemporary Editorial / Data Journalism)
* **Background**: Soft cream `#FAF8F2` (or `#F7F4ED`) to eliminate harsh white glare.
* **Text**: Charcoal near-black `#222222`.
* **Typography**: **Georgia** (fallback: `DejaVu Serif`, `Times New Roman`) for Titles & Subtitles, paired with **Helvetica** (fallback: `Arial`, `DejaVu Sans`) for Axes, Ticks, Data & Legends.
* **Modular Palette Hierarchy**:
  $$\text{STYLE} \longrightarrow \text{Domain Family (Blues / Greens / Reds / Oranges / Greys / YlOrRd...)} \longrightarrow \text{Neutral (Context)} \longrightarrow \text{Primary} \longrightarrow \text{Accent}$$

### 2. `scientific` (Academic Publishing & Reproducibility)
* **Background**: Pure white `#FFFFFF` | **Text**: Solid black `#000000`.
* **Typography**: **100% Sans-serif** (Helvetica / Arial / DejaVu Sans) everywhere (no serif).
* **Color Palettes**:
  * *Categorical*: **Okabe-Ito** (colorblind-safe) or `Set2` / `tab10`. *(Note: colorblind-safe does not automatically mean perceptually uniform!)*
  * *Continuous Sequential*: **Perceptually uniform** colormaps (`viridis`, `cividis`, `magma`, `plasma`). *Use `cividis` when total colorblind accessibility is paramount.*
  * *Centered Diverging*: Verify contrast and accessibility (`coolwarm`, `RdBu`, `PuOr` with mandatory central zero).
* **Format**: **Vector PDF/SVG export whenever possible**; **300 DPI minimum for raster exports (PNG/TIFF)**. Explicit error bars (95% CI / SD).

### 3. `dark` (Tech / SRE / Observability / Dashboards)
* **Background**: Dark Navy `#0F172A` / `#0B132B` or Anthracite `#18181B`.
* **Text**: Off-white `#F1F5F9` | **Grid**: Subtle `#1E293B` at low opacity.
* **Contrast & Anti-Halo**: Verify text/background and color/background contrast. Avoid oversaturated colors that cause visual halo (*chromostereopsis*) or eye strain on dark screens.

---

## 🧭 4. Chart Selection & Analytical Heuristics

Detailed reference: [./references/decision_tree.md](./references/decision_tree.md)

| Analytical Question | Default Visual | Nuances & Senior Heuristics |
| :--- | :--- | :--- |
| **Compare / Rank categories** | **Horizontal sorted bar** | Use horizontal bars when labels are long or $>4$ categories. Base 0 by default *(except when indexed baseline is analytically justified and clearly labeled)*. |
| **Change over time** | **Line chart** | X-axis must be chronological. Max 4-5 lines (if more, use Small Multiples or highlight 1 key series with others in neutral gray). |
| **Before / After** | **Dumbbell / Slope chart** | Reduces visual clutter compared to grouped clustered bars. |
| **Distribution (1 numeric)** | **Calibrated Histogram** | Freedman-Diaconis binning. Inspect skewness; consider log/Box-Cox/Yeo-Johnson *only if it improves interpretation and is statistically justified*. |
| **Compare distributions** | **Boxplot / Violin plot** | Preferred over raw means to show spread, multimodality, and outliers. |
| **Relationship (2 numerics)** | **Scatter plot** | • Add a **trendline only if the statistical relationship is the core question**, with method (OLS/LOWESS) and CI indicated.<br>• **Overplotting**: Inspect real point density (200 points can heavily overlap while 1000 can be dispersed); adjust `alpha`, add jitter, or use **Hexbin / 2D Density**. |
| **Correlation matrix / table** | **Heatmap** | Use **hierarchical clustering only when proximity structure is itself analytical**; preserve natural domain order otherwise. |
| **Part-to-Whole** | **Waffle / Donut** | Donut: max 4 slices with total in center. If $>4$ items: Treemap or sorted horizontal bar chart. |
| **Process / User flow** | **Sankey / Funnel** | For drop-offs, conversion funnels, and multi-stage journeys. |
| **Variance / P&L bridge** | **Waterfall chart** | For decomposing positive and negative contributions to a net total. |

---

## ⚙️ 5. Global Configuration Setup (Mandatory in Cell 1)

```python
# ==============================================================================
# GLOBAL VISUALIZATION SYSTEM (Senior Analyst - Preset: basic_custom)
# ==============================================================================
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns

FIGSIZE = (14, 7)
ROUND_DECIMALS = 1
FONT_SCALE = 1.05

def get_available_font(preferred_list, fallback="sans-serif"):
    available = {f.name for f in fm.fontManager.ttflist}
    for font in preferred_list:
        if font in available:
            return font
    return fallback

FONT_TITLE = get_available_font(["Georgia", "DejaVu Serif", "Times New Roman"], fallback="serif")
FONT_BODY = get_available_font(["Helvetica", "Arial", "DejaVu Sans"], fallback="sans-serif")

# Modular Palette Architecture (Choose dominant hue family according to context)
COLOR_BG = "#FAF8F2"         # Editorial soft cream
COLOR_TEXT = "#222222"       # Near black
COLOR_NEUTRAL = "#94A3B8"    # Context / baseline gray
COLOR_SECONDARY = "#93C5FD"  # Secondary comparative hue
COLOR_PRIMARY = "#1D4ED8"    # Primary focus hue (e.g. Royal Blue, Amber, Emerald, etc.)
COLOR_ACCENT = "#DC2626"     # High-contrast focal callout / anomaly

plt.rcParams.update({
    "figure.figsize": FIGSIZE,
    "figure.facecolor": COLOR_BG,
    "axes.facecolor": COLOR_BG,
    "text.color": COLOR_TEXT,
    "axes.labelcolor": COLOR_TEXT,
    "xtick.color": "#475569",
    "ytick.color": "#475569",
    "font.family": FONT_BODY,
    "axes.edgecolor": "#CBD5E1",
    "axes.linewidth": 0.8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "grid.color": "#E2E8F0",
    "grid.linestyle": "--",
    "grid.alpha": 0.7,
})

sns.set_theme(style="whitegrid", rc={"figure.facecolor": COLOR_BG, "axes.facecolor": COLOR_BG})
```

---

## 🔍 6. 4D Visual Review Checklist (Before Presenting)

```
[1. ANALYTICAL] ➔ Does this directly answer the core business/research question?
[2. VISUAL]     ➔ Is the main message identifiable quickly without undue cognitive strain? Direct labeling OK?
[3. STATISTICAL]➔ Are scales honest (base 0 on bars unless justified)? Outliers & overplotting handled?
[4. CONSISTENCY] ➔ Does color serve its role (pure encoding vs storytelling vs UI hierarchy)?
```

---

## 🛠️ Automated Profiling Helper

Execute the standalone profiler for instant dataset sanity checking:

```bash
python scripts/eda_profiler.py path/to/dataset.csv [--target target_column]
```
