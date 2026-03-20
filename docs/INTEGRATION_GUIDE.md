# Pseudoctor Business Reviewer - Integration Guide

## Overview

This guide explains how to use the integrated data processing pipeline that combines patterns from **ai-data-science-team** with the business logic from **pseudoctor-business-reviewer**.

**Key Principle:** The integration maintains the original calculation logic and output template of pseudoctor-business-reviewer while adding robust data processing capabilities from ai-data-science-team.

---

## Quick Start

### 1. Prepare Your Data

Place your Excel files in the `raw_data/` directory:

```
pseudoctor-business-reviewer/
└── raw_data/
    ├── 202510.xlsx          # October sales data
    ├── 202511.xlsx          # November sales data
    ├── 202512.xlsx          # December sales data
    ├── 202601.xlsx          # January sales data
    └── 202601库存.xlsx       # January inventory data
```

**Expected Excel Columns:**
- **Sales files**: `销售时间`, `商品名称`, `品牌`, `门店名称`, `销售金额`, `销售数量`, `销售净额`
- **Inventory file**: `商品名称`, `商品编码.1` (barcode), `品牌`, `数量` (quantity)

**Data Enrichment Rules (automatic):**
- If the `品牌` column is missing, the pipeline inserts it before product name and infers brand from `商品名称`.
- If the `品牌` column exists but has empty/blank values, only those missing rows are backfilled from `商品名称`.
- Cross-filter data includes province derived from `门店名称` city matching using `data/china_city_province.csv`.
- Unmatched store names are labeled as `未知省份`.

### 2. Install Dependencies

**Option A: Using the run script (Recommended)**
```bash
# macOS/Linux
./run.sh

# Windows
run.bat
```

The script will automatically create a virtual environment and install dependencies.

**Option B: Manual installation**
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Run the Data Processor

**Using the run script:**
```bash
./run.sh                    # macOS/Linux
run.bat                     # Windows
```

**Direct Python execution:**
```bash
source venv/bin/activate    # Activate virtual environment
python scripts/data_processor.py
```

### 4. View the Report

After successful processing, open the final HTML report in your browser:
```
reports/report_with_data.html
```

---

## Configuration

### Edit config.yaml

Customize the processing by editing `config.yaml`:

```yaml
# Data files to process
sales_files:
  - "202510.xlsx"
  - "202511.xlsx"
  - "202512.xlsx"
  - "202601.xlsx"

inventory_file: "202601库存.xlsx"

# Optional: keep only months >= this year (null means no year filtering)
min_year: 2025

# Risk thresholds
risk_high_threshold: 20      # 库存/销售比 >= 20 = 高风险
risk_medium_threshold: 5     # 库存/销售比 >= 5 = 中风险

# Chart settings
top_n_brands: 8              # Number of brands to display
top_n_stores: 8              # Number of stores to display
```

### Command Line Options

```bash
# Use custom config file
python scripts/data_processor.py --config my_config.yaml

# Enable debug mode
python scripts/data_processor.py --debug
```

---

## Project Structure

```
pseudoctor-business-reviewer/
├── config.yaml                 # Configuration file
├── requirements.txt            # Python dependencies
├── run.sh                      # Run script (macOS/Linux)
├── run.bat                     # Run script (Windows)
├── raw_data/                   # Raw Excel files (you add these)
├── scripts/
│   └── data_processor.py       # Main data processing pipeline
├── data/
│   └── analysis_data.json      # Generated analysis data
├── reports/
│   ├── business_sales_inventory_report.html  # Report template
│   └── report_with_data.html                 # Final report with embedded data
└── docs/
    ├── report_template_specification.md  # Report template docs
    └── INTEGRATION_GUIDE.md             # This file
```

---

## Data Processing Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                    Raw Excel Files                          │
│  Sales: YYYYMM.xlsx  |  Inventory: YYYYMM库存.xlsx         │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              DataLoader (ai-data-science-team pattern)      │
│  • Multi-file loading                                       │
│  • Column name standardization                              │
│  • Error handling                                           │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│         DataCleaningAgent (ai-data-science-team pattern)    │
│  • Data type conversion                                     │
│  • Missing value handling                                   │
│  • Duplicate removal                                        │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│       BusinessMetricsCalculator (Original Logic)            │
│  • KPI calculations (sales amount/qty/net, overview)       │
│  • Risk classification (Red/Yellow/Green)                  │
│  • Trend analysis and top-N aggregations                   │
│  • Inventory turnover                                       │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                 analysis_data.json                          │
│  Structured data matching original format                   │
└─────────────────────────────────────────────────────────────┘
```

---

## Integration with ai-data-science-team

### Patterns Used

| Pattern | Source | Purpose |
|---------|--------|---------|
| **DataLoader** | ai-data-science-team DataLoaderToolsAgent | Multi-format file loading with validation |
| **DataCleaningAgent** | ai-data-science-team DataCleaningAgent | Automated data cleaning and standardization |
| **Config Class** | ai-data-science-team configuration patterns | Centralized YAML-based configuration |

### What Was NOT Changed

To preserve the original output:
- ✅ All business logic calculations remain identical
- ✅ JSON output structure matches original exactly
- ✅ Existing report sections/charts and their calculation dimensions remain compatible
- ✅ Risk thresholds use same values
- ✅ Chart data formats are identical

---

## Output Data Structure

The generated `analysis_data.json` contains:

```json
{
  "months": ["2025-10", "2025-11", "2025-12", "2026-01"],
  "overview": [
    {"month": "2025-10", "rows": 7, "stores": 4, "skus": 4, ...},
    ...
  ],
  "trend_sales_amount": [630.0, 354267.75, 458436.87, 575171.96],
  "trend_sales_qty": [6.0, 5274.0, 7461.0, 10829.0],
  "brand_chart": {
    "labels": ["伊利", "秦俑", "君乐宝", "佳贝艾特"],
    "series": {
      "2025-10": [630.0, 0.0, 0.0, 0.0],
      ...
    }
  },
  "store_chart": { ... },
  "product_stability": [
    {"product": "...", "months_in_top10": 4, "total_top10_sales": ...},
    ...
  ],
  "inventory": {
    "total_qty": 48929.0,
    "jan_sales_qty": 10829.0,
    "turnover_ratio": 0.22,
    "slow_items": [...]
  },
  "insights": [
    {"fact": "...", "why": "...", "so_what": "..."},
    ...
  ]
}
```

Metric note:
- Trend calculations use `销售金额` as the unified business metric.
- `trend_sales_net` is kept for backward compatibility and currently mirrors `trend_sales_amount`.

---

## Cross-Filter Performance Benchmark

This benchmark focuses on the hotspot inside `applyGlobalFilteredView`:
- Old path: repeated `filter + reduce` for each `month x brand`
- New path: pre-aggregate `month -> brand -> amount` once, then reuse

### Command

Run the benchmark script:

```bash
python3 scripts/benchmark_crossfilter_perf.py --rounds 12 --scales 1,2,4
```

Why run this command:
- It executes both old/new algorithms against the same `reports/report_with_data.html` dataset.
- It reports `mean/p50/p95/min/max` latency and average speedup.
- It scales row volume by `1x/2x/4x` to approximate larger datasets.

### Latest Result Snapshot (2026-03-01)

Dataset source:
- `reports/report_with_data.html`
- Base `crossFilter.records`: `57,640` rows

| Scale | Rows | Old mean (ms) | New mean (ms) | Mean speedup |
|------|------:|--------------:|--------------:|-------------:|
| 1x | 57,640 | 17.40 | 7.61 | 2.29x |
| 2x | 115,280 | 31.69 | 15.08 | 2.10x |
| 4x | 230,560 | 60.13 | 29.87 | 2.01x |

Conclusion:
- The pre-aggregation path consistently improves this hotspot by about `2x`.
- As data volume grows, latency scales roughly linearly on both paths, with the optimized version maintaining lower constant overhead.

---

## Troubleshooting

### Common Issues

**Issue:** `FileNotFoundError: No sales data files found`
- **Solution:** Ensure Excel files are in `raw_data/` directory with correct names

**Issue:** `KeyError: '销售金额'`
- **Solution:** Check that your Excel files have the required column names

**Issue:** Incorrect calculations
- **Solution:** Verify data quality, check for missing values in key columns

**Issue:** Module import errors
- **Solution:** Make sure you've activated the virtual environment and installed dependencies

### Debug Mode

Enable debug output in `config.yaml`:
```yaml
debug: true
```

Or run with:
```bash
python scripts/data_processor.py --debug
```

---

## Automation

### Cron Job (Linux/macOS)

Add to crontab (`crontab -e`):
```bash
# Run every month on the 5th at 9 AM
0 9 5 * * cd /path/to/pseudoctor-business-reviewer && ./run.sh
```

### Task Scheduler (Windows)

Create a scheduled task that runs:
```
cmd.exe /c "cd /d C:\path\to\pseudoctor-business-reviewer && run.bat"
```

---

## API Reference

### DataLoader

```python
from scripts.data_processor import DataLoader

loader = DataLoader()
sales_data = loader.load_sales_files(['202510.xlsx', '202511.xlsx'])
inventory_df = loader.load_inventory_file('202601库存.xlsx')
```

### BusinessMetricsCalculator

```python
from scripts.data_processor import BusinessMetricsCalculator

calculator = BusinessMetricsCalculator(sales_data, inventory_df)
analysis_data = calculator.calculate_all()
```

---

## Contributing

When extending this project:

1. **Keep calculation logic unchanged** - All business metrics should remain identical
2. **Preserve JSON structure** - New fields can be added, but existing structure must match
3. **Follow existing patterns** - Use the established classes and methods
4. **Update documentation** - Keep this guide and the template spec in sync

---

## License

This project integrates patterns from ai-data-science-team while maintaining the business logic of pseudoctor-business-reviewer. Both projects should be credited when distributing derivative works.

---

**Last Updated:** 2026-01-31
**Integration Version:** 1.0
