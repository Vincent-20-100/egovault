# Data Visualization Library Matrix & Code Patterns

A comprehensive evaluation of visualization libraries across Python and JavaScript, emphasizing the `Seaborn = default` hierarchy, performance caps, and production-ready code patterns.

---

## 📊 Comprehensive Comparison Matrix

| Library | Eco | Paradigm | Best For | Output Format | Volume Cap | Interactivity |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Seaborn (v0.13+) [DEFAULT]** | Python | High-level Statistical | Rapid statistical EDA, distributions, regressions, boxplots | PNG, SVG, PDF | ~100k rows | None (Static) |
| **Plotly Express** | Python / JS | High-level Declarative / Object | Web dashboards, Streamlit apps, tooltips, zoom/pan, Geo | HTML, WebGL, PNG | ~50k rows (SVG)<br>~1M rows (`scattergl`) | Native Interactive |
| **Altair / Vega-Lite** | Python | Declarative Grammar of Graphics | Reproducible JSON specs, linked crossfiltering views | HTML, Vega JSON, SVG | ~5k rows (unbinned)<br>Unlimited (pre-aggregated) | Declarative Interactive |
| **Matplotlib** | Python | Low-level Imperative | Custom publication layouts, micro-adjustments, custom axes | PNG, SVG, PDF | ~500k rows | None (Static) |
| **Apache ECharts** | JS / TS | Declarative Config | Enterprise web dashboards, high data throughput | Canvas, SVG, WebGL | >1M points | Exceptional |
| **Observable Plot / D3** | JS / Web | Functional Grammar / Custom DOM | Editorial storytelling, bespoke interactive web visualisations | SVG, Canvas | >500k points | Full Custom |

---

## 💻 Idiomatic Code Templates (Preset: `basic_custom`)

### 1. Seaborn + Matplotlib (Horizontal Bar Chart with Direct Labeling)

```python
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
import pandas as pd

# 1. Global Setup & Robust Font Resolution
FIGSIZE = (14, 7)
COLOR_BG = "#FAF8F2"
COLOR_TEXT = "#222222"

def get_available_font(preferred_list, fallback="sans-serif"):
    available = {f.name for f in fm.fontManager.ttflist}
    for font in preferred_list:
        if font in available:
            return font
    return fallback

FONT_TITLE = get_available_font(["Georgia", "DejaVu Serif", "Times New Roman"], fallback="serif")
FONT_BODY = get_available_font(["Helvetica", "Arial", "DejaVu Sans"], fallback="sans-serif")

# 2. Data Preparation & Sorting
data = df.groupby("segment")["revenue"].sum().sort_values(ascending=True)

# 3. Hierarchy Palette (Context Grays + Primary/Accent Highlight)
colors = ["#CBD5E1" if x != data.max() else "#EA580C" for x in data]

fig, ax = plt.subplots(figsize=FIGSIZE, facecolor=COLOR_BG)
ax.set_facecolor(COLOR_BG)

bars = ax.barh(data.index, data.values, color=colors, height=0.65)

# 4. Direct Value Annotations on Bars
for bar in bars:
    width = bar.get_width()
    ax.text(
        width + (data.max() * 0.01),
        bar.get_y() + bar.get_height() / 2,
        f"${width:,.0f}",
        va="center",
        ha="left",
        fontsize=10,
        fontfamily=FONT_BODY,
        fontweight="bold" if width == data.max() else "normal",
        color=COLOR_TEXT
    )

# 5. Clean Tufte Layout (No top/right spines, subtle reading grid)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.spines["left"].set_color("#CBD5E1")
ax.spines["bottom"].set_visible(False)
ax.xaxis.grid(True, linestyle="--", alpha=0.6, color="#E2E8F0")
ax.set_axisbelow(True)
ax.set_xticks([]) # Direct labeling eliminates redundant X ticks

# 6. Action Title & Subtitle Hierarchy
ax.set_title("Enterprise Tier Drives 62% of Recognized Q3 Revenue",
             fontsize=15, fontweight="bold", fontfamily=FONT_TITLE, loc="left", color=COLOR_TEXT, pad=15)
ax.text(0, 1.02, "Total recognized revenue by customer segment (USD in thousands)",
        transform=ax.transAxes, fontsize=11, fontfamily=FONT_TITLE, color="#64748B")

plt.tight_layout()
plt.show()
```

---

### 2. Plotly Express (Interactive Web & Dashboards)

```python
import plotly.express as px

fig = px.scatter(
    df,
    x="ad_spend",
    y="conversions",
    size="user_base",
    color="campaign_type",
    hover_name="campaign_name",
    template="plotly_white",
    color_discrete_sequence=["#1D4ED8", "#EA580C", "#059669", "#94A3B8"],
    title="<b>Paid Search Drives Highest Conversion Efficiency</b><br>"
          "<span style='font-size:12px; color:#64748B;'>Ad spend vs total conversions with user volume sizing</span>"
)

fig.update_layout(
    font_family="Helvetica, Arial, sans-serif",
    paper_bgcolor="#FAF8F2",
    plot_bgcolor="#FAF8F2",
    title_x=0.02,
    margin=dict(l=40, r=40, t=80, b=40),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)
fig.update_xaxes(showgrid=True, gridcolor="#E2E8F0", zeroline=False)
fig.update_yaxes(showgrid=True, gridcolor="#E2E8F0", zeroline=False)
```
