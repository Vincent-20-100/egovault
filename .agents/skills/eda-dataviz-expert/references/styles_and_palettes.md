# Styling Presets, Modular Palettes & Domain Conventions

This reference defines typographic, chromatic, and aesthetic standards across the 3 visual systems, as well as rules for mapping existing corporate/BI design systems.

---

## 🎨 Context Precedence & Palette Mapping

Before selecting any colors, follow the priority rule:
1. **Existing Project Palette (Power BI theme, Brand Guidelines, CSS Tokens)** $\longrightarrow$ **Always map existing colors to roles; never impose foreign hex codes**.
2. **Explicit User Directives** $\longrightarrow$ Follow prompt instructions.
3. **Greenfield Fallback** $\longrightarrow$ Use built-in presets below (`editorial`, `scientific`, `dark`).

### 🔄 Mapping an Existing Corporate / Power BI Palette
When working in an existing project, do NOT use the preset hex codes. Map the client's colors to the functional roles:

```
┌─────────────────┬─────────────────────────────────────────────────────────────┐
│ Functional Role │ How to assign in an existing project / Power BI report      │
├─────────────────┼─────────────────────────────────────────────────────────────┤
│ 1. Canvas / BG  │ Existing report background (e.g. #FFFFFF or custom cream)   │
│ 2. Neutral/Base │ Brand slate / light gray for unselected / baseline data     │
│ 3. Secondary    │ Muted brand secondary tint for comparative series           │
│ 4. Primary      │ Main corporate brand color (e.g. Brand Navy, Teal, Indigo)  │
│ 5. Accent       │ High-contrast corporate alert/callout color (e.g. Coral)    │
└─────────────────┴─────────────────────────────────────────────────────────────┘
```

---

## 🔗 Cross-Chart Semantic Consistency & Scope Coding

### 1. Entity & Feature Color Invariance
* If a category or feature appears across multiple charts (e.g., *"Segment B"*, *"Product Category X"*), **bind it to the exact same color throughout the entire project**.
* Never allow automatic color cycling to assign different colors to the same entity on adjacent charts.

### 2. Scope & Granularity Signatures
* When comparing different analytical granularities across charts:
  * **Benchmark / Total / Global Average** $\longrightarrow$ Neutral / Slate tone (`COLOR_NEUTRAL`).
  * **Focus Group / Top 100 / Selected Cohort** $\longrightarrow$ Dominant Signal hue (`COLOR_PRIMARY` or `COLOR_ACCENT`).

---

## 🎭 The 3 Visual Systems (Greenfield Presets)

```
scientific   → Color = Pure Data Encoding (precision, perceptual uniformity, zero bias)
editorial    → Color = Data Encoding + Visual Storytelling (attention hierarchy, spotlight, context)
dark         → Color = Data Encoding + UI Hierarchy (calibrated luminance, contrast without visual halo)
```

> **Attention Maxim**: *« A bright color means **“Look here!”**, not merely “Category B”. »*

---

### 1. Preset: `editorial` (Default Fallback — Contemporary Editorial / Data Journalism)
* **Goal**: Refined, executive-ready analytical visualization that is easy on the eyes.
* **Background**: `#FAF8F2` (Soft cream) or `#F7F4ED`
* **Text / Ink**: `#222222` (Near black)
* **Typography**:
  * Titles & Subtitles: `Georgia` (fallback: `DejaVu Serif`, `Times New Roman`)
  * Axes, Ticks, Labels, Annotations: `Helvetica` (fallback: `Arial`, `DejaVu Sans`)
* **Grid**: Subtle horizontal lines (`#E2E8F0`, linestyle=`--`, alpha=0.7)
* **Spines**: Remove top and right spines (`spines.top=False`, `spines.right=False`)

### 2. Preset: `scientific` (Academic Publishing & Reproducibility)
* **Goal**: Maximum precision and compliance with Nature, Science, IEEE, Cell guidelines.
* **Background**: `#FFFFFF` (Pure white)
* **Text / Ink**: `#000000` (Solid black)
* **Typography**: 100% Sans-serif (`Helvetica` / `Arial` / `DejaVu Sans`) across all elements (no serif).
* **Export Standards**: **Vector PDF/SVG export whenever possible**; **300 DPI minimum for raster exports (PNG/TIFF)**.

### 3. Preset: `dark` (Tech / Observability / Dashboards)
* **Goal**: Modern dark mode for operations dashboards, command centers, and presentations.
* **Background**: `#0F172A` (Dark Navy) or `#18181B` (Anthracite)
* **Text / Ink**: `#F1F5F9` (Off-white)
* **Typography**: Sans-serif for data/axes; optional serif for major headlines.
* **Contrast & Anti-Halo**:
  * Verify text/background and color/background contrast.
  * Avoid oversaturated colors that cause visual halo (*chromostereopsis*) or eye strain on dark screens.
* **Grid**: Very subtle gridlines (`#1E293B` at low opacity).

---

## 🎨 Modular Color Architecture (Fallback Palettes)

```mermaid
graph TD
    BG[1. Background : Cream #FAF8F2 / White / Dark Navy] --> N[2. Neutral / Greys : Context, history, baseline]
    N --> S[3. Secondary : Comparative series / lighter tint]
    S --> P[4. Primary : Dominant domain hue]
    P --> A[5. Accent : Critical point, anomaly, target]
```

### Dominant Family Palettes (Plug into Primary/Secondary for Greenfield):

```python
PALETTES = {
    "blues": {
        "primary": "#1D4ED8",
        "secondary": "#93C5FD",
        "accent": "#DC2626", # Crimson callout
        "neutral": "#94A3B8"
    },
    "oranges": {
        "primary": "#EA580C",
        "secondary": "#FDBA74",
        "accent": "#1E3A8A", # Deep navy callout
        "neutral": "#94A3B8"
    },
    "greens": {
        "primary": "#059669",
        "secondary": "#A7F3D0",
        "accent": "#B91C1C", # Red callout
        "neutral": "#94A3B8"
    },
    "reds": {
        "primary": "#DC2626",
        "secondary": "#FCA5A5",
        "accent": "#1E3A8A", # Navy callout
        "neutral": "#94A3B8"
    },
    "greys": { # Minimalist / Spotlight theme
        "primary": "#334155",
        "secondary": "#CBD5E1",
        "accent": "#EA580C", # Vibrant orange focal pop
        "neutral": "#94A3B8"
    }
}
```

---

## 🔬 Mathematical Palette Families

### 1. Qualitative / Categorical (Nominal Categories)
* **Use when**: Categories have no inherent numerical order.
* **Rules**: Max 5-7 distinct colors simultaneously. Ensure cross-chart consistency for same categories.
* **Palettes**:
  * `Okabe-Ito` (Colorblind-Safe Standard): `["#000000", "#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7"]`
  * `Set2`, `tab10`.

### 2. Sequential (Continuous Low $\rightarrow$ High)
* **Use when**: Values represent continuous magnitude, intensity, or volume.
* **Rules**: Must be **perceptually uniform** (equal steps in data correspond to equal steps in perceived brightness).
* **Palettes**: `viridis`, `cividis`, `magma`, `plasma` (or monochromatic `Blues`, `Greens`, `YlOrRd`).
* *Accessibility Note*: `cividis` is specifically designed to remain perceptually uniform across complete red-green and blue-yellow color vision deficiencies.

> [!IMPORTANT]
> **Key Scientific Distinction**: *Colorblind-safe does not automatically mean perceptually uniform.*  
> Okabe-Ito is colorblind-safe for *categorical* data, but is NOT a continuous colormap. Use Viridis/Cividis for continuous quantitative scales.

### 3. Diverging (Centered Around a Neutral Pivot)
* **Use when**: Data has a meaningful center point (Zero, Mean, Target, Baseline).
* **Rules**: **Mandatory central neutral value**. Never use on strictly positive data without a pivot. Always verify contrast and accessibility against the background.
* **Palettes**: `coolwarm`, `RdBu`, `PuOr`, `Spectral` (with explicit center).

---

## 📐 Robust Multi-OS Font Detection

```python
import matplotlib.font_manager as fm

def get_available_font(preferred_list, fallback="sans-serif"):
    available = {f.name for f in fm.fontManager.ttflist}
    for font in preferred_list:
        if font in available:
            return font
    return fallback

FONT_TITLE = get_available_font(["Georgia", "DejaVu Serif", "Times New Roman"], fallback="serif")
FONT_BODY = get_available_font(["Helvetica", "Arial", "DejaVu Sans"], fallback="sans-serif")
```

---

## 🔢 Numerical Hygiene & Locale Format Reference

### 1. The Zero-Scientific-Notation Rule
Scientific notation (`1.2e+06`, `2e-03`) is strictly banned on charts outside physical science research.
Always ensure Matplotlib axes do not generate scientific offsets:

```python
ax.ticklabel_format(style="plain", useOffset=False)
```

### 2. Formatter Implementation Patterns

```python
import matplotlib.ticker as ticker

# Anglo-Saxon Formatter (US / UK: $1.2M, 450k, 12.5%)
def fmt_us_currency(x, _):
    if abs(x) >= 1e9: return f"${x*1e-9:.1f}B".replace(".0B", "B")
    if abs(x) >= 1e6: return f"${x*1e-6:.1f}M".replace(".0M", "M")
    if abs(x) >= 1e3: return f"${x*1e-3:.0f}k"
    return f"${x:,.0f}"

# European / French Formatter (FR / EU: 1,2 M €, 450 k €, 12,5 %)
def fmt_eu_currency(x, _):
    if abs(x) >= 1e9: return f"{x*1e-9:.1f} Md €".replace(".0 Md", " Md").replace(".", ",")
    if abs(x) >= 1e6: return f"{x*1e-6:.1f} M €".replace(".0 M", " M").replace(".", ",")
    if abs(x) >= 1e3: return f"{x*1e-3:.0f} k €"
    return f"{x:,.0f} €".replace(",", " ")

# Percentage Formatter
def fmt_percent(x, _):
    return f"{x*100:.1f}%".replace(".0%", "%") # If input is ratio 0-1
```

### 3. Power BI / DAX Format String Reference

| Metric Type | Anglo-Saxon (`en-US`) | European / French (`fr-FR`) |
| :--- | :--- | :--- |
| **Millions Currency** | `$#,##0.0,, "M"` or `$#,##0,, "M"` | `#,##0.0,, "M €"` or `#,##0,, "M €"` |
| **Thousands Currency** | `$#,##0.0, "k"` or `$#,##0, "k"` | `#,##0.0, "k €"` or `#,##0, "k €"` |
| **Billions Currency** | `$#,##0.0,,, "B"` | `#,##0.0,,, "Md €"` |
| **Standard Number** | `#,##0` | `#,##0` *(Power BI applies space separator based on locale)* |
| **Percentage** | `0.0%` or `0%` | `0,0 %` or `0 %` |

