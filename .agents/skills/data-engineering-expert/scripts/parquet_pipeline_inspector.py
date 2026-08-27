#!/usr/bin/env python3
"""Parquet Pipeline Metadata & Health Inspector.

Inspects Parquet files without loading data into RAM:
- Schema field names, physical types, and nullability
- Number of row groups, rows per group, and byte sizes
- Compression codec and compression ratio
- Column chunk statistics (min, max, null counts)

Usage:
    python parquet_pipeline_inspector.py path/to/file.parquet [--verbose]
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence

BANNER_WIDTH: int = 75


def format_bytes(byte_count: int) -> str:
    """Format integer byte count into human-readable unit string."""
    val: float = float(byte_count)
    for unit in ["B", "KB", "MB", "GB"]:
        if abs(val) < 1024.0:
            return f"{val:.2f} {unit}"
        val /= 1024.0
    return f"{val:.2f} TB"


def inspect_parquet_file(file_path: Path, verbose: bool = False) -> int:
    """Inspect and print detailed metadata from a Parquet file.

    Args:
        file_path: Path to the target Parquet file.
        verbose: If True, prints column-level statistics for every row group.

    Returns:
        0 on success, 1 on inspection failure.
    """
    try:
        import pyarrow.parquet as pq
    except ImportError:
        sys.stderr.write(
            "Error: 'pyarrow' is required to inspect Parquet metadata. Run 'pip install pyarrow'.\n"
        )
        return 1

    if not file_path.is_file():
        sys.stderr.write(f"Error: Target file does not exist: {file_path}\n")
        return 1

    try:
        parquet_file = pq.ParquetFile(file_path)
        meta = parquet_file.metadata
        schema = parquet_file.schema_arrow
    except Exception as exc:
        sys.stderr.write(f"Error reading Parquet metadata from {file_path}: {exc}\n")
        return 1

    total_compressed = meta.serialized_size or file_path.stat().st_size
    total_uncompressed = sum(meta.row_group(i).total_byte_size for i in range(meta.num_row_groups))
    compression_ratio = (
        (total_uncompressed / total_compressed) if total_compressed > 0 else 1.0
    )

    print("\n" + "=" * BANNER_WIDTH)
    print(f" 📦 PARQUET HEALTH & METADATA REPORT: {file_path.name}")
    print("=" * BANNER_WIDTH)

    print(f"📄 File Path         : {file_path.resolve().as_posix()}")
    print(f"📊 Total Rows        : {meta.num_rows:,}")
    print(f"🏛️  Columns Count     : {meta.num_columns}")
    print(f"🗂️  Row Groups Count  : {meta.num_row_groups}")
    print(f"💾 File Size (Disk)  : {format_bytes(total_compressed)}")
    print(f"📈 Uncompressed Size : {format_bytes(total_uncompressed)}")
    print(f"🗜️  Compression Ratio: {compression_ratio:.2f}x")

    # Schema breakdown
    print("\n" + "-" * BANNER_WIDTH)
    print(" 📜 SCHEMA DEFINITION (PyArrow Native)")
    print("-" * BANNER_WIDTH)
    for field_idx in range(len(schema)):
        field = schema.field(field_idx)
        nullable_str = "NULLABLE" if field.nullable else "NOT NULL"
        print(f"  [{field_idx:02d}] {field.name:<28} : {str(field.type):<20} ({nullable_str})")

    # Row Groups breakdown
    print("\n" + "-" * BANNER_WIDTH)
    print(" 🧱 ROW GROUPS & COLUMN CHUNKS")
    print("-" * BANNER_WIDTH)
    for rg_idx in range(meta.num_row_groups):
        rg = meta.row_group(rg_idx)
        rg_compressed = sum(rg.column(c).total_compressed_size for c in range(rg.num_columns))
        print(
            f"  Row Group {rg_idx:02d} ➔ Rows: {rg.num_rows:<10,d} | "
            f"Disk: {format_bytes(rg_compressed):<10} | "
            f"Memory: {format_bytes(rg.total_byte_size):<10}"
        )

        if verbose:
            for col_idx in range(rg.num_columns):
                col_chunk = rg.column(col_idx)
                stats = col_chunk.statistics
                stat_str = ""
                if stats and stats.has_min_max:
                    stat_str = f"| Min: {stats.min} | Max: {stats.max} | Nulls: {stats.null_count}"
                print(
                    f"     • {col_chunk.path_in_schema:<20} "
                    f"[{col_chunk.compression}] {format_bytes(col_chunk.total_compressed_size):<8} "
                    f"{stat_str}"
                )

    print("\n" + "=" * BANNER_WIDTH)
    print(" ✅ Parquet inspection complete. Zero memory overhead.")
    print("=" * BANNER_WIDTH + "\n")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint for Parquet Inspector."""
    parser = argparse.ArgumentParser(description="Parquet Metadata & Health Inspector")
    parser.add_argument("file_path", type=Path, help="Path to Parquet file to analyze")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Print detailed column chunk statistics"
    )
    args = parser.parse_args(argv)
    return inspect_parquet_file(args.file_path, verbose=args.verbose)


if __name__ == "__main__":
    sys.exit(main())
