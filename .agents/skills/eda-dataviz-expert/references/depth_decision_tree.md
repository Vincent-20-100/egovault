# Visualization Depth Decision Tree (Anti-Overengineering vs Anti-Sloppiness)

> **Core Philosophy**: Match visual polish and tooling to the audience and shelf-life of the output. Never spend an hour theming a chart that answers a question you'll never look at again, and never ship an unlabeled default-matplotlib chart to a client deck.

---

## 🧭 The 3-Tier Depth Matrix

```text
                    ┌──────────────────────────────────────────────┐
                    │  Who is the audience, and how long does this │
                    │              chart need to live?              │
                    └──────────────────────┬───────────────────────┘
                                           │
         ┌─────────────────────────────────┼─────────────────────────────────┐
         ▼                                 ▼                                 ▼
┌──────────────────┐             ┌──────────────────┐             ┌──────────────────┐
│   TIER 0 (PEEK)  │             │  TIER 1 (REPORT) │             │ TIER 2 (PRESENT) │
│ Solo exploration │             │ Internal analysis│             │ Client / exec /   │
│                  │             │                  │             │ published deck    │
└────────┬─────────┘             └────────┬─────────┘             └────────┬─────────┘
         │                                │                                │
         ▼                                ▼                                ▼
• Default library theme           • One consistent preset          • Full preset applied
• No labels beyond axis names     • Direct labels on key series    • Direct labeling everywhere
• Throwaway, never re-run         • Locale-correct units           • Reviewed against 5D checklist
• `df.plot()` / `sns.histplot()`  • Entity colors consistent       • Annotated takeaway sentence
  is enough                        within the notebook              per chart
```

---

## 📊 Detailed Comparison by Dimension

| Dimension | Tier 0: Solo Peek | Tier 1: Internal Report | Tier 2: Presentation-Grade |
| :--- | :--- | :--- | :--- |
| **Typical Target** | "What does this column look like" during EDA | Team-facing notebook, internal dashboard | Client deliverable, exec dashboard, publication |
| **Styling** | Library default, no theme | One preset (`editorial`/`scientific`/`dark`) applied consistently | Preset + brand tokens + typography pass |
| **Labeling** | Axis titles only, if that | Direct labels on the series that matter | Full direct labeling, annotated insight |
| **Numerical hygiene** | Not enforced | Ban on scientific notation, locale units | Same, plus decimal/rounding polish reviewed |
| **Review** | None — it's disposable | Skim against the 5D checklist | Full 5D checklist, pass required before shipping |

---

## 🚫 When NOT to Reach for Tier 2 (Counter-Cases)

Audience size or chart count doesn't automatically justify presentation polish. Stay at Tier 0/1 when:

* **The chart answers a question once**, in the middle of an exploratory session, and won't be looked at again after the decision is made.
* **You are the only viewer** — a themed, annotated chart for your own scratch analysis is time spent on an audience of one.
* **The dataset or question is still shifting** — polishing a chart you're about to redefine is wasted effort; theme once the analytical question has stabilized.

Tier 2 earns its cost when the chart will be seen by someone who wasn't in the room for the analysis — a colleague, a client, a reader.

---

## 📣 Declare Your Tier Before Building

Before producing a chart or dashboard, state the choice in one line so it's visible and correctable by the user rather than silently baked in:

```text
Tier chosen: T{0|1|2} — because: {one clause on audience and shelf-life}
```

If the user disagrees, that's a signal to renegotiate scope (more or less polish), not to silently comply — surface the trade-off.
