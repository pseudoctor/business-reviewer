#!/usr/bin/env python3
"""
Pseudoctor Business Reviewer - Data Processing Pipeline

This script processes raw Excel files and generates analysis_data.json
maintaining the exact calculation logic and output format.

Inspired by ai-data-science-team patterns for data loading and cleaning.
"""

import pandas as pd
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional
import yaml

try:
    from common_data_utils import (
        ensure_brand_column,
        normalize_sales_columns,
        parse_month_label,
        parse_year_month_key,
        read_sales_excel_auto_sheet,
        split_sales_by_month,
        sort_month_labels,
    )
except ModuleNotFoundError:
    from scripts.common_data_utils import (
        ensure_brand_column,
        normalize_sales_columns,
        parse_month_label,
        parse_year_month_key,
        read_sales_excel_auto_sheet,
        split_sales_by_month,
        sort_month_labels,
    )

BASE_DIR = Path(__file__).parent.parent


# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    """
    Central configuration for the data processing pipeline

    Supports loading from YAML config file or using default values.
    """

    # Default values
    _defaults = {
        'raw_data_dir': './raw_data',
        'output_dir': './data',
        'output_file': './data/analysis_data.json',
        'sales_files': ['202510.xlsx', '202511.xlsx', '202512.xlsx', '202601.xlsx'],
        'inventory_file': '202601库存.xlsx',
        'min_year': None,
        'missing_value_threshold': 0.4,
        'outlier_threshold': 3.0,
        'risk_high_threshold': 20,
        'risk_medium_threshold': 5,
        'top_n_brands': 8,
        'top_n_stores': 8,
        'top_n_products': 20,
        'slow_items_threshold': 5.0,
        'debug': False,
        'skip_cleaning': False,
    }

    def __init__(self, config_file: str = None):
        """
        Initialize configuration

        Args:
            config_file: Path to YAML config file (optional)
        """
        # Load from config file if provided
        if config_file:
            self._load_from_yaml(config_file)
        else:
            # Try to load default config file
            default_config = Path(__file__).parent.parent / "config.yaml"
            if default_config.exists():
                self._load_from_yaml(default_config)
            else:
                # Use defaults
                self._apply_defaults()

    def _apply_defaults(self):
        """Apply default configuration values"""
        # Resolve paths relative to script location
        base_dir = Path(__file__).parent.parent
        self.RAW_DATA_DIR = base_dir / "raw_data"
        self.OUTPUT_DIR = base_dir / "data"
        self.OUTPUT_FILE = self.OUTPUT_DIR / "analysis_data.json"
        self.SALES_FILES = self._defaults['sales_files']
        self.INVENTORY_FILE = self._defaults['inventory_file']
        self.MIN_YEAR = self._defaults['min_year']
        self.MISSING_VALUE_THRESHOLD = self._defaults['missing_value_threshold']
        self.OUTLIER_THRESHOLD = self._defaults['outlier_threshold']
        self.RISK_HIGH_THRESHOLD = self._defaults['risk_high_threshold']
        self.RISK_MEDIUM_THRESHOLD = self._defaults['risk_medium_threshold']
        self.TOP_N_BRANDS = self._defaults['top_n_brands']
        self.TOP_N_STORES = self._defaults['top_n_stores']
        self.TOP_N_PRODUCTS = self._defaults['top_n_products']
        self.SLOW_ITEMS_THRESHOLD = self._defaults['slow_items_threshold']
        self.DEBUG = self._defaults['debug']
        self.SKIP_CLEANING = self._defaults['skip_cleaning']

    def _load_from_yaml(self, config_file: str):
        """Load configuration from YAML file"""
        config_path = Path(config_file)
        if not config_path.exists():
            print(f"  ⚠ Config file not found: {config_file}, using defaults")
            self._apply_defaults()
            return

        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # Resolve paths
        base_dir = Path(__file__).parent.parent
        raw_dir = config.get('raw_data_dir', self._defaults['raw_data_dir'])
        self.RAW_DATA_DIR = base_dir / raw_dir if not Path(raw_dir).is_absolute() else Path(raw_dir)
        out_dir = config.get('output_dir', self._defaults['output_dir'])
        self.OUTPUT_DIR = base_dir / out_dir if not Path(out_dir).is_absolute() else Path(out_dir)
        out_file = config.get('output_file', self._defaults['output_file'])
        self.OUTPUT_FILE = base_dir / out_file if not Path(out_file).is_absolute() else Path(out_file)

        # Load other settings
        sales = config.get('sales_files', self._defaults['sales_files'])
        self.SALES_FILES = sales if isinstance(sales, list) else self._defaults['sales_files']
        self.INVENTORY_FILE = config.get('inventory_file', self._defaults['inventory_file'])
        min_year = config.get('min_year', self._defaults['min_year'])
        if min_year in ("", None):
            self.MIN_YEAR = None
        else:
            try:
                self.MIN_YEAR = int(min_year)
            except (TypeError, ValueError):
                print(f"  ⚠ Invalid min_year={min_year}, fallback to no year filter")
                self.MIN_YEAR = None
        self.MISSING_VALUE_THRESHOLD = config.get('missing_value_threshold', self._defaults['missing_value_threshold'])
        self.OUTLIER_THRESHOLD = config.get('outlier_threshold', self._defaults['outlier_threshold'])
        self.RISK_HIGH_THRESHOLD = config.get('risk_high_threshold', self._defaults['risk_high_threshold'])
        self.RISK_MEDIUM_THRESHOLD = config.get('risk_medium_threshold', self._defaults['risk_medium_threshold'])
        self.TOP_N_BRANDS = config.get('top_n_brands', self._defaults['top_n_brands'])
        self.TOP_N_STORES = config.get('top_n_stores', self._defaults['top_n_stores'])
        self.TOP_N_PRODUCTS = config.get('top_n_products', self._defaults['top_n_products'])
        self.SLOW_ITEMS_THRESHOLD = config.get('slow_items_threshold', self._defaults['slow_items_threshold'])
        self.DEBUG = config.get('debug', self._defaults['debug'])
        self.SKIP_CLEANING = config.get('skip_cleaning', self._defaults['skip_cleaning'])


# ============================================================================
# DATA LOADER (Inspired by ai-data-science-team DataLoaderToolsAgent)
# ============================================================================

class DataLoader:
    """
    Load and validate raw data files

    Inspired by ai-data-science-team DataLoaderToolsAgent pattern
    with support for multiple file formats and safety checks.
    """

    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.raw_data_dir = self.config.RAW_DATA_DIR

    def load_sales_files(self, file_patterns: List[str] = None) -> Dict[str, pd.DataFrame]:
        """
        Load multiple sales Excel files

        Args:
            file_patterns: List of file patterns like ['202510.xlsx', '202511.xlsx']

        Returns:
            Dictionary mapping month names to DataFrames with standardized columns
        """
        if file_patterns is None:
            file_patterns = self.config.SALES_FILES

        sales_data = {}
        for pattern in file_patterns:
            file_path = self.raw_data_dir / pattern
            if file_path.exists():
                try:
                    df, selected_sheet = read_sales_excel_auto_sheet(file_path)
                    # Clean column names
                    df.columns = df.columns.str.strip()
                    fallback_month = parse_month_label(pattern)
                    monthly_frames = split_sales_by_month(df, fallback_month)

                    for month_key, month_df in monthly_frames.items():
                        ym = parse_year_month_key(month_key)
                        if self.config.MIN_YEAR is not None and ym and ym[0] < self.config.MIN_YEAR:
                            continue
                        if month_key in sales_data:
                            sales_data[month_key] = pd.concat(
                                [sales_data[month_key], month_df],
                                ignore_index=True
                            )
                        else:
                            sales_data[month_key] = month_df

                    print(f"  ✓ Loaded: {pattern} ({len(df):,} rows)")
                    if selected_sheet != "Sheet1":
                        print(f"    ↳ Selected sheet: {selected_sheet}")
                    if len(monthly_frames) > 1:
                        split_months = ", ".join(monthly_frames.keys())
                        print(f"    ↳ Split by date into months: {split_months}")
                except Exception as e:
                    print(f"  ✗ Error loading {pattern}: {e}")
            else:
                print(f"  ⚠ File not found: {pattern}")

        if not sales_data:
            raise FileNotFoundError("No sales data files found. Please check the raw_data directory.")

        return sales_data

    def load_inventory_file(self, filename: str = None) -> Optional[pd.DataFrame]:
        """
        Load inventory Excel file

        Args:
            filename: Inventory file name (default: from config)

        Returns:
            DataFrame with inventory data
        """
        if filename is None:
            filename = self.config.INVENTORY_FILE

        file_path = self.raw_data_dir / filename
        if file_path.exists():
            try:
                df = pd.read_excel(file_path)
                df.columns = df.columns.str.strip()
                print(f"  ✓ Loaded inventory: {filename} ({len(df):,} rows)")
                return df
            except Exception as e:
                print(f"  ✗ Error loading inventory file: {e}")
        else:
            print(f"  ⚠ Inventory file not found: {filename}")

        return None


# ============================================================================
# DATA CLEANING AGENT (Inspired by ai-data-science-team DataCleaningAgent)
# ============================================================================

class DataCleaningAgent:
    """
    Clean and standardize data

    Inspired by ai-data-science-team DataCleaningAgent with automatic
    data type conversion, missing value handling, and validation.
    """

    @staticmethod
    def clean_sales_data(df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and standardize sales data

        Operations:
        1. Standardize column names
        2. Convert date formats
        3. Remove rows with missing critical fields
        4. Ensure numeric types for amount/quantity fields
        5. Remove obvious duplicates

        Args:
            df: Raw sales DataFrame

        Returns:
            Cleaned DataFrame
        """
        df_clean = df.copy()

        # Standardize column names (remove extra spaces)
        df_clean.columns = df_clean.columns.str.strip()
        df_clean = normalize_sales_columns(df_clean)
        df_clean = ensure_brand_column(df_clean)

        # Convert date format
        date_columns = [col for col in df_clean.columns if '时间' in col or 'date' in col.lower()]
        for col in date_columns:
            df_clean[col] = pd.to_datetime(df_clean[col], errors='coerce')

        # Ensure numeric types for key fields
        numeric_mappings = {
            '销售金额': ['销售金额', '金额', 'amount', 'sales_amount'],
            '销售数量': ['销售数量', '数量', 'quantity', 'sales_qty'],
            '销售净额': ['销售净额', '净额', 'net_amount', 'sales_net']
        }

        for target_col, possible_names in numeric_mappings.items():
            for col in df_clean.columns:
                if col in possible_names or target_col in col:
                    df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce').fillna(0)
                    break

        # Remove rows with all-zero critical fields
        critical_fields = ['销售金额', '销售数量']
        existing_critical = [f for f in critical_fields if f in df_clean.columns]
        if existing_critical:
            df_clean = df_clean.loc[~(df_clean[existing_critical] == 0).all(axis=1)]

        return df_clean

    @staticmethod
    def clean_inventory_data(df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and standardize inventory data

        Note: For inventory, we DO NOT remove duplicates because each row
        represents inventory for a specific store-product combination.

        Args:
            df: Raw inventory DataFrame

        Returns:
            Cleaned DataFrame
        """
        df_clean = df.copy()
        df_clean.columns = df_clean.columns.str.strip()
        df_clean = ensure_brand_column(df_clean)

        # Ensure numeric type for quantity
        quantity_columns = [col for col in df_clean.columns if '数量' in col or 'quantity' in col.lower()]
        for col in quantity_columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce').fillna(0)

        return df_clean


# ============================================================================
# BUSINESS METRICS CALCULATOR (Maintains Original Calculation Logic)
# ============================================================================

class BusinessMetricsCalculator:
    """
    Calculate business metrics for pseudoctor-business-reviewer

    Maintains the exact calculation logic from the original template.
    """

    def __init__(self, sales_data: Dict[str, pd.DataFrame], inventory_df: pd.DataFrame, config: Config = None):
        self.sales_data = sales_data
        self.inventory_df = inventory_df
        self.months = sort_month_labels(list(sales_data.keys()))
        self.config = config or Config()

    def calculate_all(self) -> Dict:
        """
        Calculate all metrics and return complete analysis_data.json structure

        Returns:
            Dictionary matching the exact structure of analysis_data.json
        """
        print("\n[Calculating Metrics]")

        result = {
            "months": self.months,
            "overview": self._calculate_overview(),
            "trend_sales_amount": self._calculate_trend_amount(),
            "trend_sales_qty": self._calculate_trend_qty(),
            "trend_sales_net": self._calculate_trend_net(),
            "brand_chart": self._calculate_brand_chart(),
            "store_chart": self._calculate_store_chart(),
            "product_stability": self._calculate_product_stability(),
            "inventory": self._calculate_inventory(),
            "insights": self._generate_insights()
        }

        print(f"  ✓ All metrics calculated")
        return result

    def _calculate_overview(self) -> List[Dict]:
        """Calculate monthly overview statistics"""
        overview = []
        for month in self.months:
            df = self.sales_data[month]
            overview.append({
                "month": month,
                "rows": int(len(df)),
                "stores": int(df['门店名称'].nunique()) if '门店名称' in df.columns else 0,
                "skus": int(df['商品名称'].nunique()) if '商品名称' in df.columns else 0,
                "sales_amount": round(float(df['销售金额'].sum()), 2) if '销售金额' in df.columns else 0,
                "sales_qty": round(float(df['销售数量'].sum()), 1) if '销售数量' in df.columns else 0,
                "sales_net": round(float(df['销售净额'].sum()), 10) if '销售净额' in df.columns else 0
            })
        return overview

    def _calculate_trend_amount(self) -> List[float]:
        """Calculate monthly sales amount trend (robust to month-level schema drift)."""
        trend = []
        for month in self.months:
            df = self.sales_data[month]
            value = float(df['销售金额'].sum()) if '销售金额' in df.columns else 0.0
            trend.append(round(value, 2))
        return trend

    def _calculate_trend_qty(self) -> List[float]:
        """Calculate monthly sales quantity trend (robust to month-level schema drift)."""
        trend = []
        for month in self.months:
            df = self.sales_data[month]
            value = float(df['销售数量'].sum()) if '销售数量' in df.columns else 0.0
            trend.append(round(value, 1))
        return trend

    def _calculate_trend_net(self) -> List[float]:
        """
        Backward-compatible field.

        Business口径统一为销售金额，不再以销售净额作为趋势主口径。
        为兼容旧字段名，沿用 trend_sales_net 键但返回销售金额趋势。
        """
        return [round(v, 10) for v in self._calculate_trend_amount()]

    def _calculate_brand_chart(self) -> Dict:
        """Calculate brand sales chart data"""
        # Get all unique brands across all months
        all_brands = set()
        for df in self.sales_data.values():
            if '品牌' in df.columns:
                all_brands.update(df['品牌'].dropna().unique())

        # Sort brands by total sales
        brand_totals = {}
        for month in self.months:
            df = self.sales_data[month]
            if '品牌' in df.columns and '销售金额' in df.columns:
                month_totals = df.groupby('品牌')['销售金额'].sum()
                for brand, value in month_totals.items():
                    if brand not in brand_totals:
                        brand_totals[brand] = 0
                    brand_totals[brand] += float(value)

        # Get top N brands
        top_brands = sorted(brand_totals.items(), key=lambda x: x[1], reverse=True)
        top_brands = [b[0] for b in top_brands[:self.config.TOP_N_BRANDS]]

        # Build series data
        series = {}
        for month in self.months:
            df = self.sales_data[month]
            if '品牌' in df.columns and '销售金额' in df.columns:
                month_sales = df.groupby('品牌')['销售金额'].sum()
                series[month] = [round(float(month_sales.get(b, 0)), 2) for b in top_brands]
            else:
                series[month] = [0.0] * len(top_brands)

        return {
            "labels": top_brands,
            "series": series
        }

    def _calculate_store_chart(self) -> Dict:
        """Calculate store sales chart data"""
        # Get top N stores by total sales
        store_totals = {}
        for month in self.months:
            df = self.sales_data[month]
            if '门店名称' in df.columns and '销售金额' in df.columns:
                month_totals = df.groupby('门店名称')['销售金额'].sum()
                for store, value in month_totals.items():
                    if store not in store_totals:
                        store_totals[store] = 0
                    store_totals[store] += float(value)

        # Get top N stores
        top_stores = sorted(store_totals.items(), key=lambda x: x[1], reverse=True)
        top_stores = [s[0] for s in top_stores[:self.config.TOP_N_STORES]]

        # Build series data
        series = {}
        for month in self.months:
            df = self.sales_data[month]
            if '门店名称' in df.columns and '销售金额' in df.columns:
                month_sales = df.groupby('门店名称')['销售金额'].sum()
                series[month] = [round(float(month_sales.get(s, 0)), 2) for s in top_stores]
            else:
                series[month] = [0.0] * len(top_stores)

        return {
            "labels": top_stores,
            "series": series
        }

    def _calculate_product_stability(self) -> List[Dict]:
        """Calculate product stability (Top10 appearances)"""
        # Track which products appear in Top10 each month
        monthly_top10 = {}

        for month in self.months:
            df = self.sales_data[month]
            if '商品名称' in df.columns and '销售金额' in df.columns:
                product_sales = df.groupby('商品名称')['销售金额'].sum().sort_values(ascending=False)
                monthly_top10[month] = set(product_sales.head(10).index)
            else:
                monthly_top10[month] = set()

        # Calculate stability for all products that appeared in any Top10
        all_top_products = set()
        for top10 in monthly_top10.values():
            all_top_products.update(top10)

        product_stats = []
        for product in all_top_products:
            months_in_top10 = int(sum(1 for top10 in monthly_top10.values() if product in top10))

            # Calculate total sales when in Top10
            total_top10_sales = 0.0
            for month in self.months:
                df = self.sales_data[month]
                if product in monthly_top10.get(month, set()) and '商品名称' in df.columns and '销售金额' in df.columns:
                    product_sales = df[df['商品名称'] == product]['销售金额'].sum()
                    total_top10_sales += float(product_sales)

            product_stats.append({
                "product": product,
                "months_in_top10": months_in_top10,
                "total_top10_sales": round(total_top10_sales, 2)
            })

        # Sort by months in Top10, then by sales
        product_stats.sort(key=lambda x: (-x['months_in_top10'], -x['total_top10_sales']))

        return product_stats

    def _calculate_inventory(self) -> Dict:
        """Calculate inventory metrics and slow-moving items"""
        empty_result = {
            "total_qty": 0,
            "jan_sales_qty": 0,
            "turnover_ratio": 0,
            "risk_thresholds": {
                "high": float(self.config.RISK_HIGH_THRESHOLD),
                "medium": float(self.config.RISK_MEDIUM_THRESHOLD),
            },
            "risk_counts": {"high": 0, "medium": 0, "low": 0},
            "slow_items": []
        }

        if self.inventory_df is None:
            return empty_result

        if '商品名称' not in self.inventory_df.columns:
            return empty_result

        qty_col = next(
            (
                col
                for col in self.inventory_df.columns
                if '数量' in str(col) or 'quantity' in str(col).lower()
            ),
            None,
        )
        if not qty_col:
            return empty_result

        # Aggregate inventory by product (flexible quantity column)
        inv_by_product = self.inventory_df.groupby('商品名称').agg({
            qty_col: 'sum'
        }).reset_index()
        inv_by_product.columns = ['商品名称', '库存数量']

        # Get latest-month sales
        jan_month = self.months[-1]
        jan_df = self.sales_data[jan_month]
        if '商品名称' in jan_df.columns and '销售数量' in jan_df.columns:
            jan_sales = jan_df.groupby('商品名称').agg({
                '销售数量': 'sum'
            }).reset_index()
            jan_sales.columns = ['商品名称', '1月销售数量']
        else:
            jan_sales = pd.DataFrame(columns=['商品名称', '1月销售数量'])

        # Merge
        merged = inv_by_product.merge(jan_sales, on='商品名称', how='left')
        merged['1月销售数量'] = merged['1月销售数量'].fillna(0)

        # Calculate total metrics
        total_qty = merged['库存数量'].sum()
        jan_sales_qty = merged['1月销售数量'].sum()
        turnover_ratio = jan_sales_qty / total_qty if total_qty > 0 else 0

        # Calculate inventory/sales ratio
        merged['库存/销售比'] = merged.apply(
            lambda row: 9999 if row['1月销售数量'] == 0 else row['库存数量'] / row['1月销售数量'],
            axis=1
        )

        # Filter slow items (库存/销售比 >= threshold)
        slow_items = merged[merged['库存/销售比'] >= self.config.SLOW_ITEMS_THRESHOLD].copy()
        slow_items = slow_items.sort_values('库存/销售比', ascending=False)

        high_threshold = float(self.config.RISK_HIGH_THRESHOLD)
        medium_threshold = float(self.config.RISK_MEDIUM_THRESHOLD)
        high_risk_count = int((merged['库存/销售比'] >= high_threshold).sum())
        medium_risk_count = int(((merged['库存/销售比'] >= medium_threshold) & (merged['库存/销售比'] < high_threshold)).sum())
        low_risk_count = int((merged['库存/销售比'] < medium_threshold).sum())

        # Format output
        slow_items_list = []
        for _, row in slow_items.iterrows():
            slow_items_list.append({
                "商品名称": row['商品名称'],
                "库存数量": float(row['库存数量']),
                "1月销售数量": float(row['1月销售数量']),
                "库存/销售比": float(row['库存/销售比'])
            })

        return {
            "total_qty": float(total_qty),
            "jan_sales_qty": float(jan_sales_qty),
            "turnover_ratio": float(turnover_ratio),
            "risk_thresholds": {
                "high": high_threshold,
                "medium": medium_threshold,
            },
            "risk_counts": {
                "high": high_risk_count,
                "medium": medium_risk_count,
                "low": low_risk_count,
            },
            "slow_items": slow_items_list
        }

    def _generate_insights(self) -> List[Dict]:
        """Generate automated insights from the data"""
        insights = []

        # Insight 1: Month over month change
        if len(self.months) >= 2:
            last_month = self.months[-1]
            prev_month = self.months[-2]
            last_sales = self.sales_data[last_month]['销售金额'].sum() if '销售金额' in self.sales_data[last_month].columns else 0
            prev_sales = self.sales_data[prev_month]['销售金额'].sum() if '销售金额' in self.sales_data[prev_month].columns else 0
            change = last_sales - prev_sales

            if change > 0:
                insights.append({
                    "fact": f"{last_month}销售金额为{last_sales:,.0f}，较{prev_month}上升{change:,.0f}。",
                    "why": "节后结构调整、门店覆盖与动销节奏变化可能影响表现。",
                    "so_what": "建议针对贡献门店与品牌做补货节奏与促销强度的精细化配置。"
                })
            else:
                insights.append({
                    "fact": f"{last_month}销售金额为{last_sales:,.0f}，较{prev_month}下降{abs(change):,.0f}。",
                    "why": "季节性因素、库存结构或促销活动减少可能影响销售。",
                    "so_what": "建议分析下降原因，调整促销策略和库存配置。"
                })

        # Insight 2: Brand concentration
        all_data = pd.concat(self.sales_data.values(), ignore_index=True)
        total_sales = all_data['销售金额'].sum() if '销售金额' in all_data.columns else 0
        if '品牌' in all_data.columns and '销售金额' in all_data.columns:
            top_brand_sales = all_data.groupby('品牌')['销售金额'].sum().max()
            brand_concentration = (top_brand_sales / total_sales * 100) if total_sales > 0 else 0

            insights.append({
                "fact": f"头部品牌贡献约{brand_concentration:.1f}%销售金额。",
                "why": "品牌集中度高，头部品牌带动整体销售。",
                "so_what": "头部品牌需保障库存与陈列资源，同时培育腰部品牌分担波动。"
            })

        # Insight 3: Store concentration
        if '门店名称' in all_data.columns and '销售金额' in all_data.columns:
            store_sales = all_data.groupby('门店名称')['销售金额'].sum().sort_values(ascending=False)
            top_stores_sales = store_sales.head(self.config.TOP_N_STORES).sum()
            store_concentration = (top_stores_sales / total_sales * 100) if total_sales > 0 else 0

            insights.append({
                "fact": f"前{self.config.TOP_N_STORES}门店贡献约{store_concentration:.1f}%销售金额。",
                "why": "核心门店覆盖人流与消费力较强。",
                "so_what": "对核心门店设置差异化货品结构与补货频次，拉动整体。"
            })

        # Insight 4: Inventory turnover
        inv_data = self._calculate_inventory()
        if inv_data['turnover_ratio'] > 0:
            insights.append({
                "fact": f"1月销售数量/库存数量约为{inv_data['turnover_ratio']:.2f}。",
                "why": "库存结构与销量匹配度决定周转效率。",
                "so_what": "对高库存低动销SKU做降采或促销清理，提高现金效率。"
            })

        return insights


# ============================================================================
# REPORT GENERATOR
# ============================================================================

class ReportGenerator:
    """Generate analysis_data.json for pseudoctor-business-reviewer"""

    def __init__(self, output_path: Path = None):
        self.output_path = output_path or (BASE_DIR / "data" / "analysis_data.json")
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def generate(self, data: Dict) -> None:
        """Write analysis data to JSON file"""
        with open(self.output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"\n✓ Report generated: {self.output_path}")


# ============================================================================
# MAIN PROCESSING PIPELINE
# ============================================================================

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Pseudoctor Business Reviewer - Data Processing Pipeline"
    )
    parser.add_argument(
        "--config",
        help="Path to custom YAML config file (default: ./config.yaml)",
        default=None,
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode",
    )
    return parser.parse_args()


def main(config_file: str = None, force_debug: bool = False):
    """Main processing pipeline"""
    print("=" * 70)
    print(" Pseudoctor Business Reviewer - Data Processing Pipeline")
    print(" Maintaining original calculation logic and output format")
    print("=" * 70)

    try:
        # Load configuration
        config = Config(config_file)
        if force_debug:
            config.DEBUG = True
        if config.DEBUG:
            print("\n[Debug] Configuration")
            print(f"  config_file: {config_file or 'default config.yaml'}")
            print(f"  raw_data_dir: {config.RAW_DATA_DIR}")
            print(f"  output_file: {config.OUTPUT_FILE}")
            print(f"  sales_files: {config.SALES_FILES}")
            print(f"  inventory_file: {config.INVENTORY_FILE}")
            print(f"  min_year: {config.MIN_YEAR}")
            print(f"  top_n_brands/stores/products: {config.TOP_N_BRANDS}/{config.TOP_N_STORES}/{config.TOP_N_PRODUCTS}")
            print(f"  risk thresholds (high/medium): {config.RISK_HIGH_THRESHOLD}/{config.RISK_MEDIUM_THRESHOLD}")

        # Step 1: Load data
        print("\n[Step 1] Loading data files...")
        loader = DataLoader(config)
        sales_data = loader.load_sales_files()
        inventory_df = loader.load_inventory_file()
        if config.DEBUG:
            for month, df in sales_data.items():
                print(f"  [Debug] {month}: columns={len(df.columns)} rows={len(df)}")
            if inventory_df is not None:
                print(f"  [Debug] inventory: columns={len(inventory_df.columns)} rows={len(inventory_df)}")

        # Step 2: Clean data
        print("\n[Step 2] Cleaning data...")
        if config.SKIP_CLEANING:
            print("  ⚠ skip_cleaning=true, using raw loaded data without cleaning")
        else:
            for month, df in sales_data.items():
                sales_data[month] = DataCleaningAgent.clean_sales_data(df)
            if inventory_df is not None:
                inventory_df = DataCleaningAgent.clean_inventory_data(inventory_df)

        if config.DEBUG:
            print(f"  [Debug] cleaning thresholds: missing={config.MISSING_VALUE_THRESHOLD}, outlier={config.OUTLIER_THRESHOLD}")
            for month, df in sales_data.items():
                numeric_cols = [c for c in ['销售金额', '销售数量', '销售净额'] if c in df.columns]
                missing_ratio = float(df[numeric_cols].isna().mean().mean()) if numeric_cols else 0.0
                outlier_count = 0
                for col in numeric_cols:
                    s = pd.to_numeric(df[col], errors='coerce').dropna()
                    if s.empty:
                        continue
                    q1 = s.quantile(0.25)
                    q3 = s.quantile(0.75)
                    iqr = q3 - q1
                    if iqr <= 0:
                        continue
                    lower = q1 - config.OUTLIER_THRESHOLD * iqr
                    upper = q3 + config.OUTLIER_THRESHOLD * iqr
                    outlier_count += int(((s < lower) | (s > upper)).sum())
                print(f"  [Debug] {month}: missing_ratio={missing_ratio:.3f}, outliers={outlier_count}")

        # Step 3: Calculate metrics
        print("\n[Step 3] Calculating business metrics...")
        calculator = BusinessMetricsCalculator(sales_data, inventory_df, config)
        analysis_data = calculator.calculate_all()

        # Step 4: Generate report
        print("\n[Step 4] Generating analysis data...")
        generator = ReportGenerator(config.OUTPUT_FILE)
        generator.generate(analysis_data)

        # Print summary
        total_records = sum(o['rows'] for o in analysis_data['overview'])
        total_sales = sum(analysis_data['trend_sales_amount'])
        total_brands = len(analysis_data['brand_chart']['labels'])

        print("\n" + "=" * 70)
        print(" PROCESSING COMPLETE")
        print("=" * 70)
        print(f"  Months processed: {len(analysis_data['months'])}")
        print(f"  Total records: {total_records:,}")
        print(f"  Total sales: ¥{total_sales:,.2f}")
        print(f"  Brands tracked: {total_brands}")
        print(f"  Slow-moving items: {len(analysis_data['inventory']['slow_items'])}")
        print("=" * 70)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    args = parse_args()
    exit(main(config_file=args.config, force_debug=args.debug))
