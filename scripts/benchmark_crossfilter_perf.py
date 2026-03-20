#!/usr/bin/env python3
"""Benchmark cross-filter hot path: old filter+reduce vs new pre-aggregation."""

from __future__ import annotations

import argparse
import json
import re
import statistics
import time
from pathlib import Path
from typing import Any


def parse_chart_data(report_path: Path) -> dict[str, Any]:
    text = report_path.read_text(encoding="utf-8")
    match = re.search(r"const chartData = (.*?);\n\nfunction fmtNum", text, re.S)
    if not match:
        raise ValueError(f"Could not parse chartData block from {report_path}")
    return json.loads(match.group(1))


def normalize_records(chart_data: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    records = (chart_data.get("crossFilter") or {}).get("records") or []
    months = (
        ((chart_data.get("crossFilter") or {}).get("options") or {}).get("months")
        or chart_data.get("months")
        or []
    )
    all_brands = list((chart_data.get("brandMonthlyStacked") or {}).keys())
    normalized = [
        {
            "month": record.get("month"),
            "brand": record.get("brand") or "未知",
            "amount": float(record.get("amount") or 0),
        }
        for record in records
    ]
    return normalized, list(months), all_brands


def old_algo(records: list[dict[str, Any]], month_order: list[str], all_brands: list[str]) -> None:
    month_records_map: dict[str, list[dict[str, Any]]] = {month: [] for month in month_order}
    for record in records:
        month_records_map.setdefault(record["month"], []).append(record)

    amount_by_month_map: dict[str, float] = {}
    for month in month_order:
        month_total = 0.0
        for record in month_records_map.get(month, []):
            month_total += record["amount"]
        amount_by_month_map[month] = month_total

    brand_monthly_stacked = {}
    for brand in all_brands:
        series = []
        for month in month_order:
            brand_total = 0.0
            for record in month_records_map.get(month, []):
                if record["brand"] == brand:
                    brand_total += record["amount"]
            series.append(brand_total)
        brand_monthly_stacked[brand] = series

    monthly_shares_rows = []
    for brand in all_brands:
        row: dict[str, Any] = {"brand": brand}
        for month in month_order:
            month_total = amount_by_month_map.get(month, 0.0)
            brand_total = 0.0
            for record in month_records_map.get(month, []):
                if record["brand"] == brand:
                    brand_total += record["amount"]
            row[month] = (brand_total / month_total * 100.0) if month_total > 0 else 0.0
        monthly_shares_rows.append(row)

    # Keep references alive to avoid over-optimization.
    _ = brand_monthly_stacked, monthly_shares_rows


def new_algo(records: list[dict[str, Any]], month_order: list[str], all_brands: list[str]) -> None:
    month_records_map: dict[str, list[dict[str, Any]]] = {month: [] for month in month_order}
    for record in records:
        month_records_map.setdefault(record["month"], []).append(record)

    amount_by_month_map: dict[str, float] = {}
    monthly_brand_map: dict[str, dict[str, float]] = {}
    for month in month_order:
        month_total = 0.0
        brand_totals: dict[str, float] = {}
        for record in month_records_map.get(month, []):
            amount = record["amount"]
            month_total += amount
            brand = record["brand"]
            brand_totals[brand] = brand_totals.get(brand, 0.0) + amount
        amount_by_month_map[month] = month_total
        monthly_brand_map[month] = brand_totals

    brand_monthly_stacked = {}
    for brand in all_brands:
        brand_monthly_stacked[brand] = [monthly_brand_map.get(month, {}).get(brand, 0.0) for month in month_order]

    monthly_shares_rows = []
    for brand in all_brands:
        row: dict[str, Any] = {"brand": brand}
        for month in month_order:
            month_total = amount_by_month_map.get(month, 0.0)
            brand_total = monthly_brand_map.get(month, {}).get(brand, 0.0)
            row[month] = (brand_total / month_total * 100.0) if month_total > 0 else 0.0
        monthly_shares_rows.append(row)

    _ = brand_monthly_stacked, monthly_shares_rows


def benchmark(fn, records: list[dict[str, Any]], months: list[str], brands: list[str], rounds: int) -> dict[str, float]:
    times: list[float] = []
    for _ in range(3):
        fn(records, months, brands)
    for _ in range(rounds):
        start = time.perf_counter()
        fn(records, months, brands)
        end = time.perf_counter()
        times.append((end - start) * 1000)
    ordered = sorted(times)
    p95_index = max(0, min(len(ordered) - 1, int(len(ordered) * 0.95) - 1))
    return {
        "mean_ms": statistics.mean(times),
        "p50_ms": statistics.median(times),
        "p95_ms": ordered[p95_index],
        "min_ms": min(times),
        "max_ms": max(times),
    }


def parse_scales(scales_text: str) -> list[int]:
    values = []
    for raw in scales_text.split(","):
        value = int(raw.strip())
        if value <= 0:
            raise ValueError("Scale factors must be positive integers")
        values.append(value)
    return values


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark cross-filter hot path")
    parser.add_argument(
        "--report-path",
        default="reports/report_with_data.html",
        help="Path to report_with_data.html",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=12,
        help="Benchmark rounds per algorithm and scale",
    )
    parser.add_argument(
        "--scales",
        default="1,2,4",
        help="Comma-separated dataset scale multipliers (e.g. 1,2,4)",
    )
    args = parser.parse_args()

    chart_data = parse_chart_data(Path(args.report_path))
    records, month_order, all_brands = normalize_records(chart_data)
    scales = parse_scales(args.scales)

    result: dict[str, Any] = {}
    for scale in scales:
        scaled_records = records * scale
        old_stats = benchmark(old_algo, scaled_records, month_order, all_brands, args.rounds)
        new_stats = benchmark(new_algo, scaled_records, month_order, all_brands, args.rounds)
        key = f"{scale}x"
        result[key] = {
            "rows": len(scaled_records),
            "old": old_stats,
            "new": new_stats,
            "speedup_mean": old_stats["mean_ms"] / new_stats["mean_ms"] if new_stats["mean_ms"] else None,
        }

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
