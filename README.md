# Business Sales & Inventory Turnover Analysis

## Project Overview

This project analyzes sales data and inventory turnover, generating professional data analysis reports.

## Project Structure

``` 
pseudoctor-business-reviewer/
├── config.yaml
├── run.sh / run.bat
├── raw_data/                                  # Input Excel files
├── data/
│   ├── analysis_data.json                     # Structured analysis output
│   └── china_city_province.csv                # City→province mapping
├── scripts/
│   ├── data_processor.py                      # Analysis data pipeline
│   ├── create_final_report.py                 # HTML report builder
│   ├── common_data_utils.py                   # Shared data utilities
│   ├── marketing_analysis_example.py          # Optional demo script
│   └── marketing_analysis_template.py         # Optional demo template
├── reports/
│   ├── business_sales_inventory_report.html   # Report template
│   └── report_with_data.html                  # Final report with embedded latest data
├── docs/
│   ├── INTEGRATION_GUIDE.md
│   └── report_template_specification.md
└── README.md
```

## Usage Instructions

### Data Preparation

1. Place monthly sales data files (format: YYYYMM.xlsx) in `raw_data/` directory
2. Place inventory data files (format: YYYYMM库存.xlsx) in `raw_data/` directory

### Generate Reports

Recommended:

1. Run `./run.sh` (macOS/Linux) or `run.bat` (Windows)
2. The script runs:
   - `python scripts/data_processor.py`
   - `python scripts/create_final_report.py`
3. Generated outputs:
   - `data/analysis_data.json`
   - `reports/report_with_data.html`

Manual mode:

1. Run `python scripts/data_processor.py` to generate `data/analysis_data.json`
2. Run `python scripts/create_final_report.py` to generate `reports/report_with_data.html`

### View Reports

Open `reports/report_with_data.html` directly in a browser

## Report Template Specification

For detailed report structure, calculation logic, and style specifications, refer to:
- `docs/report_template_specification.md`

## Key Metrics

| Metric | Formula |
|--------|---------|
| Sales Amount | SUM(sales_amount of all records) |
| Sales Quantity | SUM(sales_quantity of all records) |
| Average Transaction Value (ATV) | Sales Amount / Sales Quantity |
| Inventory Turnover Rate | Monthly Sales Quantity / Inventory Quantity |
| Inventory/Sales Ratio | Inventory Quantity / Average Sales of Past 3 Months |

## Risk Level Classification

| Risk Level | Inventory/Sales Ratio | Color Indicator |
|-----------|---------------------|----------------|
| High Risk | ≥ 20 | 🔴 Red |
| Medium Risk | 5 ≤ ratio < 20 | 🟡 Yellow |
| Low Risk | < 5 | 🟢 Green |

## Tech Stack

- **Data Processing**: Python + Pandas
- **Data Visualization**: Chart.js 4.4.1
- **Frontend**: HTML5 + CSS3 + JavaScript

## Data Source Locations

Raw data file storage locations:
- Sales data: `/path/to/monthly/sales/data/`
- Inventory data: `/path/to/inventory/data/`

## Version History

| Version | Date | Description |
|---------|------|-------------|
| v1.0 | 2026-01-31 | Initial version, defined report structure and calculation logic |

---

**Project Created**: 2026-01-31
**Last Updated**: 2026-01-31
