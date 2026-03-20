#!/usr/bin/env python3
"""Shared data utility helpers for report/data pipelines."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import pandas as pd

BRAND_KEYWORDS = [
    "伊利",
    "蒙牛",
    "南国",
    "阿宝乐",
    "畅鲜选",
    "蜀珑珠",
    "永璞",
    "雅士利",
    "大漠银根",
    "谷栗村",
    "君乐宝",
    "秦俑",
    "红色拖拉机",
    "Seesaw",
    "佳贝艾特",
]


def parse_month_label(filename: str) -> str:
    """
    Extract month key from filename.

    Supports flexible names such as:
    - 202602.xlsx
    - 陕西华润销售202602.xlsx
    - sales_202602_detail.xlsx
    """
    match = re.search(r"((?:19|20)\d{2})(0[1-9]|1[0-2])", filename)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    return Path(filename).stem


def parse_year_month_key(label: str) -> Optional[tuple[int, int]]:
    match = re.fullmatch(r"(\d{4})-(\d{2})", str(label or ""))
    if not match:
        return None
    year = int(match.group(1))
    month = int(match.group(2))
    if 1 <= month <= 12:
        return (year, month)
    return None


def sort_month_labels(labels: list[str]) -> list[str]:
    """Sort valid YYYY-MM labels chronologically, keeping unknown labels stable at the end."""
    indexed = list(enumerate(labels))
    sorted_items = sorted(
        indexed,
        key=lambda item: (
            0 if parse_year_month_key(item[1]) is not None else 1,
            parse_year_month_key(item[1])[0] if parse_year_month_key(item[1]) else 0,
            parse_year_month_key(item[1])[1] if parse_year_month_key(item[1]) else 0,
            item[0],
        ),
    )
    return [label for _, label in sorted_items]


def find_date_column(df: pd.DataFrame) -> Optional[str]:
    for col in df.columns:
        col_text = str(col)
        if "日期" in col_text or "时间" in col_text or "date" in col_text.lower():
            return col
    return None


def find_product_name_column(df: pd.DataFrame) -> Optional[str]:
    candidates = ["商品名称", "产品名称", "商品", "product", "sku_name"]
    for col in candidates:
        if col in df.columns:
            return col
    for col in df.columns:
        col_lower = str(col).lower()
        if "商品" in str(col) or "产品" in str(col) or "product" in col_lower:
            return col
    return None


def infer_brand_from_product_name(product_name: object) -> str:
    text = str(product_name or "")
    if not text:
        return "其他"
    lowered = text.lower()
    matched = "其他"
    for brand in BRAND_KEYWORDS:
        if brand.lower() in lowered:
            matched = brand
    return matched


def ensure_brand_column(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    has_brand = "品牌" in df.columns
    if not has_brand:
        for col in df.columns:
            if col != "品牌" and "品牌" in str(col):
                df = df.rename(columns={col: "品牌"})
                has_brand = True
                break

    product_col = find_product_name_column(df)

    if not has_brand:
        if product_col:
            brand_series = df[product_col].apply(infer_brand_from_product_name)
            insert_at = df.columns.get_loc(product_col)
            df.insert(insert_at, "品牌", brand_series)
        else:
            df["品牌"] = "其他"
    else:
        brand_values = df["品牌"]
        missing_brand_mask = brand_values.isna() | brand_values.astype(str).str.strip().eq("")
        if product_col and missing_brand_mask.any():
            inferred_brands = df.loc[missing_brand_mask, product_col].apply(infer_brand_from_product_name)
            df.loc[missing_brand_mask, "品牌"] = inferred_brands
        df["品牌"] = (
            df["品牌"]
            .fillna("其他")
            .astype(str)
            .str.strip()
            .replace("", "其他")
        )

    return df


def normalize_sales_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize heterogeneous sales schemas into canonical column names.

    Canonical columns:
    - 销售时间
    - 门店名称
    - 商品名称
    - 销售金额
    - 销售数量
    - 销售净额
    """
    df = df.copy()
    df.columns = [str(col).strip() for col in df.columns]

    def find_column(
        aliases: list[str],
        contains_keywords: Optional[list[str]] = None,
        exclude_keywords: Optional[list[str]] = None,
    ) -> Optional[str]:
        contains_keywords = contains_keywords or []
        exclude_keywords = exclude_keywords or []

        # Exact match first
        for alias in aliases:
            if alias in df.columns:
                return alias

        # Case-insensitive exact match
        lower_map = {str(col).lower(): col for col in df.columns}
        for alias in aliases:
            hit = lower_map.get(alias.lower())
            if hit is not None:
                return hit

        # Keyword contains fallback
        for col in df.columns:
            col_text = str(col).strip()
            col_lower = col_text.lower()
            if any(ex_kw.lower() in col_lower for ex_kw in exclude_keywords):
                continue
            if any(kw.lower() in col_lower for kw in contains_keywords):
                return col

        return None

    rename_pairs: list[tuple[str, str]] = []
    mappings = {
        "销售时间": {
            "aliases": ["销售时间", "销售日期", "日期", "时间", "date"],
            "contains": ["日期", "时间", "date"],
            "exclude": [],
        },
        "门店名称": {
            "aliases": ["门店名称", "门店", "store_name", "store"],
            "contains": ["门店", "store"],
            "exclude": [],
        },
        "商品名称": {
            "aliases": ["商品名称", "产品名称", "商品", "product_name", "sku_name"],
            "contains": ["商品", "产品", "product", "sku"],
            "exclude": [],
        },
        "销售金额": {
            "aliases": ["销售金额", "含税销售额/元", "含税销售额", "含税销售金额", "销售额", "金额", "amount", "sales_amount"],
            "contains": ["销售额", "销售金额", "amount"],
            "exclude": ["线上"],
        },
        "销售数量": {
            "aliases": ["销售数量", "数量", "qty", "quantity", "sales_qty"],
            "contains": ["销售数量", "数量", "qty", "quantity"],
            "exclude": ["线上"],
        },
        "销售净额": {
            "aliases": ["销售净额", "净额", "net_amount", "sales_net"],
            "contains": ["销售净额", "净额", "net"],
            "exclude": ["成本"],
        },
    }

    for target, rules in mappings.items():
        if target in df.columns:
            continue
        source = find_column(
            aliases=rules["aliases"],
            contains_keywords=rules["contains"],
            exclude_keywords=rules["exclude"],
        )
        if source and source != target:
            rename_pairs.append((source, target))

    if rename_pairs:
        df = df.rename(columns={source: target for source, target in rename_pairs})

    return df


def _score_sales_sheet(df: pd.DataFrame) -> int:
    """Score a sheet for how likely it is to be row-level sales detail."""
    if df is None or df.empty:
        return 0

    cols = [str(col).strip() for col in df.columns]
    if not cols:
        return 0

    non_unnamed = sum(1 for col in cols if col and not col.startswith("Unnamed"))
    if non_unnamed == 0:
        return 0

    score = non_unnamed
    normalized = normalize_sales_columns(df)

    if find_date_column(normalized):
        score += 20
    if find_product_name_column(normalized):
        score += 20
    if "门店名称" in normalized.columns:
        score += 20
    if "销售金额" in normalized.columns:
        score += 20
    if "销售数量" in normalized.columns:
        score += 15
    if "品牌" in normalized.columns or any("品牌" in str(c) for c in normalized.columns):
        score += 5

    return score


def read_sales_excel_auto_sheet(file_path: Path | str) -> tuple[pd.DataFrame, str]:
    """
    Read an Excel sales file and auto-select the most plausible detail sheet.

    Returns:
        (dataframe, selected_sheet_name)
    """
    excel = pd.ExcelFile(file_path)
    best_sheet: Optional[str] = None
    best_score = -1
    best_df: Optional[pd.DataFrame] = None

    for sheet_name in excel.sheet_names:
        df = excel.parse(sheet_name=sheet_name)
        score = _score_sales_sheet(df)
        if score > best_score:
            best_score = score
            best_sheet = sheet_name
            best_df = df

    if best_df is None:
        fallback_df = pd.read_excel(file_path)
        return normalize_sales_columns(fallback_df), excel.sheet_names[0] if excel.sheet_names else "Sheet1"

    return normalize_sales_columns(best_df), (best_sheet or excel.sheet_names[0])


def split_sales_by_month(df: pd.DataFrame, fallback_month: str) -> dict[str, pd.DataFrame]:
    """
    Split a sales DataFrame into monthly chunks.

    Priority:
    1. If a parseable date column exists, split by the row-level month.
    2. Otherwise, fallback to the month parsed from filename.
    """
    date_col = find_date_column(df)
    if not date_col:
        return {fallback_month: df}

    parsed_dates = pd.to_datetime(df[date_col], errors="coerce")
    if parsed_dates.notna().sum() == 0:
        return {fallback_month: df}

    df_with_month = df.copy()
    df_with_month["__month_key"] = parsed_dates.dt.strftime("%Y-%m")

    monthly_data: dict[str, pd.DataFrame] = {}
    valid_df = df_with_month[df_with_month["__month_key"].notna()]
    for month_key, month_df in valid_df.groupby("__month_key", sort=True):
        monthly_data[month_key] = month_df.drop(columns="__month_key")

    invalid_df = df_with_month[df_with_month["__month_key"].isna()].drop(columns="__month_key")
    if not invalid_df.empty:
        if fallback_month in monthly_data:
            monthly_data[fallback_month] = pd.concat(
                [monthly_data[fallback_month], invalid_df],
                ignore_index=True,
            )
        else:
            monthly_data[fallback_month] = invalid_df

    return monthly_data if monthly_data else {fallback_month: df}
