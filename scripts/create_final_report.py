#!/usr/bin/env python3
"""Generate final HTML report with embedded data derived from raw inputs."""

import json
import argparse
from datetime import datetime
from collections import defaultdict
from functools import lru_cache
from typing import Optional
from pathlib import Path

import pandas as pd
import yaml

try:
    from common_data_utils import (
        ensure_brand_column,
        find_date_column,
        infer_brand_from_product_name,
        normalize_sales_columns,
        parse_month_label,
        parse_year_month_key,
        read_sales_excel_auto_sheet,
        sort_month_labels,
        split_sales_by_month,
    )
except ModuleNotFoundError:
    from scripts.common_data_utils import (
        ensure_brand_column,
        find_date_column,
        infer_brand_from_product_name,
        normalize_sales_columns,
        parse_month_label,
        parse_year_month_key,
        read_sales_excel_auto_sheet,
        sort_month_labels,
        split_sales_by_month,
    )

BASE_DIR = Path(__file__).parent.parent
CONFIG_PATH = BASE_DIR / "config.yaml"
REPORT_TEMPLATE = BASE_DIR / "reports" / "business_sales_inventory_report.html"
OUTPUT_REPORT = BASE_DIR / "reports" / "report_with_data.html"
CITY_PROVINCE_PATH = BASE_DIR / "data" / "china_city_province.csv"

DEFAULT_CONFIG = {
    "raw_data_dir": "./raw_data",
    "sales_files": ["202510.xlsx", "202511.xlsx", "202512.xlsx", "202601.xlsx"],
    "inventory_file": "202601库存.xlsx",
    "min_year": None,
    "max_slow_items": 20,
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate final HTML report with embedded data."
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to YAML config file (default: ./config.yaml)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Reserved flag for compatibility with run.sh/run.bat",
    )
    return parser.parse_args()


def load_config(config_path: Optional[Path] = None):
    config = DEFAULT_CONFIG.copy()
    target_config = config_path or CONFIG_PATH
    if target_config.exists():
        with open(target_config, "r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}
        for key in config:
            if key in loaded:
                config[key] = loaded[key]
    return config


def build_report_meta(months: list[str]) -> dict[str, str]:
    ym_pairs = [parse_year_month_key(m) for m in months]
    ym_pairs = [x for x in ym_pairs if x is not None]

    if ym_pairs:
        ym_pairs = sorted(ym_pairs)
        start_year, start_month = ym_pairs[0]
        end_year, end_month = ym_pairs[-1]
        period_text = f"{start_year}年{start_month}月-{end_year}年{end_month}月"
        latest_month = f"{end_year:04d}-{end_month:02d}"
    elif months:
        period_text = f"{months[0]}-{months[-1]}"
        latest_month = months[-1]
    else:
        period_text = "--"
        latest_month = "--"

    return {
        "period_text": period_text,
        "latest_month": latest_month,
        "generated_date": datetime.now().strftime("%Y-%m-%d"),
    }


@lru_cache(maxsize=1)
def load_city_province_pairs() -> list[tuple[str, str]]:
    if not CITY_PROVINCE_PATH.exists():
        print(f"Warning: City-province mapping not found: {CITY_PROVINCE_PATH}")
        return []

    try:
        mapping_df = pd.read_csv(CITY_PROVINCE_PATH, dtype=str, encoding="utf-8-sig")
    except UnicodeDecodeError:
        mapping_df = pd.read_csv(CITY_PROVINCE_PATH, dtype=str, encoding="gbk")
    except Exception as exc:
        print(f"Warning: Could not read city-province mapping: {exc}")
        return []

    if "city" not in mapping_df.columns or "province" not in mapping_df.columns:
        print("Warning: City-province mapping must include 'city' and 'province' columns.")
        return []

    mapping_df = mapping_df.fillna("")
    pairs: list[tuple[str, str]] = []
    for _, row in mapping_df.iterrows():
        city = str(row["city"]).strip()
        province = str(row["province"]).strip()
        if city and province:
            pairs.append((city, province))
    return pairs


@lru_cache(maxsize=8192)
def infer_province_from_store_name(store_name: object) -> str:
    text = str(store_name or "").strip()
    if not text:
        return "未知省份"

    best_start_idx: Optional[int] = None
    best_city_len = -1
    best_province = ""

    for city, province in load_city_province_pairs():
        idx = text.find(city)
        if idx < 0:
            continue
        city_len = len(city)
        if (
            best_start_idx is None
            or idx < best_start_idx
            or (idx == best_start_idx and city_len > best_city_len)
        ):
            best_start_idx = idx
            best_city_len = city_len
            best_province = province

    return best_province if best_province else "未知省份"


def clean_sales_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = df.columns.str.strip()
    df = normalize_sales_columns(df)
    df = ensure_brand_column(df)

    column_map = {
        "销售金额": ["销售金额", "金额", "amount", "sales_amount"],
        "销售数量": ["销售数量", "数量", "quantity", "sales_qty"],
        "销售净额": ["销售净额", "净额", "net_amount", "sales_net"],
    }

    for target, candidates in column_map.items():
        for col in df.columns:
            if col in candidates or target in col:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
                break

    # Keep cleaning behavior aligned with data_processor.py
    critical_fields = ["销售金额", "销售数量"]
    existing_critical = [f for f in critical_fields if f in df.columns]
    if existing_critical:
        df = df.loc[~(df[existing_critical] == 0).all(axis=1)]

    return df


def clean_inventory_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = df.columns.str.strip()
    df = ensure_brand_column(df)
    for col in df.columns:
        if "数量" in col or "quantity" in col.lower():
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


def build_rankings(monthly_series: dict[str, pd.Series], months: list[str], top_n: int = 30):
    total_sales = defaultdict(float)
    for series in monthly_series.values():
        for name, value in series.items():
            total_sales[name] += float(value)

    top_items = [
        name for name, _ in sorted(total_sales.items(), key=lambda x: x[1], reverse=True)[:top_n]
    ]

    monthly_ranks = {}
    for month in months:
        series = monthly_series.get(month, pd.Series(dtype=float))
        sorted_items = series.sort_values(ascending=False)
        monthly_ranks[month] = {name: idx + 1 for idx, name in enumerate(sorted_items.index)}

    ranking_changes = []
    for name in top_items:
        rankings = {}
        trends = {}
        for i, month in enumerate(months):
            curr_rank = monthly_ranks.get(month, {}).get(name)
            rankings[month] = curr_rank if curr_rank is not None else None

            if i == 0 or curr_rank is None:
                trends[month] = None
                continue

            prev_month = months[i - 1]
            prev_rank = monthly_ranks.get(prev_month, {}).get(name)
            if prev_rank is None:
                trends[month] = {"direction": "new", "change": None}
            elif curr_rank < prev_rank:
                trends[month] = {"direction": "up", "change": prev_rank - curr_rank}
            elif curr_rank > prev_rank:
                trends[month] = {"direction": "down", "change": curr_rank - prev_rank}
            else:
                trends[month] = {"direction": "stable", "change": 0}

        ranking_changes.append({"name": name, "rankings": rankings, "trends": trends})

    return ranking_changes


def main(config_file: Optional[str] = None):
    config_path = None
    if config_file:
        config_path = Path(config_file)
        if not config_path.is_absolute():
            config_path = (BASE_DIR / config_path).resolve()

    config = load_config(config_path)

    raw_data_dir = Path(config["raw_data_dir"])
    if not raw_data_dir.is_absolute():
        raw_data_dir = (BASE_DIR / raw_data_dir).resolve()

    sales_files = config.get("sales_files") or DEFAULT_CONFIG["sales_files"]
    inventory_file = config.get("inventory_file") or DEFAULT_CONFIG["inventory_file"]
    min_year = config.get("min_year", DEFAULT_CONFIG["min_year"])
    if min_year in ("", None):
        min_year = None
    else:
        try:
            min_year = int(min_year)
        except (TypeError, ValueError):
            print(f"Warning: Invalid min_year={min_year}, fallback to no year filter")
            min_year = None
    max_slow_items = config.get("max_slow_items") or DEFAULT_CONFIG["max_slow_items"]

    if not REPORT_TEMPLATE.exists():
        raise FileNotFoundError(f"Report template not found: {REPORT_TEMPLATE}")

    sales_data: dict[str, pd.DataFrame] = {}
    months: list[str] = []
    total_records_count = 0

    for filename in sales_files:
        filepath = raw_data_dir / filename
        if not filepath.exists():
            print(f"Warning: Sales file not found: {filepath}")
            continue
        try:
            df, selected_sheet = read_sales_excel_auto_sheet(filepath)
            df = clean_sales_df(df)
            if selected_sheet != "Sheet1":
                print(f"Info: {filename} selected sheet -> {selected_sheet}")
            fallback_month = parse_month_label(filename)
            monthly_frames = split_sales_by_month(df, fallback_month)
            for month_label, month_df in monthly_frames.items():
                ym = parse_year_month_key(month_label)
                if min_year is not None and ym and ym[0] < min_year:
                    continue
                if month_label in sales_data:
                    sales_data[month_label] = pd.concat(
                        [sales_data[month_label], month_df],
                        ignore_index=True
                    )
                else:
                    sales_data[month_label] = month_df
                    months.append(month_label)
        except Exception as e:
            print(f"Warning: Could not process {filename}: {e}")

    if not sales_data:
        raise FileNotFoundError("No sales data files were loaded.")

    # Normalize month order for stable chronological reporting
    months = sort_month_labels([m for m in months if m in sales_data])
    total_records_count = int(sum(len(sales_data[m]) for m in months))
    report_meta = build_report_meta(months)

    latest_month = report_meta["latest_month"] if report_meta["latest_month"] in sales_data else months[-1]
    report_meta["latest_month"] = latest_month
    latest_df = sales_data[latest_month]
    total_stores_latest_month = int(latest_df["门店名称"].nunique()) if "门店名称" in latest_df.columns else 0

    # Monthly store stats and trends
    monthly_store_stats = []
    monthly_sales = []
    monthly_qty = []
    monthly_qty_by_month = {}
    for month in months:
        df = sales_data[month]
        store_count = int(df["门店名称"].nunique()) if "门店名称" in df.columns else 0
        total_amount = float(df["销售金额"].sum()) if "销售金额" in df.columns else 0.0
        total_qty = float(df["销售数量"].sum()) if "销售数量" in df.columns else 0.0
        avg_price = total_amount / total_qty if total_qty > 0 else 0.0
        monthly_store_stats.append({
            "month": month,
            "storeCount": store_count,
            "salesQty": int(total_qty),
            "salesAmount": round(total_amount, 2),
            "avgPrice": round(avg_price, 2),
        })
        monthly_sales.append(round(total_amount, 2))
        monthly_qty.append(round(total_qty, 1))
        monthly_qty_by_month[month] = float(total_qty)

    # Daily sales
    daily_sales_map = defaultdict(float)
    for df in sales_data.values():
        date_col = find_date_column(df)
        if not date_col or "销售金额" not in df.columns:
            continue
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.dropna(subset=[date_col])
        df["__date"] = df[date_col].dt.strftime("%Y-%m-%d")
        daily = df.groupby("__date")["销售金额"].sum()
        for date, value in daily.items():
            daily_sales_map[date] += float(value)

    daily_sales = [
        {"date": date, "value": round(value, 2)}
        for date, value in sorted(daily_sales_map.items())
    ]

    # Build concatenated data with month label for cross filtering
    all_sales = pd.concat(
        [sales_data[month].assign(__month=month) for month in months],
        ignore_index=True
    )

    # Cross-filter dataset (month/province/store/brand)
    filter_records = []
    filter_options = {"months": months, "stores": [], "brands": [], "provinces": []}
    if not all_sales.empty:
        filter_df = all_sales.copy()

        # Normalize dimension fields
        for text_col in ["__month", "门店名称", "品牌", "商品名称"]:
            if text_col not in filter_df.columns:
                filter_df[text_col] = "未知"
            filter_df[text_col] = (
                filter_df[text_col]
                .fillna("未知")
                .astype(str)
                .str.strip()
                .replace("", "未知")
            )

        for numeric_col in ["销售金额", "销售数量", "销售净额"]:
            if numeric_col not in filter_df.columns:
                filter_df[numeric_col] = 0
            filter_df[numeric_col] = pd.to_numeric(filter_df[numeric_col], errors="coerce").fillna(0)

        date_col = find_date_column(filter_df)
        if date_col:
            parsed_date = pd.to_datetime(filter_df[date_col], errors="coerce")
            filter_df["__date"] = parsed_date.dt.strftime("%Y-%m-%d").fillna("")
        else:
            filter_df["__date"] = ""

        filter_df["__province"] = filter_df["门店名称"].apply(infer_province_from_store_name)

        filter_options["stores"] = sorted(filter_df["门店名称"].unique().tolist())
        filter_options["brands"] = sorted(filter_df["品牌"].unique().tolist())
        filter_options["provinces"] = sorted(filter_df["__province"].unique().tolist())

        agg_keys = ["__month", "__province", "门店名称", "品牌", "商品名称", "__date"]
        aggregated_filter_df = (
            filter_df.groupby(agg_keys, dropna=False, as_index=False)[["销售金额", "销售数量", "销售净额"]]
            .sum()
            .sort_values(agg_keys)
        )

        filter_records = [
            {
                "month": row["__month"],
                "province": row["__province"],
                "store": row["门店名称"],
                "brand": row["品牌"],
                "product": row["商品名称"],
                "date": row["__date"],
                "amount": round(float(row["销售金额"]), 2),
                "qty": float(row["销售数量"]),
                "net": round(float(row["销售净额"]), 2),
            }
            for _, row in aggregated_filter_df.iterrows()
        ]

    # Brand data
    monthly_brand_sales = {}
    monthly_brand_qty = {}
    for month in months:
        df = sales_data[month]
        if "品牌" in df.columns and "销售金额" in df.columns:
            monthly_brand_sales[month] = df.groupby("品牌")["销售金额"].sum()
        else:
            monthly_brand_sales[month] = pd.Series(dtype=float)
        if "品牌" in df.columns and "销售数量" in df.columns:
            monthly_brand_qty[month] = df.groupby("品牌")["销售数量"].sum()
        else:
            monthly_brand_qty[month] = pd.Series(dtype=float)

    preferred_brand_order = ["伊利", "秦俑", "君乐宝", "佳贝艾特"]
    detected_brands = set()
    brand_sales_totals = defaultdict(float)
    for month in months:
        for brand, value in monthly_brand_sales[month].items():
            detected_brands.add(brand)
            brand_sales_totals[brand] += float(value)

    sorted_detected_brands = [
        b for b, _ in sorted(brand_sales_totals.items(), key=lambda x: x[1], reverse=True)
    ]
    brand_order = [b for b in preferred_brand_order if b in detected_brands]
    brand_order.extend([b for b in sorted_detected_brands if b not in brand_order])
    if not brand_order:
        brand_order = preferred_brand_order.copy()

    brand_monthly_stacked = {brand: [] for brand in brand_order}

    for brand in brand_order:
        for month in months:
            brand_monthly_stacked[brand].append(round(float(monthly_brand_sales[month].get(brand, 0.0)), 2))

    total_sales_all = float(all_sales["销售金额"].sum()) if "销售金额" in all_sales.columns else 0.0
    total_qty_all = float(all_sales["销售数量"].sum()) if "销售数量" in all_sales.columns else 0.0

    brand_total_sales = {brand: sum(brand_monthly_stacked[brand]) for brand in brand_order}
    brand_total_qty = {
        brand: float(sum(monthly_brand_qty[month].get(brand, 0.0) for month in months))
        for brand in brand_order
    }

    brand_shares = [
        round(brand_total_sales[brand] / total_sales_all * 100, 1) if total_sales_all > 0 else 0
        for brand in brand_order
    ]
    brand_qty_shares = [
        round(brand_total_qty[brand] / total_qty_all * 100, 1) if total_qty_all > 0 else 0
        for brand in brand_order
    ]
    brand_qty_values = [int(brand_total_qty[brand]) for brand in brand_order]

    brand_cumulative_data = [
        {
            "name": brand,
            "amount": int(brand_total_sales[brand]),
            "qty": int(brand_total_qty[brand]),
            "amountShare": brand_shares[i],
            "qtyShare": brand_qty_shares[i],
        }
        for i, brand in enumerate(brand_order)
    ]

    latest_month_total = float(sales_data[latest_month]["销售金额"].sum()) if "销售金额" in sales_data[latest_month].columns else 0.0
    latest_month_qty_total = float(sales_data[latest_month]["销售数量"].sum()) if "销售数量" in sales_data[latest_month].columns else 0.0
    brand_current_data = []
    for brand in brand_order:
        amount = float(monthly_brand_sales[latest_month].get(brand, 0.0))
        qty = float(monthly_brand_qty[latest_month].get(brand, 0.0))
        amount_share = round(amount / latest_month_total * 100, 1) if latest_month_total > 0 else 0
        qty_share = round(qty / latest_month_qty_total * 100, 1) if latest_month_qty_total > 0 else 0
        brand_current_data.append({
            "name": brand,
            "amount": int(amount),
            "qty": int(qty),
            "amountShare": amount_share,
            "qtyShare": qty_share,
        })

    # Brand monthly share table data
    brand_monthly_shares = []
    for brand in brand_order:
        share_row = {"brand": brand}
        for month in months:
            month_total = float(monthly_brand_sales[month].sum()) if not monthly_brand_sales[month].empty else 0.0
            brand_value = float(monthly_brand_sales[month].get(brand, 0.0))
            share = round(brand_value / month_total * 100, 1) if month_total > 0 else 0
            share_row[month] = share
        brand_monthly_shares.append(share_row)

    # Product sales per month
    monthly_product_sales = {}
    monthly_product_qty = {}
    for month in months:
        df = sales_data[month]
        if "商品名称" in df.columns and "销售金额" in df.columns:
            monthly_product_sales[month] = df.groupby("商品名称")["销售金额"].sum()
        else:
            monthly_product_sales[month] = pd.Series(dtype=float)
        if "商品名称" in df.columns and "销售数量" in df.columns:
            monthly_product_qty[month] = df.groupby("商品名称")["销售数量"].sum()
        else:
            monthly_product_qty[month] = pd.Series(dtype=float)

    # Top 20 products by total sales
    product_total_sales = defaultdict(float)
    for series in monthly_product_sales.values():
        for name, value in series.items():
            product_total_sales[name] += float(value)

    top20_products = [
        {"name": name, "value": int(value)}
        for name, value in sorted(product_total_sales.items(), key=lambda x: x[1], reverse=True)[:20]
    ]

    # Top 20 products by total quantity
    product_total_qty = defaultdict(float)
    for series in monthly_product_qty.values():
        for name, value in series.items():
            product_total_qty[name] += float(value)

    top20_products_qty = [
        {"name": name, "value": int(value)}
        for name, value in sorted(product_total_qty.items(), key=lambda x: x[1], reverse=True)[:20]
    ]

    # Product stability (Top10 each month)
    product_top10_map = {}
    for month, series in monthly_product_sales.items():
        product_top10_map[month] = list(series.sort_values(ascending=False).head(10).index)

    product_stats = []
    top_products = set()
    for products in product_top10_map.values():
        top_products.update(products)

    for product in top_products:
        months_in_top10 = 0
        total_top10_sales = 0.0
        for month in months:
            if product in product_top10_map[month]:
                months_in_top10 += 1
                total_top10_sales += float(monthly_product_sales[month].get(product, 0.0))
        product_stats.append({
            "name": product,
            "months": months_in_top10,
            "sales": int(total_top10_sales),
        })

    product_stats = sorted(product_stats, key=lambda x: (-x["months"], -x["sales"]))

    # Product concentration (Top10 by total sales)
    top10_products = sorted(product_total_sales.items(), key=lambda x: x[1], reverse=True)[:10]
    product_concentration_sales = [int(value) for _, value in top10_products]
    product_concentration_labels = [str(name)[:15] for name, _ in top10_products]
    running_total = 0.0
    product_concentration_cumulative = []
    for _, value in top10_products:
        running_total += float(value)
        product_concentration_cumulative.append(
            round(running_total / total_sales_all * 100, 1) if total_sales_all > 0 else 0
        )

    # Store sales per month
    monthly_store_sales = {}
    monthly_store_qty = {}
    for month in months:
        df = sales_data[month]
        if "门店名称" in df.columns and "销售金额" in df.columns:
            monthly_store_sales[month] = df.groupby("门店名称")["销售金额"].sum()
        else:
            monthly_store_sales[month] = pd.Series(dtype=float)
        if "门店名称" in df.columns and "销售数量" in df.columns:
            monthly_store_qty[month] = df.groupby("门店名称")["销售数量"].sum()
        else:
            monthly_store_qty[month] = pd.Series(dtype=float)

    store_total_sales = defaultdict(float)
    store_total_qty = defaultdict(float)
    for month in months:
        for name, value in monthly_store_sales[month].items():
            store_total_sales[name] += float(value)
        for name, value in monthly_store_qty[month].items():
            store_total_qty[name] += float(value)

    top20_stores = [
        {"name": name, "value": int(value)}
        for name, value in sorted(store_total_sales.items(), key=lambda x: x[1], reverse=True)[:20]
    ]

    # Store stability (Top20 per month)
    store_top20_map = {}
    for month, series in monthly_store_sales.items():
        store_top20_map[month] = list(series.sort_values(ascending=False).head(20).index)

    store_stats = []
    top_stores = set()
    for stores in store_top20_map.values():
        top_stores.update(stores)

    for store in top_stores:
        months_in_top20 = 0
        total_top20_sales = 0.0
        for month in months:
            if store in store_top20_map[month]:
                months_in_top20 += 1
                total_top20_sales += float(monthly_store_sales[month].get(store, 0.0))
        store_stats.append({
            "name": store,
            "months": months_in_top20,
            "sales": int(total_top20_sales),
        })

    store_stats = sorted(store_stats, key=lambda x: (-x["months"], -x["sales"]))[:20]

    # Store concentration cumulative (Top5/10/15/20)
    sorted_store_totals = [value for _, value in sorted(store_total_sales.items(), key=lambda x: x[1], reverse=True)]
    total_store_sales_sum = sum(sorted_store_totals)
    store_concentration_labels = []
    store_concentration_cumulative = []
    for cutoff in [5, 10, 15, 20]:
        if len(sorted_store_totals) >= cutoff:
            store_concentration_labels.append(f"Top{cutoff}")
            share = sum(sorted_store_totals[:cutoff]) / total_store_sales_sum * 100 if total_store_sales_sum > 0 else 0
            store_concentration_cumulative.append(round(share, 1))

    # Store average price data
    store_avg_price_data = []
    for store, sales_amount in store_total_sales.items():
        qty = store_total_qty.get(store, 0.0)
        avg_price = sales_amount / qty if qty > 0 else 0.0
        store_avg_price_data.append({
            "name": store,
            "avgPrice": round(avg_price, 2),
            "sales": int(sales_amount),
            "qty": int(qty),
        })

    store_avg_price_sorted = sorted(store_avg_price_data, key=lambda x: x["avgPrice"], reverse=True)

    # Store classification & scatter
    avg_sales_values = [s["sales"] for s in store_avg_price_data] or [0]
    avg_price_values = [s["avgPrice"] for s in store_avg_price_data] or [0]
    sales_threshold = sorted(avg_sales_values)[len(avg_sales_values) // 2]
    price_threshold = sorted(avg_price_values)[len(avg_price_values) // 2]

    store_classification = {"star": [], "potential": [], "volume": [], "improve": []}
    scatter_data = []
    category_colors = {
        "star": "#4caf50",
        "potential": "#2196f3",
        "volume": "#ff9800",
        "improve": "#9e9e9e",
    }

    for store in store_avg_price_data:
        is_high_sales = store["sales"] >= sales_threshold
        is_high_price = store["avgPrice"] >= price_threshold

        if is_high_sales and is_high_price:
            category = "star"
        elif not is_high_sales and is_high_price:
            category = "potential"
        elif is_high_sales and not is_high_price:
            category = "volume"
        else:
            category = "improve"

        store_classification[category].append(store)
        scatter_data.append({
            "x": store["qty"],
            "y": store["avgPrice"],
            "name": store["name"],
            "category": category,
            "color": category_colors[category],
        })

    # Ranking changes
    product_ranking_changes = []
    store_ranking_changes = []

    product_changes = build_rankings(monthly_product_sales, months, top_n=30)
    for item in product_changes:
        product_ranking_changes.append({
            "product": item["name"],
            "rankings": item["rankings"],
            "trends": item["trends"],
        })

    store_changes = build_rankings(monthly_store_sales, months, top_n=30)
    for item in store_changes:
        store_ranking_changes.append({
            "store": item["name"],
            "rankings": item["rankings"],
            "trends": item["trends"],
        })

    # New product contributions
    seen_products = set()
    new_product_contributions = []
    for month in months:
        products_in_month = set(monthly_product_sales[month].index)
        new_products = products_in_month - seen_products
        seen_products.update(products_in_month)

        new_product_list = []
        new_sales_amount = 0.0
        new_sales_qty = 0.0
        for product in new_products:
            sales_amount = float(monthly_product_sales[month].get(product, 0.0))
            sales_qty = float(monthly_product_qty[month].get(product, 0.0))
            new_sales_amount += sales_amount
            new_sales_qty += sales_qty
            new_product_list.append({
                "product": product,
                "sales_amount": round(sales_amount, 2),
                "sales_qty": int(sales_qty),
            })

        month_total_amount = float(monthly_product_sales[month].sum()) if not monthly_product_sales[month].empty else 0.0
        month_total_qty = float(monthly_product_qty[month].sum()) if not monthly_product_qty[month].empty else 0.0

        amount_contribution = round(new_sales_amount / month_total_amount * 100, 1) if month_total_amount > 0 else 0
        qty_contribution = round(new_sales_qty / month_total_qty * 100, 1) if month_total_qty > 0 else 0

        new_product_contributions.append({
            "month": month,
            "new_product_count": len(new_products),
            "new_sales_amount": round(new_sales_amount, 2),
            "new_sales_qty": int(new_sales_qty),
            "amount_contribution": amount_contribution,
            "qty_contribution": qty_contribution,
            "new_products": sorted(new_product_list, key=lambda x: x["sales_amount"], reverse=True),
        })

    new_product_contributions = new_product_contributions[-2:]

    # Inventory data
    inventory_data = []
    inventory_df = None
    inv_path = raw_data_dir / inventory_file
    if inv_path.exists():
        try:
            inventory_df = pd.read_excel(inv_path, sheet_name=0)
            inventory_df = clean_inventory_df(inventory_df)
        except Exception as e:
            print(f"Warning: Could not load inventory file: {e}")

    inventory_totals = defaultdict(float)
    inventory_barcode = {}
    inventory_brand = {}
    if inventory_df is not None and "商品名称" in inventory_df.columns:
        qty_col = None
        for col in inventory_df.columns:
            if "数量" in col or "quantity" in col.lower():
                qty_col = col
                break
        if qty_col:
            inventory_totals = inventory_df.groupby("商品名称")[qty_col].sum().to_dict()

        barcode_col = None
        if "商品编码.1" in inventory_df.columns:
            barcode_col = "商品编码.1"
        elif "商品编码" in inventory_df.columns:
            barcode_col = "商品编码"

        if barcode_col:
            for _, row in inventory_df.iterrows():
                name = row.get("商品名称")
                if name and name not in inventory_barcode:
                    barcode = row.get(barcode_col)
                    if pd.notna(barcode):
                        inventory_barcode[name] = str(barcode)

        brand_col = None
        if "品牌" in inventory_df.columns:
            brand_col = "品牌"
        else:
            for col in inventory_df.columns:
                if "品牌" in str(col):
                    brand_col = col
                    break

        for _, row in inventory_df.iterrows():
            name = row.get("商品名称")
            if not name:
                continue
            name = str(name).strip()
            if not name:
                continue

            brand_value = ""
            if brand_col:
                raw_brand = row.get(brand_col)
                if pd.notna(raw_brand):
                    brand_value = str(raw_brand).strip()
            if not brand_value:
                brand_value = infer_brand_from_product_name(name)

            current_brand = inventory_brand.get(name)
            if not current_brand or current_brand in {"其他", "未知"}:
                inventory_brand[name] = brand_value

    recent_months = months[-3:] if len(months) >= 3 else months
    for product, inventory_qty in inventory_totals.items():
        sales_qty_values = [
            float(monthly_product_qty[month].get(product, 0.0))
            for month in recent_months
        ]
        avg_sales_qty = sum(sales_qty_values) / len(sales_qty_values) if sales_qty_values else 0.0
        ratio = inventory_qty / avg_sales_qty if avg_sales_qty > 0 else 999
        inventory_data.append({
            "name": product,
            "brand": inventory_brand.get(product, infer_brand_from_product_name(product)),
            "barcode": inventory_barcode.get(product, "-"),
            "inventory": int(inventory_qty),
            "avgSales": round(avg_sales_qty, 2),
            "ratio": round(ratio, 2) if ratio < 999 else 999,
        })

    inventory_data = sorted(inventory_data, key=lambda x: x["ratio"], reverse=True)

    total_inventory_qty = sum(item["inventory"] for item in inventory_data)
    latest_month_sales_qty = float(monthly_qty_by_month.get(latest_month, monthly_qty[-1] if monthly_qty else 0.0))
    turnover_ratio = latest_month_sales_qty / total_inventory_qty if total_inventory_qty > 0 else 0

    # Appendix: data sources & quality
    data_source_items = [f"{month}销售数据" for month in months]
    if inventory_file:
        inv_label = parse_month_label(inventory_file)
        data_source_items.append(f"{inv_label}库存数据")

    total_fields = int(all_sales.shape[1]) if not all_sales.empty else 0
    key_columns = ["商品名称", "品牌", "门店名称", "销售金额", "销售数量"]
    date_column = find_date_column(all_sales)
    if date_column:
        key_columns.append(date_column)
    key_columns = [c for c in key_columns if c in all_sales.columns]

    if key_columns and not all_sales.empty:
        completeness = all_sales[key_columns].notna().mean().mean() * 100
    else:
        completeness = 0.0

    negative_amount = int((all_sales["销售金额"] < 0).sum()) if "销售金额" in all_sales.columns else 0
    negative_qty = int((all_sales["销售数量"] < 0).sum()) if "销售数量" in all_sales.columns else 0

    # Radar data (Top 5 stores)
    top5_stores = [s["name"] for s in top20_stores[:5]]
    store_product_counts = defaultdict(int)
    store_day_counts = defaultdict(int)

    if "门店名称" in all_sales.columns:
        if "商品名称" in all_sales.columns:
            store_product_counts = all_sales.groupby("门店名称")["商品名称"].nunique().to_dict()
        date_col = find_date_column(all_sales)
        if date_col:
            temp = all_sales.copy()
            temp[date_col] = pd.to_datetime(temp[date_col], errors="coerce")
            temp = temp.dropna(subset=[date_col])
            temp["__date"] = temp[date_col].dt.strftime("%Y-%m-%d")
            store_day_counts = temp.groupby("门店名称")["__date"].nunique().to_dict()

    max_sales = max(store_total_sales.values()) if store_total_sales else 1
    max_avg_price = max((s["avgPrice"] for s in store_avg_price_data), default=1)
    max_sku = max(store_product_counts.values(), default=1)
    max_days = max(store_day_counts.values(), default=1)

    radar_data = []
    for store in top5_stores:
        total_sales = store_total_sales.get(store, 0.0)
        total_qty = store_total_qty.get(store, 0.0)
        avg_price = total_sales / total_qty if total_qty > 0 else 0.0
        sku_count = store_product_counts.get(store, 0)
        day_count = store_day_counts.get(store, 0)

        sales_score = min(total_sales / max_sales * 100, 100) if max_sales > 0 else 0
        price_score = min(avg_price / max_avg_price * 100, 100) if max_avg_price > 0 else 0
        sku_score = min(sku_count / max_sku * 100, 100) if max_sku > 0 else 0
        day_score = min(day_count / max_days * 100, 100) if max_days > 0 else 0
        turnover_score = min(turnover_ratio * 100, 100)

        radar_data.append({
            "label": store,
            "data": [
                round(sales_score, 1),
                round(price_score, 1),
                round(sku_score, 1),
                round(day_score, 1),
                round(turnover_score, 1),
            ],
        })

    # Build chartData
    chart_data = {
        "monthlySales": monthly_sales,
        "monthlyQty": monthly_qty,
        "months": months,
        "dailySales": daily_sales,
        "brandMonthlyStacked": brand_monthly_stacked,
        "brandOrder": brand_order,
        "brandShares": brand_shares,
        "brandQtyShares": brand_qty_shares,
        "brandQty": brand_qty_values,
        "top20Products": top20_products,
        "top20ProductsQty": top20_products_qty,
        "top20Stores": top20_stores,
        "productStability": product_stats[:20],
        "storeStability": store_stats,
        "productConcentration": {
            "labels": product_concentration_labels,
            "sales": product_concentration_sales,
            "cumulative": product_concentration_cumulative,
        },
        "storeConcentration": {
            "labels": store_concentration_labels,
            "cumulative": store_concentration_cumulative,
        },
        "inventoryData": inventory_data,
        "radarData": radar_data,
        "brandMonthlyShares": brand_monthly_shares,
        "productRankingChanges": product_ranking_changes,
        "storeRankingChanges": store_ranking_changes,
        "newProductContributions": new_product_contributions,
        "turnoverRatio": round(turnover_ratio, 2),
        "storeAvgPriceData": store_avg_price_sorted,
        "brandCumulativeData": brand_cumulative_data,
        "brandCurrentData": brand_current_data,
        "dataSourceFiles": ", ".join(sales_files),
        "reportMeta": {
            "period": report_meta["period_text"],
            "generatedDate": report_meta["generated_date"],
            "latestMonth": report_meta["latest_month"],
        },
        "storeClassification": store_classification,
        "storeScatterData": scatter_data,
        "totalRecordsCount": total_records_count,
        "totalStoresLatestMonth": total_stores_latest_month,
        "monthlyStoreStats": monthly_store_stats[-12:],
        "dataSourceItems": data_source_items,
        "dataQuality": {
            "totalRows": total_records_count,
            "totalFields": total_fields,
            "keyCompleteness": round(completeness, 1),
            "negativeAmount": negative_amount,
            "negativeQty": negative_qty,
        },
        "maxSlowItems": int(max_slow_items),
        "crossFilter": {
            "options": filter_options,
            "records": filter_records,
        },
    }

    with open(REPORT_TEMPLATE, "r", encoding="utf-8") as f:
        html_template = f.read()

    chartdata_js = f"const chartData = {json.dumps(chart_data, ensure_ascii=False)};"

    start_marker = "const chartData ="
    start_idx = html_template.find(start_marker)
    if start_idx == -1:
        raise ValueError("Could not find chartData block in template.")

    end_idx = html_template.find(";", start_idx)
    while end_idx != -1 and html_template[end_idx - 1] != "}":
        end_idx = html_template.find(";", end_idx + 1)
    if end_idx == -1:
        raise ValueError("Could not find end of chartData block in template.")

    new_html = html_template[:start_idx] + chartdata_js + html_template[end_idx + 1 :]

    with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
        f.write(new_html)

    print(f"✓ Final report: {OUTPUT_REPORT}")
    print(f"  Size: {len(new_html):,} bytes")
    print()
    print("【数据概览】")
    print(f"  月份数: {len(months)}")
    print(f"  品牌: {brand_order}")
    print(f"  门店: {len(store_total_sales)}")
    print(f"  产品稳定性: {len(product_stats)}")
    print(f"  库存项: {len(inventory_data)}")
    print(f"  日销售记录: {len(daily_sales)}")


if __name__ == "__main__":
    args = parse_args()
    main(config_file=args.config)
