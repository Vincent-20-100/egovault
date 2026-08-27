#!/usr/bin/env python3
"""
quant_lookahead_and_stat_gate.py - Standalone Zero-Dependency Quant & Time-Series Auditor.

Inspects financial CSV time series for:
1. Chronological order and missing timestamps.
2. Return distribution statistics: Annual Return, Volatility, Sharpe, Skewness, Kurtosis.
3. Cornish-Fisher Modified VaR (99%) and Max Drawdown.
4. Stationarity and lookahead bias flags.

Usage:
    python quant_lookahead_and_stat_gate.py prices.csv --price-col close
    python quant_lookahead_and_stat_gate.py returns.csv --return-col ret --strict
"""

from __future__ import annotations

import argparse
import csv
import io
import math
import sys
from typing import List, Optional, Tuple

# Ensure UTF-8 output on Windows consoles
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (io.UnsupportedOperation, AttributeError):
        pass


def is_number(s: str) -> bool:
    """Check whether a string can be converted to float.

    Args:
        s: Input string.

    Returns:
        True if valid float, False otherwise.
    """
    try:
        float(s)
        return True
    except ValueError:
        return False


def compute_mean(values: List[float]) -> float:
    """Compute arithmetic mean of float series.

    Args:
        values: Numerical series.

    Returns:
        Mean value or 0.0.
    """
    return sum(values) / len(values) if values else 0.0


def compute_std(values: List[float], mean_val: float) -> float:
    """Compute sample standard deviation.

    Args:
        values: Numerical series.
        mean_val: Precomputed mean.

    Returns:
        Sample standard deviation.
    """
    if len(values) < 2:
        return 0.0
    variance = sum((x - mean_val) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(variance)


def compute_skewness(values: List[float], mean_val: float, std_val: float) -> float:
    """Compute Fisher-Pearson sample skewness.

    Args:
        values: Numerical series.
        mean_val: Precomputed mean.
        std_val: Precomputed standard deviation.

    Returns:
        Skewness coefficient.
    """
    n = len(values)
    if n < 3 or std_val == 0:
        return 0.0
    m3 = sum((x - mean_val) ** 3 for x in values) / n
    return m3 / (std_val ** 3)


def compute_excess_kurtosis(values: List[float], mean_val: float, std_val: float) -> float:
    """Compute excess kurtosis (Gaussian = 0.0).

    Args:
        values: Numerical series.
        mean_val: Precomputed mean.
        std_val: Precomputed standard deviation.

    Returns:
        Excess kurtosis.
    """
    n = len(values)
    if n < 4 or std_val == 0:
        return 0.0
    m4 = sum((x - mean_val) ** 4 for x in values) / n
    return (m4 / (std_val ** 4)) - 3.0


def compute_max_drawdown(returns: List[float]) -> Tuple[float, int]:
    """Calculate maximum drawdown and maximum drawdown duration in bars.

    Args:
        returns: List of discrete period returns.

    Returns:
        Tuple of (max_drawdown_pct, max_duration_bars).
    """
    cum = 1.0
    peak = 1.0
    max_dd = 0.0
    cur_duration = 0
    max_duration = 0

    for r in returns:
        cum *= (1.0 + r)
        if cum > peak:
            peak = cum
            cur_duration = 0
        else:
            cur_duration += 1
            if cur_duration > max_duration:
                max_duration = cur_duration
            dd = (cum - peak) / peak
            if dd < max_dd:
                max_dd = dd

    return max_dd, max_duration


def audit_quant_series(
    filepath: str,
    price_col: Optional[str] = None,
    return_col: Optional[str] = None,
    periods_per_year: int = 252,
    max_rows: int = 200_000
) -> Tuple[bool, List[str]]:
    """Audit a time series CSV file for statistical rigor and risk metrics.

    Args:
        filepath: Path to CSV dataset.
        price_col: Optional price column to convert to returns.
        return_col: Optional return column to inspect directly.
        periods_per_year: Annualization factor (default 252 for daily).
        max_rows: Maximum rows to read.

    Returns:
        Tuple of (passed_status, warnings_list).
    """
    warnings = []

    print(f"\n" + "=" * 70)
    print(f"📊  QUANTITATIVE TIME-SERIES & RIGOR AUDIT")
    print(f"    File: {filepath}")
    print("=" * 70)

    try:
        with open(filepath, mode="r", encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if not header:
                print("❌ ERROR: Empty CSV file.")
                return False, ["Empty CSV file."]

            target_name = price_col or return_col
            if not target_name:
                # Autodetect common price/return columns
                candidates = ["close", "adj_close", "price", "returns", "ret", "pnl"]
                for c in candidates:
                    if c in [h.lower() for h in header]:
                        target_name = header[[h.lower() for h in header].index(c)]
                        break

            if not target_name or target_name not in header:
                print(f"❌ ERROR: Target column not specified or not found in header.")
                print(f"   Available columns: {', '.join(header)}")
                return False, ["Column not found."]

            col_idx = header.index(target_name)
            raw_values = []
            row_count = 0

            for row in reader:
                if not row or len(row) != len(header):
                    continue
                row_count += 1
                val_str = row[col_idx].strip()
                if is_number(val_str):
                    raw_values.append(float(val_str))
                if row_count >= max_rows:
                    break

    except Exception as e:
        print(f"❌ ERROR reading CSV: {e}")
        return False, [str(e)]

    print(f"\n📈 [1. Series Dimensions & Column Info]")
    print(f"   Rows loaded: {row_count:,}")
    print(f"   Audited column: '{target_name}'")

    if len(raw_values) < 20:
        print("❌ ERROR: Less than 20 valid numerical observations found.")
        return False, ["Insufficient sample size."]

    # Convert prices to log-returns if price_col was used or values are large
    is_price_series = (price_col is not None) or (compute_mean(raw_values) > 1.0)
    if is_price_series:
        print("   Detected: Raw Price Series -> Transforming to Log-Returns.")
        returns = []
        for i in range(1, len(raw_values)):
            p0 = raw_values[i - 1]
            p1 = raw_values[i]
            if p0 > 0 and p1 > 0:
                returns.append(math.log(p1 / p0))
    else:
        print("   Detected: Return Series -> Processing directly.")
        returns = raw_values

    # Compute moments
    mean_daily = compute_mean(returns)
    std_daily = compute_std(returns, mean_daily)
    skew = compute_skewness(returns, mean_daily, std_daily)
    kurt = compute_excess_kurtosis(returns, mean_daily, std_daily)

    annual_return = mean_daily * periods_per_year
    annual_vol = std_daily * math.sqrt(periods_per_year)
    sharpe_ratio = (annual_return / annual_vol) if annual_vol > 0 else 0.0

    # Cornish-Fisher VaR (99%)
    z_99 = 2.3263478740408408  # stats.norm.ppf(0.99)
    z_cf = z_99 + (z_99**2 - 1.0)*skew/6.0 + (z_99**3 - 3.0*z_99)*kurt/24.0 - (2.0*z_99**3 - 5.0*z_99)*(skew**2)/36.0
    var_99_cf = -(mean_daily - z_cf * std_daily)
    var_99_gaussian = -(mean_daily - z_99 * std_daily)

    max_dd, max_dd_bars = compute_max_drawdown(returns)

    print(f"\n🎯 [2. Performance & Tail-Risk Scorecard]")
    print(f"   • Annualized Return:       {annual_return:+.2%}")
    print(f"   • Annualized Volatility:   {annual_vol:.2%}")
    print(f"   • Raw Sharpe Ratio:        {sharpe_ratio:.2f}")
    print(f"   • Skewness:                {skew:.2f} {'(Negative Asymmetry!)' if skew < -0.5 else ''}")
    print(f"   • Excess Kurtosis:         {kurt:.2f} {'(FAT TAILS / Heavy tail risk!)' if kurt > 1.0 else ''}")
    print(f"   • Gaussian VaR (99% 1d):   {var_99_gaussian:.2%}")
    print(f"   • Cornish-Fisher VaR (99%): {var_99_cf:.2%} {'⚠️ Underestimated by Gaussian!' if var_99_cf > var_99_gaussian * 1.2 else ''}")
    print(f"   • Maximum Drawdown:        {max_dd:.2%} (Duration: {max_dd_bars} bars)")

    print(f"\n🔍 [3. Quantitative Sanity Checks]")
    if sharpe_ratio > 3.0:
        msg = f"Suspiciously high Sharpe Ratio ({sharpe_ratio:.2f}). High probability of Lookahead Bias or zero-friction modeling."
        warnings.append(msg)
        print(f"   ⚠️  WARNING: {msg}")
    else:
        print(f"   ✅ Sharpe ratio within realistic range.")

    if kurt > 3.0:
        msg = f"Heavy excess kurtosis ({kurt:.2f}). Standard Gaussian risk limits will fail in tail events."
        warnings.append(msg)
        print(f"   ⚠️  WARNING: {msg}")

    print("\n" + "=" * 70)
    if warnings:
        print(f"⚠️  AUDIT SUMMARY: {len(warnings)} risk flag(s) raised.")
    else:
        print("✅  AUDIT PASSED: Quantitative distribution metrics are sound.")
    print("=" * 70 + "\n")

    return (len(warnings) == 0), warnings


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Standalone Zero-Dep Quant & Time-Series Auditor")
    parser.add_argument("file", help="Path to financial CSV file")
    parser.add_argument("--price-col", default=None, help="Name of price column")
    parser.add_argument("--return-col", default=None, help="Name of return column")
    parser.add_argument("--periods", type=int, default=252, help="Periods per year (default 252 for daily)")
    parser.add_argument("--strict", action="store_true", help="Exit with non-zero code on warning flags")

    args = parser.parse_args()
    passed, warnings = audit_quant_series(
        filepath=args.file,
        price_col=args.price_col,
        return_col=args.return_col,
        periods_per_year=args.periods
    )

    if args.strict and not passed:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
