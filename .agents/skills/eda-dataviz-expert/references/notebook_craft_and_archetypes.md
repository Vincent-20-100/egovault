# Notebook Craft & The 3 Archetypes (`notebook_craft_and_archetypes.md`)

> **Guiding Philosophy**: *« A notebook is not a dumping ground for unstructured exploratory code. It is an engineering narrative whose structure must match its purpose: fast hypothesis testing, stakeholder decision support, or reactive application. »*

---

## 🧭 The 3 Notebook Archetypes

Before writing a notebook, identify its archetype to set the right depth, code visibility, and polish:

```
                     What is the primary objective of this notebook?
                                            │
             ┌──────────────────────────────┼──────────────────────────────┐
             ▼                              ▼                              ▼
┌────────────────────────────┐ ┌────────────────────────────┐ ┌────────────────────────────┐
│ 1. EXPLORATORY SCRATCHPAD  │ │ 2. DECISION SHOWCASE / DEMO│ │ 3. REACTIVE APP (MARIMO)   │
│    (Research / Tier 0)     │ │    (Deliverable / Tier 1/2)│ │    (Interactive Dashboard) │
├────────────────────────────┤ ├────────────────────────────┤ ├────────────────────────────┤
│ • Fast hypothesis testing  │ • Shared with peers/execs    │ • Pure Python (`.py` format) │
│ • Raw code cells visible   │ • Imports logic from `src/`  │ • Reactive DAG state graph   │
│ • Intermediate data checks │ • Focus on charts & decisions│ • Interactive widget sliders │
│ • Short-lived or prototype │ • Clean markdown narrative   │ • Git-friendly, no JSON diffs│
└────────────────────────────┘ └────────────────────────────┘ └────────────────────────────┘
```

---

## 📐 Archetype Breakdown & Code Discipline

### 1. Exploratory Scratchpad (Research / Rapid Prototyping)
* **Goal**: Understand raw data distributions, test transformations, and establish quick baselines.
* **Code Style**:
  - Direct, transparent code cells.
  - Frequent intermediate sanity prints (`print(f"Shape: {df.shape}")`, `df['target'].value_counts()`).
  - Small, focused cells (one transformation or plot per cell).
* **Hygiene**: Delete dead experiment cells before saving. Keep a linear top-to-bottom flow.

### 2. Decision Showcase & Living Deliverable (Team / Executive Handoff)
* **Goal**: Communicate findings, defend an architectural choice, or present model trade-offs to stakeholders.
* **Code Style**:
  - **Do NOT inline 200 lines of helper functions**. Extract business logic into `src/` modules and import them:
    ```python
    # ✅ Clean Showcase Cell
    from src.data.loader import load_clean_orders
    from src.models.evaluator import compute_cost_matrix, plot_cost_curve

    df = load_clean_orders(snapshot_date="2026-08-25")
    fig = plot_cost_curve(df, model_name="baseline_logreg")
    fig.show()
    ```
  - Hide verbose debug outputs. Display polished tables (`df.head(5)`, `.to_markdown()`) and clean visual charts.
  - Markdown cells contain the **Executive Narrative**: Problem $\to$ Evidence $\to$ Business Decision.

### 3. Reactive Data Application (`marimo`)
* **Goal**: Interactive exploration without hidden notebook state, directly shareable as a web UI or script.
* **Core Rules**:
  - **No Global Variable Mutation**: A variable defined in Cell A must not be reassigned in Cell B (`marimo` enforces a strict Directed Acyclic Graph).
  - Use UI elements (`mo.ui.slider`, `mo.ui.dropdown`) to parameterize queries reactively.
  - Native Git integration: marimo stores pure `.py` code with zero messy notebook JSON metadata.

---

## 🛡️ The 4 Non-Negotiable Rules of Notebook Hygiene

### Rule 1: The Output Precedes the Interpretation
* **The Anti-Pattern**: Writing markdown text that asserts a conclusion *before* the code has run, guessing the result.
* **The Senior Standard**:
  1. `[Markdown]` Formulate the **Question / Hypothesis**.
  2. `[Code Cell]` Run the calculation or visualization.
  3. `[Markdown or Print]` State the **Factual Observation** based strictly on the output.
  4. `[Markdown]` Conclude with the **Next Action / Decision**.

### Rule 2: The "Restart Kernel & Run All" Invariant
* Every Jupyter notebook (`.ipynb`) must be able to execute cleanly from top to bottom on a fresh kernel:
  - No out-of-order execution artifacts (e.g. Cell `[45]` preceding Cell `[3]`).
  - No dependency on memory variables left over from deleted cells.

### Rule 3: Output Formatting & Volume Discipline
* **Never dump 500 rows of raw text or unformatted JSON** into a notebook cell.
* Cap outputs with `.head(5)`, `.describe()`, or aggregated summaries.
* Suppress noisy library warnings at the top of the notebook:
  ```python
  import warnings
  warnings.filterwarnings("ignore", category=UserWarning)
  ```

### Rule 4: Clear Header & Audience Declaration
Every notebook should begin with a clean Level-1 Header declaring its purpose:

```markdown
# 📊 Customer Churn Risk Analysis (Q3 2026)
> **Archetype**: Decision Showcase · **Target Audience**: Growth & Retention Team  
> **Objective**: Evaluate whether the baseline Logistic Regression model justifies deployment based on the €500/false-negative cost matrix.
```
