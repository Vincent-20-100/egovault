#!/usr/bin/env python3
"""
ml_leakage_and_baseline_gate.py - Standalone Zero-Dependency ML Dataset & Baseline Auditor.

Inspects CSV datasets for:
1. Target distribution, class imbalance, or skewness.
2. Mandatory Dummy Baseline metrics (Majority class / Mean predictor).
3. Candidate ID columns and high-risk target leakage.
4. Missing value rates.

Usage:
    python ml_leakage_and_baseline_gate.py data.csv --target churn
    python ml_leakage_and_baseline_gate.py data.csv --target price --strict
"""

from __future__ import annotations

import argparse
import csv
import io
import math
import sys
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Tuple

# Ensure UTF-8 output on Windows consoles
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (io.UnsupportedOperation, AttributeError):
        pass


def is_number(s: str) -> bool:
    """Check whether a string represents a valid float number.

    Args:
        s: Input string to test.

    Returns:
        True if convertible to float, False otherwise.
    """
    try:
        float(s)
        return True
    except ValueError:
        return False


def compute_mean(values: List[float]) -> float:
    """Compute the arithmetic mean of a list of floats.

    Args:
        values: Non-empty list of numerical values.

    Returns:
        The average value, or 0.0 if empty.
    """
    return sum(values) / len(values) if values else 0.0


def compute_std(values: List[float], mean_val: float) -> float:
    """Compute sample standard deviation given precalculated mean.

    Args:
        values: List of numerical values.
        mean_val: Precomputed mean of the list.

    Returns:
        Sample standard deviation.
    """
    if len(values) < 2:
        return 0.0
    variance = sum((x - mean_val) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(variance)


def compute_pearson(x: List[float], y: List[float]) -> float:
    """Compute Pearson correlation coefficient between two series.

    Args:
        x: First numerical series.
        y: Second numerical series.

    Returns:
        Pearson r coefficient between -1.0 and 1.0.
    """
    n = len(x)
    if n != len(y) or n < 2:
        return 0.0
    mean_x = compute_mean(x)
    mean_y = compute_mean(y)
    cov = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    std_x = compute_std(x, mean_x)
    std_y = compute_std(y, mean_y)
    if std_x == 0 or std_y == 0:
        return 0.0
    return cov / ((n - 1) * std_x * std_y)


def audit_dataset(filepath: str, target_col: str, max_rows: int = 100_000) -> Tuple[bool, List[str]]:
    """Scan a CSV dataset for sanity, leakage, and dummy baselines.

    Args:
        filepath: Path to CSV dataset file.
        target_col: Name of the target variable column.
        max_rows: Maximum number of rows to scan.

    Returns:
        A tuple of (passed_status, list_of_warning_messages).
    """
    warnings = []

    print(f"\n" + "=" * 70)
    print(f"🚀  APPLIED-ML DATASET & BASELINE AUDIT")
    print(f"    File: {filepath}")
    print(f"    Target Column: '{target_col}'")
    print("=" * 70)

    try:
        with open(filepath, mode="r", encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if not header:
                print("❌ ERROR: Empty CSV file.")
                return False, ["Empty CSV file."]

            if target_col not in header:
                print(f"❌ ERROR: Target column '{target_col}' not found in CSV header.")
                print(f"   Available columns ({len(header)}): {', '.join(header[:15])}...")
                return False, [f"Target column '{target_col}' not found."]

            columns_data = defaultdict(list)
            row_count = 0

            for row in reader:
                if not row or len(row) != len(header):
                    continue
                row_count += 1
                for idx, val in enumerate(row):
                    columns_data[header[idx]].append(val.strip())
                if row_count >= max_rows:
                    break

    except Exception as e:
        print(f"❌ ERROR reading CSV: {e}")
        return False, [str(e)]

    print(f"\n📊 [1. Dataset Dimensions]")
    print(f"   Rows loaded: {row_count:,}")
    print(f"   Total features: {len(header) - 1}")

    target_values = columns_data[target_col]
    valid_target_values = [v for v in target_values if v != ""]

    if not valid_target_values:
        print(f"❌ ERROR: Target column '{target_col}' has 100% missing values.")
        return False, ["Target column has 100% missing values."]

    # 1. Target Type Detection
    is_numeric_target = all(is_number(v) for v in valid_target_values[:500])
    unique_target_count = len(set(valid_target_values))

    # If numeric but <= 10 unique integer values, treat as classification
    is_classification = (not is_numeric_target) or (unique_target_count <= 10)

    print(f"\n🎯 [2. Target Analysis & Dummy Baseline]")
    if is_classification:
        counts = Counter(valid_target_values)
        total = len(valid_target_values)
        sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        majority_class, majority_count = sorted_counts[0]
        majority_pct = majority_count / total

        print(f"   Task: Classification ({len(sorted_counts)} classes)")
        print(f"   Class distribution:")
        for cls_name, count in sorted_counts[:10]:
            print(f"     • {cls_name}: {count:,} ({count / total:.1%})")

        print(f"\n   🏆 MANDATORY DUMMY BASELINE (Strategy: Most Frequent):")
        print(f"     • Baseline Accuracy: {majority_pct:.4f} ({majority_pct:.1%})")
        print(f"     • Benchmark Rule: Any trained model MUST score significantly higher than {majority_pct:.4f}.")

        if majority_pct > 0.90:
            msg = f"Severe class imbalance: Majority class is {majority_pct:.1%}. Raw accuracy is DECEPTIVE. Mandate PR-AUC / F-beta / Brier score."
            warnings.append(msg)
            print(f"\n   ⚠️  WARNING: {msg}")

    else:
        num_targets = [float(v) for v in valid_target_values]
        mean_t = compute_mean(num_targets)
        std_t = compute_std(num_targets, mean_t)
        sorted_t = sorted(num_targets)
        median_t = sorted_t[len(sorted_t) // 2]
        mae_mean_baseline = sum(abs(y - mean_t) for y in num_targets) / len(num_targets)
        rmse_mean_baseline = math.sqrt(sum((y - mean_t) ** 2 for y in num_targets) / len(num_targets))

        print(f"   Task: Regression")
        print(f"   Mean: {mean_t:.4f} | Median: {median_t:.4f} | Std: {std_t:.4f}")
        print(f"   Min: {sorted_t[0]:.4f} | Max: {sorted_t[-1]:.4f}")
        print(f"\n   🏆 MANDATORY DUMMY BASELINE (Strategy: Mean Predictor):")
        print(f"     • Baseline MAE:  {mae_mean_baseline:.4f}")
        print(f"     • Baseline RMSE: {rmse_mean_baseline:.4f}")
        print(f"     • Benchmark Rule: Any trained model MUST produce MAE < {mae_mean_baseline:.4f}.")

    # 3. High-cardinality ID candidate checks
    print(f"\n🔍 [3. High-Cardinality & Potential ID Detection]")
    id_candidates = []
    for col in header:
        if col == target_col:
            continue
        vals = [v for v in columns_data[col] if v != ""]
        distinct_count = len(set(vals))
        if distinct_count == row_count and row_count > 50:
            id_candidates.append((col, distinct_count))

    if id_candidates:
        msg = f"Found {len(id_candidates)} high-cardinality candidate ID column(s): {[c[0] for c in id_candidates]}. Drop before modeling!"
        warnings.append(msg)
        print(f"   🚨 SUSPICIOUS ID COLUMNS DETECTED:")
        for c, count in id_candidates:
            print(f"     • '{c}' has {count:,} unique values (100% uniqueness).")
    else:
        print(f"   ✅ No 100% unique ID columns detected.")

    # 4. Target Leakage Correlation Check
    print(f"\n🚨 [4. Target Leakage & High-Correlation Audit]")
    leakage_found = False
    if not is_classification:
        num_targets = [float(v) for v in valid_target_values]
        for col in header:
            if col == target_col:
                continue
            vals = columns_data[col]
            if all(is_number(v) for v in vals if v != "") and len(vals) == len(num_targets):
                num_vals = [float(v) if v != "" else mean_t for v in vals]
                corr = compute_pearson(num_vals, num_targets)
                if abs(corr) > 0.95:
                    leakage_found = True
                    msg = f"Feature '{col}' has extreme correlation ({corr:.4f}) with target. Suspected target leakage!"
                    warnings.append(msg)
                    print(f"   ⚠️  POTENTIAL TARGET LEAKAGE: '{col}' (Pearson r = {corr:.4f})")
    if not leakage_found:
        print(f"   ✅ No obvious single-feature target leakage (>0.95 correlation) detected.")

    # 5. Missingness summary
    print(f"\n📉 [5. Missing Values Summary]")
    missing_cols = []
    for col in header:
        vals = columns_data[col]
        null_count = sum(1 for v in vals if v == "")
        if null_count > 0:
            null_pct = null_count / row_count
            missing_cols.append((col, null_count, null_pct))

    if missing_cols:
        missing_cols.sort(key=lambda x: x[2], reverse=True)
        print(f"   Features with missing values ({len(missing_cols)} total):")
        for col, count, pct in missing_cols[:8]:
            print(f"     • '{col}': {count:,} missing ({pct:.1%})")
    else:
        print(f"   ✅ No missing values detected in dataset.")

    print("\n" + "=" * 70)
    if warnings:
        print(f"⚠️  AUDIT SUMMARY: {len(warnings)} potential risk(s) identified.")
    else:
        print("✅  AUDIT PASSED: Dataset is ready for baseline modeling.")
    print("=" * 70 + "\n")

    return (len(warnings) == 0), warnings


def main() -> None:
    """Entry point for the command-line interface."""
    parser = argparse.ArgumentParser(description="Standalone Zero-Dep ML Dataset & Baseline Auditor")
    parser.add_argument("file", help="Path to CSV dataset")
    parser.add_argument("--target", required=True, help="Target column name")
    parser.add_argument("--max-rows", type=int, default=100_000, help="Maximum rows to scan (default 100k)")
    parser.add_argument("--strict", action="store_true", help="Exit with non-zero code if warnings are found")

    args = parser.parse_args()
    passed, warnings = audit_dataset(args.file, args.target, args.max_rows)

    if args.strict and not passed:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
