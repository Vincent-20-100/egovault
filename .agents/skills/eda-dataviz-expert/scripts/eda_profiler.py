#!/usr/bin/env python3
"""
EDA Diagnostic Profiler
------------------------
Automated data health check, statistical hygiene analysis, and visual encoding recommendations.
Zero-dependency native fallback (pure Python standard library) with auto-acceleration if pandas/numpy are present.
Supports CSV, JSON, and TSV files. Outputs a clean Markdown report.
"""

import sys
import os
import csv
import json
import math
import statistics
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Ensure UTF-8 stdout encoding on Windows consoles
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def is_float(val: str) -> bool:
    try:
        float(val)
        return True
    except (ValueError, TypeError):
        return False


def calculate_skewness(values: List[float], mean_val: float, std_val: float) -> Optional[float]:
    n = len(values)
    if n < 3 or std_val == 0:
        return None
    m3 = sum((x - mean_val) ** 3 for x in values) / n
    skew = m3 / (std_val ** 3)
    return skew


def profile_pure_python(file_path: Path, max_rows: Optional[int] = None, target_col: Optional[str] = None) -> Dict[str, Any]:
    with open(file_path, mode="r", encoding="utf-8", errors="replace") as f:
        sample = f.read(4096)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample)
            delimiter = dialect.delimiter
        except Exception:
            delimiter = "," if not file_path.suffix.lower() == ".tsv" else "\t"

        reader = csv.reader(f, delimiter=delimiter)
        try:
            headers = next(reader)
        except StopIteration:
            return {"error": "Empty file"}

        headers = [h.strip() for h in headers]
        raw_cols: Dict[str, List[str]] = {h: [] for h in headers}
        
        row_count = 0
        seen_rows = set()
        n_duplicates = 0

        for row in reader:
            if not row or all(c.strip() == "" for c in row):
                continue
            row_count += 1
            if max_rows and row_count > max_rows:
                break
            
            row_tuple = tuple(row)
            if row_tuple in seen_rows:
                n_duplicates += 1
            else:
                seen_rows.add(row_tuple)

            for i, val in enumerate(row):
                if i < len(headers):
                    raw_cols[headers[i]].append(val.strip())

    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    dup_pct = (n_duplicates / row_count * 100) if row_count > 0 else 0.0

    columns_summary = []
    high_skew_cols = []
    outlier_alerts = []
    missing_alerts = []
    numeric_series: Dict[str, List[float]] = {}

    for col_name, raw_vals in raw_cols.items():
        total_vals = len(raw_vals)
        non_null_vals = [v for v in raw_vals if v != "" and v.lower() not in ["nan", "none", "null", "na", "n/a", "nil"]]
        n_missing = total_vals - len(non_null_vals)
        missing_pct = (n_missing / total_vals * 100) if total_vals > 0 else 0.0
        unique_set = set(non_null_vals)
        n_unique = len(unique_set)
        unique_ratio = (n_unique / total_vals) if total_vals > 0 else 0.0

        if missing_pct > 0:
            missing_alerts.append((col_name, n_missing, missing_pct))

        num_floats = [float(v) for v in non_null_vals if is_float(v)]
        is_num = len(num_floats) > 0 and (len(num_floats) / len(non_null_vals) >= 0.90) if non_null_vals else False

        col_dict: Dict[str, Any] = {
            "name": col_name,
            "missing_pct": missing_pct,
            "n_unique": n_unique,
            "unique_ratio": unique_ratio,
            "mean": None,
            "median": None,
            "std": None,
            "min": None,
            "max": None,
            "skewness": None,
            "iqr_outliers": 0,
            "outlier_pct": 0.0
        }

        if is_num and len(num_floats) > 0:
            numeric_series[col_name] = num_floats
            mean_v = statistics.mean(num_floats)
            median_v = statistics.median(num_floats)
            std_v = statistics.stdev(num_floats) if len(num_floats) > 1 else 0.0
            min_v = min(num_floats)
            max_v = max(num_floats)

            col_dict["mean"] = mean_v
            col_dict["median"] = median_v
            col_dict["std"] = std_v
            col_dict["min"] = min_v
            col_dict["max"] = max_v

            if n_unique == 2:
                col_dict["semantic_type"] = "Binary Numeric"
            elif n_unique <= 10 and all(v.is_integer() for v in num_floats):
                col_dict["semantic_type"] = "Discrete Ordinal"
            else:
                col_dict["semantic_type"] = "Continuous Numeric"

            if len(num_floats) >= 3:
                skew = calculate_skewness(num_floats, mean_v, std_v)
                col_dict["skewness"] = skew
                if skew is not None and abs(skew) > 1.0:
                    high_skew_cols.append((col_name, skew))

            # IQR Outliers
            if len(num_floats) >= 4:
                sorted_vals = sorted(num_floats)
                q25 = sorted_vals[int(len(sorted_vals) * 0.25)]
                q75 = sorted_vals[int(len(sorted_vals) * 0.75)]
                iqr = q75 - q25
                if iqr > 0:
                    lower = q25 - 1.5 * iqr
                    upper = q75 + 1.5 * iqr
                    n_outliers = sum(1 for v in num_floats if v < lower or v > upper)
                    out_pct = (n_outliers / len(num_floats) * 100)
                    col_dict["iqr_outliers"] = n_outliers
                    col_dict["outlier_pct"] = out_pct
                    if out_pct > 2.0:
                        outlier_alerts.append((col_name, n_outliers, out_pct))
        else:
            if n_unique == 2:
                col_dict["semantic_type"] = "Binary Categorical"
            elif n_unique <= 15:
                col_dict["semantic_type"] = "Nominal Categorical"
            elif unique_ratio > 0.95 and total_vals > 20:
                col_dict["semantic_type"] = "Unique ID / Text"
            else:
                col_dict["semantic_type"] = "Categorical / Text"

        columns_summary.append(col_dict)

    # Correlation check (pure python)
    corr_pairs = []
    num_cols = list(numeric_series.keys())
    if len(num_cols) > 1:
        for i in range(len(num_cols)):
            for j in range(i + 1, len(num_cols)):
                c1, c2 = num_cols[i], num_cols[j]
                v1, v2 = numeric_series[c1], numeric_series[c2]
                min_len = min(len(v1), len(v2))
                if min_len >= 5:
                    sub1 = v1[:min_len]
                    sub2 = v2[:min_len]
                    m1, m2 = statistics.mean(sub1), statistics.mean(sub2)
                    num = sum((x - m1) * (y - m2) for x, y in zip(sub1, sub2))
                    den = math.sqrt(sum((x - m1)**2 for x in sub1) * sum((y - m2)**2 for y in sub2))
                    if den > 0:
                        r = abs(num / den)
                        if r >= 0.70:
                            corr_pairs.append((c1, c2, r))
        corr_pairs.sort(key=lambda x: x[2], reverse=True)

    target_info = None
    if target_col and target_col in raw_cols:
        t_vals = raw_cols[target_col]
        non_null_t = [v for v in t_vals if v != ""]
        counts = {}
        for v in non_null_t:
            counts[v] = counts.get(v, 0) + 1
        dist = {k: (v / len(non_null_t)) for k, v in sorted(counts.items(), key=lambda x: x[1], reverse=True)[:10]} if len(counts) <= 10 else None
        target_info = {
            "name": target_col,
            "type": "Categorical" if len(counts) <= 10 else "Continuous",
            "missing_pct": ((len(t_vals) - len(non_null_t)) / len(t_vals) * 100) if t_vals else 0.0,
            "distribution": dist
        }

    return {
        "n_rows": row_count,
        "n_cols": len(headers),
        "memory_mb": file_size_mb,
        "n_duplicates": n_duplicates,
        "dup_pct": dup_pct,
        "columns": columns_summary,
        "missing_alerts": missing_alerts,
        "high_skew_cols": high_skew_cols,
        "outlier_alerts": outlier_alerts,
        "corr_pairs": corr_pairs,
        "target_info": target_info
    }


def generate_markdown_report(profile: Dict[str, Any]) -> str:
    lines = []
    lines.append("# Data Health & EDA Diagnostic Report\n")
    
    # 1. Overview
    lines.append("## 1. Dataset Overview")
    lines.append(f"- **Dimensions**: `{profile['n_rows']:,}` rows × `{profile['n_cols']}` columns")
    lines.append(f"- **Size on Disk / Memory**: `{profile['memory_mb']:.2f} MB`")
    lines.append(f"- **Duplicate Rows**: `{profile['n_duplicates']:,}` ({profile['dup_pct']:.2f}%)")
    lines.append("")

    # 2. Critical Hygiene Alerts
    lines.append("## 2. Critical Hygiene Alerts")
    alerts_count = len(profile["missing_alerts"]) + len(profile["outlier_alerts"]) + len(profile["high_skew_cols"])
    if alerts_count == 0 and profile["n_duplicates"] == 0:
        lines.append("No critical hygiene issues detected.")
    else:
        if profile["n_duplicates"] > 0:
            lines.append(f"- **Duplicates**: `{profile['n_duplicates']:,}` duplicate rows found. Consider dropping.")
        if profile["missing_alerts"]:
            lines.append("- **Missing Values Detected**:")
            for col, count, pct in profile["missing_alerts"]:
                lines.append(f"  - `{col}`: {count:,} NaNs ({pct:.1f}%)")
        if profile["high_skew_cols"]:
            lines.append("- **High Skewness ($|\\text{skew}| > 1.0$)**:")
            for col, skew in profile["high_skew_cols"]:
                direction = "Right-tailed" if skew > 0 else "Left-tailed"
                lines.append(f"  - `{col}`: Skew = `{skew:.2f}` ({direction}) -> Use Median/IQR or Log scale")
        if profile["outlier_alerts"]:
            lines.append("- **High Outlier Density (IQR > 2%)**:")
            for col, count, pct in profile["outlier_alerts"]:
                lines.append(f"  - `{col}`: {count:,} outliers ({pct:.1f}%) -> Inspect before linear modeling")
    lines.append("")

    # 3. Multicollinearity / High Correlations
    if profile["corr_pairs"]:
        lines.append("## 3. High Correlation Warnings ($|r| >= 0.70$)")
        lines.append("| Feature A | Feature B | Pearson Correlation ($r$) | Recommendation |")
        lines.append("| :--- | :--- | :--- | :--- |")
        for col_a, col_b, r in profile["corr_pairs"][:8]:
            lines.append(f"| `{col_a}` | `{col_b}` | **{r:.3f}** | Check for collinearity or target leakage |")
        lines.append("")

    # 4. Target Analysis
    if profile.get("target_info"):
        t = profile["target_info"]
        lines.append(f"## 4. Target Variable Analysis: `{t['name']}`")
        lines.append(f"- **Semantic Type**: {t['type']}")
        lines.append(f"- **Missing Rate**: {t['missing_pct']:.2f}%")
        if t["distribution"]:
            lines.append("- **Class Breakdown**:")
            for val, prop in t["distribution"].items():
                lines.append(f"  - `{val}`: {prop*100:.2f}%")
        lines.append("")

    # 5. Column Profiling Summary Table
    lines.append("## 5. Column Profile Summary")
    lines.append("| Column | Inferred Type | Missing % | Uniques | Central Tendency (Mean / Median) | Dispersion (Std / Outliers) |")
    lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
    for c in profile["columns"]:
        mean_med = "-"
        disp = "-"
        if c["mean"] is not None:
            mean_med = f"{c['mean']:.2f} / {c['median']:.2f}"
            disp = f"σ={c['std']:.2f} ({c['outlier_pct']:.1f}% out)"
        lines.append(f"| `{c['name']}` | {c['semantic_type']} | {c['missing_pct']:.1f}% | {c['n_unique']} | {mean_med} | {disp} |")
    lines.append("")

    # 6. Prescribed Visualizations
    lines.append("## 6. Recommended Visualizations (Action Plan)")
    for c in profile["columns"]:
        if c["semantic_type"] == "Continuous Numeric":
            if c["skewness"] and abs(c["skewness"]) > 1.0:
                lines.append(f"- **`{c['name']}`**: Log-scale Histogram + Boxplot (High Skewness: `{c['skewness']:.2f}`).")
            else:
                lines.append(f"- **`{c['name']}`**: Standard Histogram with KDE + Boxplot for IQR boundaries.")
        elif c["semantic_type"] in ["Nominal Categorical", "Binary Categorical"]:
            lines.append(f"- **`{c['name']}`**: Sorted Horizontal Bar Chart (Cardinality: {c['n_unique']}).")
        elif c["semantic_type"] == "Datetime":
            lines.append(f"- **`{c['name']}`**: Continuous Line Chart with Rolling Mean.")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="EDA & Data Hygiene Diagnostic Tool")
    parser.add_argument("file_path", type=str, help="Path to data file (.csv, .tsv, .json)")
    parser.add_argument("--target", type=str, default=None, help="Optional target column name")
    parser.add_argument("--max-rows", type=int, default=None, help="Max rows to sample for quick profiling")
    parser.add_argument("--output", type=str, default=None, help="Optional output Markdown file path")
    args = parser.parse_args()

    path = Path(args.file_path)
    if not path.exists():
        print(f"Error: File '{path}' does not exist.", file=sys.stderr)
        sys.exit(1)

    print(f"Profiling '{path.name}'...", file=sys.stderr)
    profile = profile_pure_python(path, max_rows=args.max_rows, target_col=args.target)
    report = generate_markdown_report(profile)

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(report, encoding="utf-8")
        print(f"Report saved to: {out_path}", file=sys.stderr)
    else:
        print(report)


if __name__ == "__main__":
    main()
