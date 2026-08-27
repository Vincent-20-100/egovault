# Visual Decision Tree (Chart Selection Guide with Heuristics)

A decision guide helping data analysts and LLMs select the most statistically accurate, cognitively direct visual encoding based on analytical intent and observed data structure.

---

## 🧭 Analytical Intent Matrix

| Analytical Intent | Default Visualization | Alternative / Nuance | When to Avoid |
| :--- | :--- | :--- | :--- |
| **Compare & Rank categories** | **Horizontal sorted bar chart** | Lollipop chart, Dumbbell plot | Vertical bars with rotated labels; 3D bars; arbitrary unordered bars |
| **Track change over time** | **Line chart** | Small multiples grid, Sparklines | Line charts for unordered categorical data; spaghetti plots with $>5$ unweighted lines |
| **Compare two states (Before/After, Target/Actual)** | **Dumbbell (DNA) plot or Slope chart** | Bullet graph | Multi-clustered grouped bars with $>3$ series |
| **Inspect distribution (1 numeric)** | **Calibrated Histogram** (Freedman-Diaconis) | Strip plot + Jitter (small $N$), Boxplot | Arbitrary bin count; raw pie charts |
| **Compare distributions ($N$ groups)** | **Boxplot or Violin plot** | Ridge plot (Joyplot) if $>5$ categories/periods | Bare bar charts with mean $\pm$ SE that hide multimodality |
| **Investigate relationship (2 variables)** | **Scatter plot** | Hexbin / 2D Density if overplotting occurs | 3D scatter plots; unreflective trendlines when relationship is non-linear |
| **Correlation matrix / pairwise table** | **Heatmap** | Clustered heatmap *only when proximity structure is analytical* | Indiscriminate clustering when chronological/hierarchical order has inherent meaning |
| **Part-to-whole / Composition** | **Waffle chart or Donut** (max 4 slices) | Treemap (if $>4$ slices or hierarchical) | Pie charts with $>5$ slices; 3D pie charts |
| **Flows, journeys & drop-offs** | **Sankey diagram or Funnel chart** | Alluvial diagram | Disconnected separate bar charts |
| **Variance / P&L decomposition** | **Waterfall chart** | Range / Band chart | Raw tables of numbers |

---

## 🔬 Critical Heuristics & Nuances

### 1. Scatter Plots & Overplotting
* **Trendlines**: Never add an OLS or LOWESS line mechanically. Add a trendline **only if the analytical question specifically concerns the statistical relationship**, and explicitly display the method and confidence interval (e.g. 95% CI).
* **Overplotting Management**: 200 points with identical integer values can overlap completely, while 1,000 continuous points can be well dispersed. Inspect real point density:
  * Slight overlap $\rightarrow$ Adjust alpha transparency (`alpha=0.2` to `0.5`).
  * Discrete/integer overlap $\rightarrow$ Add jittering (`sns.stripplot(jitter=True)`).
  * High-density saturation $\rightarrow$ Switch to **Hexbin** (`plt.hexbin(..., gridsize=30)`) or **2D KDE Contour** (`sns.kdeplot(fill=True)`).

### 2. Heatmaps & Hierarchical Clustering
* **Natural Order vs Clustered Order**:
  * If rows/columns represent time (e.g. month $\times$ day), geographic regions, or domain hierarchies (e.g. seniority levels), **preserve the natural order**. Clustering would destroy the chronological or structural narrative.
  * Use hierarchical clustering (`sns.clustermap`) **only when grouping similar variables by mathematical proximity provides the primary analytical insight**.

### 3. Bar Charts & Baseline
* **Base 0 Rule**: Bar charts encode value through height/length; truncating the baseline distorts perceptual proportions.
* **Exceptions**: An offset baseline is permissible only when scientifically justified (e.g. index base 100, temperature anomalies around a $0^\circ\text{C}$ baseline, or physiological metrics within an active range) — provided the baseline and offset are prominently marked and labeled.

### 4. Distributions & Asymmetry
* **Skewness & Transformations**: Inspect skewness carefully. Envisage log, Box-Cox, or Yeo-Johnson transformations **only if it genuinely improves interpretation and is statistically justified** (do not apply log automatically).
* Prefer median and interquartile range (IQR) to arithmetic mean/std when reporting central tendency on skewed distributions.
